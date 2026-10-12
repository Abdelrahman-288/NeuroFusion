"""Local simulation primitives. Updates offer no privacy or poisoning protection."""
import torch


def aggregate(updates, expected_clients):
    if len(updates)!=len(expected_clients) or {u['client'] for u in updates}!=set(expected_clients):
        raise ValueError('Exactly one update from every configured client required')
    reference=updates[0]['state'];total=0
    for update in updates:
        if type(update['samples']) is not int or update['samples']<=0:raise ValueError('Positive sample count required')
        if update['state'].keys()!=reference.keys():raise ValueError('Incompatible model keys')
        total+=update['samples']
        for key,value in update['state'].items():
            if value.shape!=reference[key].shape or value.dtype!=reference[key].dtype or not torch.isfinite(value).all():raise ValueError('Invalid or incompatible update')
            if not value.is_floating_point() and not torch.equal(value,reference[key]):raise ValueError('Nonfloating buffers differ')
    return {key:sum(u['state'][key].double()*u['samples']/total for u in updates).to(value.dtype) if value.is_floating_point() else value.clone() for key,value in reference.items()}
