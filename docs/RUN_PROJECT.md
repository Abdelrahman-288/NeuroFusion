# Run NeuroFusion locally

Start the local upload viewer to run the trained tumor classifier, tumor segmenter
or DWI stroke segmenter. See `LOCAL_VIEWER.md` for supported inputs and limitations.

```powershell
Set-Location D:\NeuroFusion
.\scripts\launch_viewer.ps1
```

Open http://127.0.0.1:8766. No training is required.

## Historical training dashboards

The static dashboards remain available separately.

From PowerShell:

```powershell
Set-Location D:\NeuroFusion
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\launch_dashboard.ps1
```

The browser opens the comparison dashboard. It links to the voxel-versus-
component-sampling results. Other useful pages are:

```text
http://127.0.0.1:8765/experiments/dwi-component-001/progress.html
http://127.0.0.1:8765/experiments/lesion-analysis-component-001/index.html
http://127.0.0.1:8765/experiments/lesion-analysis-component-001/error-gallery/index.html
http://127.0.0.1:8765/experiments/dwi-component-001/MODEL_CARD.md
```

To check the installation and tests:

```powershell
$python = '.\.venv-neurofusion\Scripts\python.exe'
& $python -m pytest -q
& $python -m pip check
```

The saved model outputs are already available in
`experiments\dwi-component-001\predictions`. No training is needed just to view
the dashboards. Training again requires the downloaded ISLES data, a working CUDA
GPU, and a fresh output directory; existing runs are protected from overwrite.

This is research software. The implemented models support BRISC-style tumor images and ISLES-style DWI
stroke segmentation. This is not a diagnostic application.
