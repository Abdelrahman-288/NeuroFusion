"""Exact nested checkpoint-state comparison for deterministic diagnostic replay."""
import torch


def state_equal(left,right):
    if isinstance(left,torch.Tensor):
        return isinstance(right,torch.Tensor) and left.dtype==right.dtype and left.shape==right.shape and torch.equal(left.cpu(),right.cpu())
    if isinstance(left,dict):
        return isinstance(right,dict) and left.keys()==right.keys() and all(state_equal(left[k],right[k]) for k in left)
    if isinstance(left,(list,tuple)):
        return type(left)==type(right) and len(left)==len(right) and all(state_equal(a,b) for a,b in zip(left,right))
    return type(left)==type(right) and left==right
