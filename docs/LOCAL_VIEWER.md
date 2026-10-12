# Local prediction viewer

Implemented 2026-10-06. This is a local research prototype, not a diagnostic service.

## Start on this laptop

```powershell
Set-Location D:\NeuroFusion
.\scripts\launch_viewer.ps1
```

Open http://127.0.0.1:8766. If PowerShell blocks scripts, use the foreground
server command below and open the address yourself. Ctrl+C stops that server.

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts/serve_viewer.py
```

Select the analysis, choose a compatible file, confirm its input type, and click
Analyze locally. Inspect the red overlay, adjust opacity, and download the result
JSON or probability array. DWI results also provide a slice slider.

## Supported tasks

| Task | Input | Models | Output |
|---|---|---|---|
| Tumor image | BRISC-style 2D T1 MRI PNG/JPEG | TumorCNN classifier and TumorUNet segmenter | Four uncalibrated class scores; independent region overlay; native-size NPZ probability |
| Stroke DWI | Single 3D DWI NIfTI, millimeter units | Component-balanced 3D DWI U-Net | Slice overlays; native-grid NIfTI probability with original affine |

Upload limit is 25 MiB. Tumor inputs are limited to 4 million pixels; DWI inputs
to 16 million voxels and 512 per axis. The user selects the modality; the software
cannot establish that an uploaded image is the correct sequence. DICOM and 4D
volumes are not supported. The DWI/ADC experiment is not exposed because its
development results underperformed the selected DWI baseline.

The segmenter was evaluated on tumor-positive images only. Classifier and
segmenter predictions may disagree: neither gates the other. The no_tumor class
does not establish brain health. Threshold 0.5 is fixed and uncalibrated. DWI
preview proportions follow voxels, not physical distances. No universal danger
score, clinical finding or treatment recommendation is generated.

## Implementation and storage

- `src/neurofusion/inference.py`: label-free preprocessing, hash-pinned model
  loading, common version-1 JSON result and visualization exports.
- `scripts/predict.py`: command-line inference with a fresh output directory.
- `scripts/serve_viewer.py`: loopback-only HTTP server, persistent background jobs, compatible task/extension checks and restricted
  generated-result routes.
- `viewer/index.html`: upload, scores, overlays, slices and download links.
- `experiments/local-viewer/uploads`: retained uploaded copies.
- `experiments/local-viewer/results/<job>`: retained outputs for each random job ID.
- `experiments/local-viewer/server*.log`: launcher logs.

Files persist locally until manually removed. SQLite job persistence, a bounded background queue and saved-result history are
implemented; see `BACKGROUND_JOBS.md`. Authentication and deployment remain pending. This server must remain bound to
127.0.0.1; it is not intended for public hosting. It serves the viewer and generated
results, rather than exposing the project or raw dataset directories.

Example command-line use:

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts/predict.py --task tumor-image --input C:\path\image.png --output experiments\my-prediction
```

The JSON records input SHA-256, task, device, model/checkpoint hashes, scores when
applicable, visualization filenames and limitations. Inference does not read
reference labels. Models use the existing trained local checkpoints; starting
the viewer does not retrain them.

## Verification

96 automated tests passed; pip check found no broken requirements. Real development
examples reproduced both saved segmentation outputs exactly; classifier maximum
score difference was 8.94e-8. Evidence is in
`experiments/inference-integration-002/verification.json`.
HTTP checks cover health, result downloads, invalid task, rejected Host/Origin,
required request header, traversal rejection and hidden dataset routes; evidence
is in `experiments/local-viewer/http-verification.json`.

Background jobs and saved-result history are now implemented. Downloadable HTML/JSON research reports are implemented; see `RESEARCH_REPORTS.md`. Technical input-quality checks are now implemented; see `INPUT_QUALITY.md`. Next: development robustness evaluation. Local review notes and slice annotations are
implemented; see `HUMAN_REVIEW.md`. External evaluation, calibration and further specialists
remain separate research milestones.
