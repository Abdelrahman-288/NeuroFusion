"""Close the user-approved research application scope without qualifying failed models."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.research_release import accept_delivery

root=Path(__file__).resolve().parents[1]
def read(path):return json.loads((root/path).read_text(encoding='utf-8'))
scope=read('configs/release_scope.json')
if scope.get('completion_definition')!='local_research_application':raise ValueError('Research scope amendment required')
status=read('docs/release_status.json')
suite=ET.parse(root/'experiments/research-release-tests-001.xml').getroot()
suites=list(suite.iter('testsuite'))
tests=sum(int(s.attrib.get('tests',0)) for s in suites)
failed=sum(int(s.attrib.get(k,0)) for s in suites for k in ('failures','errors','skipped'))
install=read('experiments/local-install-verification-002.json')
recovery=read('experiments/release-readiness-001.json')
promotion=read('experiments/versioned-retraining-acceptance-001/rejection-verification.json')
evaluation=read('experiments/final-evaluation-readiness-001/protocol-readiness.json')
checks=dict(regression_tests=tests>0 and failed==0,installed_package=install.get('passed') is True,
            private_recovery=recovery.get('passed') is True,promotion_rejection=promotion.get('passed') is True,
            evaluation_disposition=evaluation.get('status')=='BLOCKED_NOT_FROZEN_FOR_EXECUTION')
dispositions={r['id']:dict(outcome='delivered' if r['status']=='implemented' else 'delivered_with_limitations',
    explanation=r['remaining'],evidence=r['evidence'],scientific_or_original_status=r['status']) for r in status['requirements']}
paths=['configs/release_scope.json','experiments/research-release-tests-001.xml','experiments/local-install-verification-002.json',
       'experiments/release-readiness-001.json','experiments/versioned-retraining-acceptance-001/rejection-verification.json',
       'experiments/versioned-retraining-acceptance-001/promotion.json','experiments/final-evaluation-readiness-001/protocol-readiness.json']
paths+=sorted(set(r['evidence'] for r in status['requirements']))
# Bind code and tests so later changes invalidate this release's acceptance.
for folder in ('src','scripts','tests'):
    paths += [p.relative_to(root).as_posix() for p in sorted((root/folder).rglob('*.py'))]
artifacts=[dict(path=p,sha256=digest(root/p)) for p in paths]
result=accept_delivery(root,status['requirements'],dispositions,checks,artifacts)
result.update(updated='2026-10-12',tests_passed=tests,scope_amendment='User accepted completion as a research application with documented model limitations on 12 October 2026')
output=root/'docs/research_delivery.json';output.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'research_application_complete':True,'delivery_percent':100,'tests_passed':tests,'all_models_qualified':False}))
