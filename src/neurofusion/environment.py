"""Measured environment diagnostics with a small GPU forward/backward test."""
import platform
import sys
import time
from importlib.metadata import version, PackageNotFoundError


def doctor(require_cuda: bool = False) -> dict:
    result = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
              "packages": {}, "cuda_available": False, "passed": False}
    for name in ("neurofusion", "torch", "numpy", "nibabel", "pytest"):
        try:
            result["packages"][name] = version(name)
        except PackageNotFoundError:
            result["packages"][name] = "not installed"
    try:
        import torch
        result["cuda_build"] = torch.version.cuda
        result["cuda_available"] = torch.cuda.is_available()
        if require_cuda and not result["cuda_available"]:
            result["error"] = "CUDA required but unavailable; install a compatible official CUDA PyTorch wheel"
            return result
        device = "cuda" if result["cuda_available"] else "cpu"
        if device == "cuda":
            result["gpu"] = torch.cuda.get_device_name(0)
            result["vram_bytes"] = torch.cuda.get_device_properties(0).total_memory
            torch.cuda.reset_peak_memory_stats()
        start = time.perf_counter()
        model = torch.nn.Conv3d(3, 1, 3, padding=1).to(device)
        inputs = torch.randn(1, 3, 16, 16, 16, device=device)
        loss = model(inputs).square().mean()
        loss.backward()
        if device == "cuda":
            torch.cuda.synchronize()
            result["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
        result.update(device=device, smoke_seconds=time.perf_counter() - start,
                      loss=float(loss.detach().cpu()),
                      passed=bool(torch.isfinite(loss).item() and torch.isfinite(model.weight.grad).all().item()))
        result["note"] = "Small synthetic convolution test; not a training benchmark or clinical evaluation"
    except (ImportError, RuntimeError, OSError) as exc:
        result["error"] = str(exc)
    return result
