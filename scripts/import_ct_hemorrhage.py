"""Prepare authorized local RSNA CT slices without claiming a trained specialist."""
import argparse
import hashlib
from pathlib import Path
import numpy as np
import pydicom
from PIL import Image
from neurofusion.specialist_inputs import ct_windows,rsna_hemorrhage_labels,HEMORRHAGE_LABELS
from neurofusion.cohort import digest
from neurofusion.data import save_json
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dicom-root',type=Path,required=True);parser.add_argument('--labels',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists():parser.error('Fresh output required')
labels=rsna_hemorrhage_labels(args.labels);sources=sorted(args.dicom_root.rglob('*.dcm'))
if not sources:parser.error('No local DICOM data; obtain authorized training data first')
records=[];seen=set();args.output.mkdir(parents=True)
for path in sources:
    identity=path.stem
    if identity in seen or identity not in labels:raise ValueError('Duplicate slice ID or missing labels')
    seen.add(identity)
    header=pydicom.dcmread(path,stop_before_pixels=True)
    if not getattr(header,'PatientID',''):raise ValueError('Patient identity required before split')
    patient=hashlib.sha256(('ct-patient-v1:'+str(header.PatientID)).encode()).hexdigest()
    bucket=int(patient[:8],16)%10
    partition='train' if bucket<7 else 'validation' if bucket<9 else 'holdout'
    # Keep holdout pixels unprocessed and out of development arrays.
    record={'image_id':identity,'patient_group':patient,'partition':partition,'source_sha256':digest(path),'labels':[labels[identity][k] for k in HEMORRHAGE_LABELS]}
    if partition!='holdout':
        windows,metadata=ct_windows(path)
        resized=np.stack([np.asarray(Image.fromarray(a).resize((128,128),Image.Resampling.BILINEAR)) for a in windows])
        target=args.output/'arrays'/f'{identity}.npy';target.parent.mkdir(exist_ok=True);np.save(target,resized,allow_pickle=False)
        record.update(array=str(target.relative_to(args.output)),array_sha256=digest(target))
    records.append(record)
save_json(args.output/'manifest.json',{'task':'noncontrast-head-ct-hemorrhage-slice-classification','labels':list(HEMORRHAGE_LABELS),'records':records,
    'labels_sha256':digest(args.labels),'patient_identity_verified':False,'trained':False,'source_root':str(args.dicom_root.resolve()),
    'limitations':'PatientID hashing groups documented identities but does not prove independence. Contrast/anatomy require provenance review. Slice labels do not train bleeding segmentation.'})
print(f'Prepared {len(records)} source records; no training or qualification claimed')
