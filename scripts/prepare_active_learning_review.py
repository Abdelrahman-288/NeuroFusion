"""Create a review workspace for existing development training patients only."""
import argparse
import json
from pathlib import Path
import shutil
from neurofusion.external_import import digest

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    parts=json.loads((ROOT/'experiments/ucsf-specialist-plan-001/partitions.json').read_text(encoding='utf-8'))
    protected={r['patient_id'] for r in json.loads((ROOT/'experiments/ucsf-acquisition-001/summary.json').read_text(encoding='utf-8'))['results']}
    source=(ROOT/'data/raw/ucsf-pdgm-v5').resolve();rows=[];jobs=[]
    for row in parts['records']:
        if row['role']!='train':continue
        if row['patient_id'] in protected:raise ValueError('Protected overlap')
        files=[]
        for key,suffix in [('image','T1c'),('mask','tumor_segmentation')]:
            src=(source/row[key]['path']).resolve()
            if not src.is_relative_to(source) or digest(src)!=row[key]['sha256']:raise ValueError('Source mismatch')
            name=f'{row["exam_id"]}_{suffix}.nii.gz';files.append({'path':name,'sha256':row[key]['sha256']});jobs.append((src,name,row[key]['sha256']))
        rows.append({'exam_id':row['exam_id'],'patient_id':row['patient_id'],'status':'integrity_verified','files':files})
    a.output.mkdir(parents=True,exist_ok=False)
    for src,name,checksum in jobs:
        shutil.copy2(src,a.output/name)
        if digest(a.output/name)!=checksum:raise ValueError('Copy checksum mismatch')
    (a.output/'summary.json').write_text(json.dumps({'purpose':'Development annotation workflow; not the protected evaluation cohort','results':rows},indent=2),encoding='utf-8')
    print(json.dumps({'training_patients':len(rows),'review_accounts_created':0,'annotations_created':0}))

if __name__=='__main__':main()
