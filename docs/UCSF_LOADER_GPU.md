# UCSF specialist loader and GPU readiness

2026-10-08. Cache: experiments/ucsf-specialist-cache-001; GPU evidence:
experiments/ucsf-specialist-smoke-001. Reproduce using scripts/prepare_ucsf_specialist.py
and scripts/smoke_ucsf_specialist.py with --help.

All 20 source pairs were checked against source hashes, patient-role assignments,
geometry and numeric labels. Every canonical slice was prepared at 240 pixels.
The loader uses read-only memory-mapped uint8 arrays, converts each input to
float32 /255 and targets to binary float32. Dataset roles remain 16 training
patients (2,480 slices) and 4 development-validation patients (620 slices).
Empty slices are retained. Cache arrays and geometry are checksummed on opening;
patient role crossings, path escapes and unexpected shapes/targets are rejected.

Normalization clarification: this implementation uses the existing adapter's
nonzero-volume p1/p99 clipping followed by uint8 rounding and division by 255.
That quantization is now explicit before full training. No BRISC weights are used;
a new instance of the shared 8/16/32-channel U-Net architecture is initialized.

RTX 4070 Laptop GPU smoke result: two mixed-precision optimizer steps with batch
8 and 240x240 input, finite losses/gradients and confirmed parameter updates.
Losses were 1.7280 and 1.5866 on different batches; they are not a convergence
claim. Peak PyTorch allocated memory was 345.4 MiB, not total device usage.
No checkpoint saved, no validation inference and no full training run occurred.

190 tests passed in 35.62 seconds, including three loader checks for scaling and
empty-slice retention, altered cache hashes and patient-role crossings. Source
snapshots and cache-manifest hash are archived with the smoke evidence.

Next: implement native-grid per-patient development validation, checkpointed
five-epoch training and result reporting. Numeric foreground remains an engineering
target; expert alignment, clinical semantics and independent evaluation remain
pending. Overall rough implementation estimate advances to approximately 84%.
