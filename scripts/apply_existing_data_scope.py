"""Apply the explicit existing-data scope while preserving historical records."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    scope = json.loads((ROOT/'configs/release_scope.json').read_text())
    archive = ROOT/'experiments/existing-data-scope-001'
    archive.mkdir(exist_ok=True)
    for name in ['configs/additional_specialists.json', 'configs/datasets.json',
                 'docs/progress_tracker.json', 'docs/release_status.json']:
        target = archive / name.replace('/', '__')
        if not target.exists():
            target.write_bytes((ROOT/name).read_bytes())
    path = ROOT/'configs/additional_specialists.json'
    value = json.loads(path.read_text())
    value['scope'] = scope['scope']
    value['dataset_downloads_allowed'] = False
    value['specialists'] = [s for s in value['specialists'] if s['id']=='eeg']
    for s in value['specialists']:
        s.update(status='pilot_trained_quality_failed', trained=True,
                 remaining='Use the existing 12 EDF recordings only. Reduce false alarms; no additional acquisition. Independent qualification is not established.')
    write(path, value)
    path = ROOT/'configs/datasets.json'
    value = json.loads(path.read_text())
    for dataset in value['datasets']:
        if dataset['id']=='ucsf-pdgm':
            dataset.update(status='local_development_and_protected_subsets_acquired',
                downloaded_mri_volumes=40, downloaded_mask_volumes=40,
                development_exams=20, protected_exams=20,
                protected_local_root='experiments/ucsf-acquisition-001/raw',
                protected_provenance='experiments/ucsf-acquisition-001/summary.json')
            dataset['limitations']=[
                '20 development exams plus 20 protected exams; not the full UCSF collection',
                'Protected cohort integrity verified; independence unresolved',
                'Development specialist failed qualification; no independent evaluation',
                'Expert review optional; no review claimed',
                'No further acquisition permitted']
    value['dataset_downloads_allowed'] = False
    value['scope'] = scope['scope']
    if not any(d['id']=='chbmit-pilot' for d in value['datasets']):
        value['datasets'].append(dict(id='chbmit-pilot', local_root='data/raw/chbmit-pilot',
            version='1.0.0 subset', recordings=12, task='eeg_seizure_event_research',
            status='pilot_trained_quality_failed', source='https://physionet.org/content/chbmit/1.0.0/',
            provenance='experiments/eeg-pilot-001/download-manifest.json',
            limitations=['Label-selected pilot', '722 false alarms in validation; no deployment qualification', 'No additional recordings permitted']))
    write(path, value)
    path = ROOT/'docs/progress_tracker.json'
    value = json.loads(path.read_text())
    value['scope'] = scope['scope']
    value['dataset_downloads_allowed'] = False
    value['scope_freeze'].update(baseline_requirement_groups=19,
        scope_amendment=scope['reason'], document='docs/CURRENT_PLAN.md')
    value['milestones'] = [m for m in value['milestones'] if m['id']=='eeg']
    value['milestones'][0]['remaining']='Reduce false alarms using existing 12-recording pilot only; no downloads'
    value['total_milestones']=len(value['milestones'])
    value['next_stage']={'name':'Finish retained software and model acceptance using existing data only',
                         'dataset_downloads_allowed':False, 'expert_review_required':False}
    write(path,value)
    banner = ('> **Current scope (10 October 2026):** Existing local BRISC, ISLES, UCSF and '
              '12-recording CHB-MIT pilot only. Missing datasets and their specialist branches '
              'are removed; no downloads. [Current completion plan](CURRENT_PLAN.md) supersedes '
              'historical acquisition and expansion steps below. Failed quality checks remain failed.\n\n')
    for name in ['SCOPE_FREEZE.md','ADDITIONAL_SPECIALISTS.md','DATASET_SETUP.md',
                 'IMPLEMENTATION_STATUS.md','PROJECT_PROGRESS.md','NEXT_MILESTONE.md']:
        path=ROOT/'docs'/name
        content=path.read_text(encoding='utf-8')
        if not content.startswith('> **Current scope'):
            path.write_text(banner+content,encoding='utf-8')
    for name in ['README.md','NeuroFusion_Project_Manual.md']:
        path=ROOT/name
        content=path.read_text(encoding='utf-8')
        if not content.startswith('> **Current scope'):
            path.write_text(banner.replace('(CURRENT_PLAN.md)','(docs/CURRENT_PLAN.md)')+content,encoding='utf-8')
    print('Existing-data scope applied. No network requests performed.')


if __name__=='__main__':main()
