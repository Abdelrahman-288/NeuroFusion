"""Durable local message exchange for a synchronous federated simulation.

Hashes provide integrity, not authenticated participants, privacy or secure transport.
"""
import hashlib,io,json,os,secrets
from pathlib import Path
from contextlib import contextmanager
import torch
from neurofusion.cohort import digest
from neurofusion.federated import aggregate


def serialize(value):
    stream=io.BytesIO();torch.save(value,stream);return stream.getvalue()


def atomic_bytes(path,data):
    path=Path(path);temporary=path.with_name(path.name+'.'+secrets.token_hex(8)+'.tmp')
    try:
        with temporary.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)


class RoundExchange:
    @classmethod
    def create(cls,folder,state,round_id,protocol_sha256,clients):
        if type(round_id) is not int or round_id<1 or not clients or any(type(n) is not int or n<=0 for n in clients.values()):raise ValueError('Invalid round/client contract')
        if any(not isinstance(c,str) or not c or not c.replace('-','').isalnum() for c in clients):raise ValueError('Invalid client name')
        if len(protocol_sha256)!=64:raise ValueError('Invalid protocol hash')
        if not state or any(not torch.is_tensor(v) or not torch.isfinite(v).all() for v in state.values()):raise ValueError('Invalid base state')
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
        atomic_bytes(folder/'base.pt',serialize({k:v.detach().cpu() for k,v in state.items()}))
        contract=dict(schema_version=1,round=round_id,protocol_sha256=protocol_sha256,clients=clients,base_sha256=digest(folder/'base.pt'))
        atomic_bytes(folder/'contract.json',json.dumps(contract,sort_keys=True).encode())
        return cls(folder)

    def __init__(self,folder):
        self.folder=Path(folder);self.contract=json.loads((self.folder/'contract.json').read_text())
        if digest(self.folder/'base.pt')!=self.contract['base_sha256']:raise ValueError('Base checkpoint changed')
        self.base=torch.load(self.folder/'base.pt',weights_only=True,map_location='cpu')
        self.contract_sha256=digest(self.folder/'contract.json')

    @contextmanager
    def lock(self):
        path=self.folder/'writer.lock'
        try:handle=path.open('x')
        except FileExistsError:raise ValueError('Round writer active; inspect lock before recovery') from None
        try:
            handle.close()
            if digest(self.folder/'contract.json')!=self.contract_sha256 or digest(self.folder/'base.pt')!=self.contract['base_sha256']:raise ValueError('Round contract/base changed')
            yield
        finally:path.unlink()

    def encode(self,client,state):
        return serialize(dict(schema_version=1,client=client,samples=self.contract['clients'][client],
            round=self.contract['round'],protocol_sha256=self.contract['protocol_sha256'],
            base_sha256=self.contract['base_sha256'],contract_sha256=self.contract_sha256,state=state))

    def decode(self,payload):
        if not isinstance(payload,bytes) or len(payload)>2*(self.folder/'base.pt').stat().st_size+65536:raise ValueError('Update payload exceeds bound')
        try:value=torch.load(io.BytesIO(payload),weights_only=True,map_location='cpu')
        except Exception as error:raise ValueError('Invalid serialized update') from error
        if not isinstance(value,dict):raise ValueError('Invalid update envelope')
        if set(value)!={'schema_version','client','samples','round','protocol_sha256','base_sha256','contract_sha256','state'} or type(value['schema_version']) is not int or type(value['round']) is not int:raise ValueError('Unexpected message fields or types')
        c=value.get('client')
        if c not in self.contract['clients'] or type(value.get('samples')) is not int or value['samples']!=self.contract['clients'][c]:raise ValueError('Client or sample count differs')
        if value.get('schema_version')!=1 or any(value.get(k)!=self.contract[k] for k in ('round','protocol_sha256','base_sha256')) or value.get('contract_sha256')!=self.contract_sha256:raise ValueError('Stale or incompatible update')
        state=value.get('state')
        if not isinstance(state,dict) or state.keys()!=self.base.keys():raise ValueError('Model keys differ')
        for k,v in state.items():
            base=self.base[k]
            if not torch.is_tensor(v) or v.shape!=base.shape or v.dtype!=base.dtype or not torch.isfinite(v).all():raise ValueError('Malformed state')
            if not v.is_floating_point() and not torch.equal(v,base):raise ValueError('Nonfloating base buffers changed')
        return value

    def submit(self,payload):
        with self.lock():
            value=self.decode(payload);path=self.folder/(value['client']+'.pt')
            if path.exists():
                if path.read_bytes()!=payload:raise ValueError('Conflicting client retry')
                receipt=path.with_suffix('.sha256')
                checksum=hashlib.sha256(payload).hexdigest()
                if receipt.exists() and receipt.read_text()!=checksum:raise ValueError('Accepted update checksum changed')
                if not receipt.exists():atomic_bytes(receipt,checksum.encode())
                return 'identical_retry'
            if (self.folder/'commit.json').exists():raise ValueError('Round already committed')
            atomic_bytes(path,payload)
            atomic_bytes(path.with_suffix('.sha256'),hashlib.sha256(payload).hexdigest().encode())
            return 'accepted'

    def finish(self):
        with self.lock():
            commit=self.folder/'commit.json'
            if commit.exists():
                info=json.loads(commit.read_text())
                if info['contract_sha256']!=self.contract_sha256 or digest(self.folder/'global.pt')!=info['global_sha256']:raise ValueError('Committed checkpoint changed')
                for c,h in info['update_sha256'].items():
                    if digest(self.folder/(c+'.pt'))!=h:raise ValueError('Committed update changed')
                return torch.load(self.folder/'global.pt',weights_only=True,map_location='cpu')
            updates=[];hashes={};wire_bytes=0
            for client in sorted(self.contract['clients']):
                path=self.folder/(client+'.pt')
                if not path.exists():raise ValueError('Round incomplete; missing client update')
                receipt=path.with_suffix('.sha256')
                if not receipt.exists():raise ValueError('Update receipt incomplete; retry client delivery')
                if digest(path)!=receipt.read_text():raise ValueError('Accepted update checksum changed')
                data=path.read_bytes();updates.append(self.decode(data));hashes[client]=hashlib.sha256(data).hexdigest();wire_bytes+=len(data)
            state=aggregate(updates,sorted(self.contract['clients']))
            if any(not torch.isfinite(v).all() for v in state.values()):raise ValueError('Nonfinite aggregate')
            atomic_bytes(self.folder/'global.pt',serialize(state))
            info=dict(contract_sha256=self.contract_sha256,global_sha256=digest(self.folder/'global.pt'),update_sha256=hashes,
                round=self.contract['round'],unique_update_payload_bytes=wire_bytes,
                broadcast_checkpoint_bytes=(self.folder/'base.pt').stat().st_size*len(updates),
                tensor_bytes_per_model=sum(v.numel()*v.element_size() for v in self.base.values()),
                total_samples=sum(u['samples'] for u in updates),
                accounting='Serialized unique model messages only; excludes retries, protocol manifest, filesystem/network overhead; no real network transport')
            atomic_bytes(commit,json.dumps(info,sort_keys=True).encode())
            return state
