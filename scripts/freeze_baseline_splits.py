"""Freeze the reviewed initial split without changing patient assignments."""
import hashlib
import json
from pathlib import Path
from neurofusion.data import save_json

root=Path(__file__).resolve().parents[1]
folder=root/'experiments/isles-curated-001'
output=folder/'frozen-splits-v1.json'
if output.exists():
    raise SystemExit('Frozen split already exists; no overwrite permitted')
splits=json.loads((folder/'draft-splits.json').read_text())
review=json.loads((root/'experiments/split-review-001.json').read_text())
digest=hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest()
if digest!=review['manifest_sha256']:
    raise ValueError('Reviewed manifest has changed')
splits.update(frozen=True,manifest_sha256=digest,version='baseline-v1',
              review_sha256=hashlib.sha256((root/'experiments/split-review-001.json').read_bytes()).hexdigest(),
              design_note='Retained initial seed-42 assignments before model fitting. Mixed-site, not stratified. Site and lesion-size imbalance documented; no external-site claim.')
save_json(output,splits)
print(output)
