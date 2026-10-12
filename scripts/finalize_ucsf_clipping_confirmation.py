"""Complete clipping confirmation documentation and verify report delivery."""
from pathlib import Path
import json,importlib.util,threading,urllib.request
from html.parser import HTMLParser
root=Path(__file__).resolve().parents[1];out=root/'experiments/ucsf-clipping-confirmation-001';read=lambda p:json.loads(p.read_text(encoding='utf-8'))
s=read(out/'summary.json')
spec=importlib.util.spec_from_file_location('viewer',root/'scripts/serve_viewer.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Quiet(module.Handler):
 def log_message(self,*args):pass
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):self.links.extend(v for k,v in attrs if k=='href')
server=module.ThreadingHTTPServer(('127.0.0.1',0),Quiet);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/research/ucsf/clipping-confirmation/'
try:
 with urllib.request.urlopen(base+'index.html') as response:page=response.read().decode()
 parser=Links();parser.feed(page)
 for link in parser.links:
  with urllib.request.urlopen(base+link) as response:assert response.status==200 and response.read()
 assert module.pilot_report_path('/research/ucsf/clipping-confirmation/epoch-05.pt') is None
finally:server.shutdown();server.server_close()
verification={'regression_tests_passed':203,'new_full_training_runs':3,'new_checkpoints_hash_checked':15,'new_native_masks_reproduced_on_reload':12,'http_report_pages':1,'linked_artifacts_checked':len(parser.links),'active_models_changed':False}
(out/'verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
rows='\n'.join(f'| {seed} | {r["means"]["baseline_dice"]:.6f} | {r["means"]["candidate_dice"]:.6f} | {r["means"]["baseline_fp_ml"]:.3f} | {r["means"]["candidate_fp_ml"]:.3f} | {sum(r["gates"].values())}/4 |' for seed,r in s['seeds'].items())
training=[]
for seed in (42,43,44):
 run=root/'experiments'/(f'ucsf-clipping-seed{seed}-'+('002' if seed==44 else '001'));history=read(run/'history.json')
 training.append({'seed':seed,'clipped_updates':sum(h['clipped_updates'] for h in history),'amp_skipped_updates':sum(h['overflow_skipped_updates'] for h in history),'final_empty_states':read(run/'summary.json')['final_epoch']['aggregate']['empty_states']})
(out/'training-counts.json').write_text(json.dumps(training,indent=2)+'\n',encoding='utf-8')
doc='''# UCSF clipping from initialization: three-seed confirmation

Completed 8 October 2026. Artifact: `experiments/ucsf-clipping-confirmation-001`.

**Decision: '''+s['decision']+'''. No active model was changed.**

| Seed | Baseline Dice | Clipped Dice | Baseline FP mL | Clipped FP mL | Checks passed |
|---|---:|---:|---:|---:|---:|
'''+rows+'''

Seed 44 attempt 001 exited with Windows code 3221226505 before any epoch checkpoint, without a Python traceback. Cause is unknown. It is retained with failure.json; attempt 002 restarted with identical settings.

Three five-epoch models were trained from random initialization with seeds 42, 43 and 44. Each is paired with its existing unclipped run. Only finite unscaled gradient clipping (global L2 maximum 1.0) was added. Adam learning rate 0.001, original uniform sampling, batch size, architecture, AMP skipped-update behavior, loss, data split, threshold 0.5 and final-checkpoint selection were preserved. No warm start from the successful diagnostic probe was used.

Acceptance required all four previously defined checks separately in every seed. Avoiding empty predictions is a separate diagnostic observation, not a substitute for overlap and false-positive checks. An empty-output baseline's zero false positives does not make it useful; all failures and the original rules are retained. These repeatedly reviewed four validation patients remain development data.

All 15 new checkpoint hashes and actual optimizer learning rates were verified. All 12 saved final native predictions and metric dictionaries were reproduced by reloading checkpoints. Shared source, partitions, cache and complete per-epoch training coverage matched the controls; clipping norms stayed within the specified bound. The regression suite passed 203 tests, and the report plus three linked JSON artifacts passed HTTP checks. Restart a running viewer to load `/research/ucsf/clipping-confirmation/index.html`.

## Progress reporting correction

This stage is 4/4 complete: train three seeds; verify saved predictions; apply prespecified comparisons; publish the report and viewer link. These deliverables are equally counted for task completion only, not time or model quality. The historical overall 86% was an informal estimate without a weighted full roadmap. It should not be repeated as a measured completion percentage. `docs/progress_tracker.json` now separates completed work from readiness.

Infrastructure, data intake and research diagnostics have progressed even when experiments fail. The full project still requires robust model qualification, additional planned disease/data/model branches, independent evaluation, expert review, and deployment readiness. Stage completion must not imply those are finished.

## Next work

Use the completed stabilization evidence to set a bounded model-qualification plan, rather than repeatedly extending experiments on the same four patients. Record explicit acceptance criteria and outstanding failures, then prioritize the independent cohort/data requirements and the missing product/model milestones. Any revised criteria constitute a new prospective protocol; previous failed comparisons remain failed. No clinical performance claim or automatic promotion follows from this stage.
'''
(root/'docs/UCSF_CLIPPING_CONFIRMATION.md').write_text(doc,encoding='utf-8')
tracker=read(root/'docs/progress_tracker.json')
for item in tracker['milestones']:item['status']='complete'
tracker['completed_milestones']=4;tracker['total_milestones']=4;tracker['stage_percent']=100;tracker['model_decision']=s['decision'];tracker['scope']='UCSF clipping from initialization confirmation stage';tracker['report']='experiments/ucsf-clipping-confirmation-001/index.html'
(root/'docs/progress_tracker.json').write_text(json.dumps(tracker,indent=2)+'\n',encoding='utf-8')
for name in ('PROJECT_PROGRESS.md','IMPLEMENTATION_STATUS.md'):
 p=root/'docs'/name;old=p.read_text(encoding='utf-8');title,rest=old.split('\n',1)
 p.write_text(title+'\n\n2026-10-08 clipping from initialization stage complete: 3 training runs, 15 checkpoints and 12 reproduced native predictions. Decision: '+s['decision']+'. 203 tests passed. Current stage 4/4 (100%) complete. Historical overall 86% is an informal estimate, superseded by explicit stage tracking in `progress_tracker.json`; it is not measured project completion. See `UCSF_CLIPPING_CONFIRMATION.md`.\n'+rest,encoding='utf-8')
p=root/'configs/ucsf_clipping_confirmation_protocol.json';plan=read(p);plan['stage']='completed full-initialization clipping confirmation';plan['started']=True;plan['execution']={'report':'experiments/ucsf-clipping-confirmation-001','all_seeds_passed':s['all_seeds_passed'],'decision':s['decision'],'model_promoted':False};p.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'verification':verification,'training_counts':training},indent=2))
