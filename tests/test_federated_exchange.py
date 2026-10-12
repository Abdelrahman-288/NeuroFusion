import io,json
import pytest
import torch
from neurofusion.federated_exchange import RoundExchange,serialize


@pytest.fixture
def exchange(tmp_path):return RoundExchange.create(tmp_path/'round',{'w':torch.tensor([0.])},2,'a'*64,{'a':1,'b':3})


def test_partial_recovery_retry_and_commit(exchange):
    a=exchange.encode('a',{'w':torch.tensor([2.])});b=exchange.encode('b',{'w':torch.tensor([6.])})
    assert exchange.submit(a)=='accepted'
    with pytest.raises(ValueError,match='incomplete'):exchange.finish()
    reopened=RoundExchange(exchange.folder);assert reopened.submit(a)=='identical_retry'
    reopened.submit(b);assert reopened.finish()['w'].item()==5
    assert RoundExchange(exchange.folder).finish()['w'].item()==5
    info=json.loads((exchange.folder/'commit.json').read_text())
    assert info['unique_update_payload_bytes']==len(a)+len(b)
    assert info['broadcast_checkpoint_bytes']==2*(exchange.folder/'base.pt').stat().st_size
    assert info['tensor_bytes_per_model']==4


@pytest.mark.parametrize('field,value',[('round',1),('protocol_sha256','b'*64),('base_sha256','c'*64),('samples',2),('client','unknown')])
def test_stale_or_wrong_contract_rejected(exchange,field,value):
    data=torch.load(io.BytesIO(exchange.encode('a',{'w':torch.tensor([1.])})),weights_only=True)
    data[field]=value
    with pytest.raises(ValueError):exchange.submit(serialize(data))
    assert not (exchange.folder/'a.pt').exists()


def test_corrupt_conflicting_and_nonfinite_updates(exchange):
    for payload in [b'truncated',exchange.encode('a',{'w':torch.tensor([float('nan')])}),exchange.encode('a',{'w':torch.ones(2)})]:
        with pytest.raises(ValueError):exchange.submit(payload)
    exchange.submit(exchange.encode('a',{'w':torch.ones(1)}))
    with pytest.raises(ValueError,match='Conflicting'):exchange.submit(exchange.encode('a',{'w':torch.zeros(1)}))


def test_crash_before_commit_recovers_and_preserves_updates(exchange,monkeypatch):
    exchange.submit(exchange.encode('a',{'w':torch.tensor([2.])}));exchange.submit(exchange.encode('b',{'w':torch.tensor([6.])}))
    from neurofusion import federated_exchange as module
    real=module.atomic_bytes
    def fail(path,data):
        if path.name=='commit.json':raise OSError('simulated crash after global checkpoint')
        real(path,data)
    with monkeypatch.context() as context:
        context.setattr(module,'atomic_bytes',fail)
        with pytest.raises(OSError):exchange.finish()
    assert not (exchange.folder/'commit.json').exists()
    assert RoundExchange(exchange.folder).finish()['w'].item()==5


def test_changed_base_commit_and_writer_lock(exchange):
    lock=exchange.folder/'writer.lock';lock.write_text('')
    with pytest.raises(ValueError,match='writer'):exchange.finish()
    lock.unlink()
    exchange.submit(exchange.encode('a',{'w':torch.tensor([2.])}));exchange.submit(exchange.encode('b',{'w':torch.tensor([6.])}));exchange.finish()
    (exchange.folder/'global.pt').write_bytes(b'changed')
    with pytest.raises(ValueError,match='checkpoint'):RoundExchange(exchange.folder).finish()
    (exchange.folder/'base.pt').write_bytes(b'changed')
    with pytest.raises(ValueError,match='Base'):RoundExchange(exchange.folder)


def test_partial_update_corruption_and_interrupted_receipt(exchange):
    payload=exchange.encode('a',{'w':torch.tensor([2.])});exchange.submit(payload)
    (exchange.folder/'a.sha256').unlink()
    with pytest.raises(ValueError,match='receipt incomplete'):exchange.finish()
    assert RoundExchange(exchange.folder).submit(payload)=='identical_retry'
    (exchange.folder/'a.pt').write_bytes(exchange.encode('a',{'w':torch.tensor([8.])}))
    with pytest.raises(ValueError,match='checksum'):exchange.finish()


def test_reordered_delivery_has_same_aggregate(exchange):
    exchange.submit(exchange.encode('b',{'w':torch.tensor([6.])}))
    exchange.submit(exchange.encode('a',{'w':torch.tensor([2.])}))
    assert exchange.finish()['w'].item()==5


def test_extra_data_and_oversized_payload_rejected(exchange):
    data=torch.load(io.BytesIO(exchange.encode('a',{'w':torch.ones(1)})),weights_only=True)
    data['raw_images']=torch.zeros(1)
    with pytest.raises(ValueError,match='Unexpected'):exchange.submit(serialize(data))
    with pytest.raises(ValueError,match='bound'):exchange.submit(b'x'*1000000)
