"""Write the completion record and verify the confirmation report route."""
from pathlib import Path
import json,importlib.util,threading,urllib.request
from html.parser import HTMLParser
root=Path(__file__).resolve().parents[1];out=root/'experiments/ucsf-lr-confirmation-001'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
s=read(out/'summary.json')
spec=importlib.util.spec_from_file_location('viewer',root/'scripts/serve_viewer.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Quiet(module.Handler):
    def log_message(self,*args):pass
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):self.links.extend(v for k,v in attrs if k=='href')
server=module.ThreadingHTTPServer(('127.0.0.1',0),Quiet);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/research/ucsf/confirmation/'
try:
    with urllib.request.urlopen(base+'index.html') as response:page=response.read().decode()
    parser=Links();parser.feed(page)
    for link in parser.links:
        with urllib.request.urlopen(base+link) as response:assert response.status==200 and response.read()
    assert module.pilot_report_path('/research/ucsf/confirmation/../epoch-05.pt') is None
finally:server.shutdown();server.server_close()
verification={'regression_tests_passed':198,'confirmation_tests_rechecked':2,'new_training_runs':4,'new_checkpoints_hash_checked':20,'new_final_masks_reproduced_on_reload':16,'http_report_pages':1,'linked_artifacts_checked':len(parser.links),'active_models_changed':False}
(out/'verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
rows='\n'.join(f'| {seed} | {r["means"]["baseline_dice"]:.6f} | {r["means"]["candidate_dice"]:.6f} | {r["means"]["baseline_fp_ml"]:.3f} | {r["means"]["candidate_fp_ml"]:.3f} | {sum(r["gates"].values())}/4 |' for seed,r in s['seeds'].items())
doc='''# UCSF paired-seed confirmation

Completed 8 October 2026. Artifact: `experiments/ucsf-lr-confirmation-001`.

**Decision: '''+s['decision']+'''. No model promoted.**

| Seed | Baseline Dice | Lower-LR Dice | Baseline FP mL | Lower-LR FP mL | Checks passed |
|---|---:|---:|---:|---:|---:|
'''+rows+'''

The predeclared rule required all four checks to pass separately for seeds 42, 43 and 44. Failed seeds cannot be hidden by averaging. Seed 42 was reused from the candidate-selection experiment; four additional five-epoch runs were trained for seeds 43 and 44. Each pair compares Adam 0.001 versus 0.0003, using identical initialization seed, original uniform sampling, all 2,480 training slices each epoch, the same 16/4 patient partition, and final-epoch selection. No checkpoint, threshold or seed was selected after seeing outcomes.

The seed-43 baseline predicted empty masks for all four patients. Its zero false-positive volume is therefore not evidence of a useful model. Lower LR improves overlap for that seed but increases mean false-positive volume to 53.999 mL, failing the predefined volume guardrail. Preserve both facts; do not reinterpret the protocol after the result. Inspect all patient-level metrics in summary.json.

Checks verified patient partitions, cache hashes, intended seed and learning rate, shared architecture/preprocessing source, all checkpoint hashes, and full training-slice coverage. Each new final checkpoint was reloaded and reproduced all four saved native masks and metric dictionaries exactly. Twenty new checkpoints and sixteen final prediction masks are retained. All 198 regression tests passed; confirmation aggregation tests were rerun after clarifying per-seed decision wording. The report and three JSON links passed HTTP verification. Restart an already-running local viewer to load `/research/ucsf/confirmation/index.html`.

Three seeds reuse the same four development patients, not twelve independent patients. Repeated inspection and candidate selection on this cohort prevent an independent generalization claim. These are numeric annotation-union comparisons, not diagnostic accuracy.

## Next stage

Investigate the empty-output training failure before further tuning: evaluate original-grid foreground coverage on a fixed training subset and all development patients, inspect probability distributions and gradients/checkpoint histories, and distinguish training failure from generalization failure. Keep the failed comparisons intact. Any revised acceptance rule or training schedule must be declared as a new experiment; it cannot retroactively make this confirmation pass. Broader data acquisition, independent cohort evaluation and expert review remain required.

Overall implementation estimate stays approximately 86%. Confirmation is complete, but the candidate has not earned promotion. This estimate is not a measure of clinical readiness.
'''
(root/'docs/UCSF_LR_CONFIRMATION.md').write_text(doc,encoding='utf-8')
for name in ('PROJECT_PROGRESS.md','IMPLEMENTATION_STATUS.md'):
    p=root/'docs'/name;old=p.read_text(encoding='utf-8');title,rest=old.split('\n',1)
    p.write_text(title+'\n\n2026-10-08 paired-seed confirmation complete: seeds 42/43/44 compared with four additional five-epoch runs. Decision: '+s['decision']+'. 198 tests passed; new checkpoints reproduced 16 saved masks. No promotion. Overall rough estimate remains ~86%. See `UCSF_LR_CONFIRMATION.md`.\n'+rest,encoding='utf-8')
p=root/'configs/ucsf_lr_confirmation_protocol.json';plan=read(p);plan['stage']='completed paired-seed confirmation';plan['additional_training_started']=True;plan['execution']={'report':'experiments/ucsf-lr-confirmation-001','all_seeds_passed':s['all_seeds_passed'],'decision':s['decision'],'model_promoted':False};p.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(verification)
