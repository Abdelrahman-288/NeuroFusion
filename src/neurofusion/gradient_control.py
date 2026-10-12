"""Finite global gradient clipping applied after AMP unscaling."""
import torch


def clip_unscaled_gradients(parameters, max_norm=1.0):
    parameters=list(parameters)
    if max_norm<=0 or not torch.isfinite(torch.tensor(max_norm)):
        raise ValueError('Positive finite clipping norm required')
    before=torch.nn.utils.clip_grad_norm_(parameters,max_norm,error_if_nonfinite=True)
    after=torch.cat([p.grad.detach().flatten().double() for p in parameters if p.grad is not None]).norm()
    return float(before),float(after)
