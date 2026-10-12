"""Explicit private-state backup/restore and one-shot local health checks."""
import argparse,json
from pathlib import Path
from neurofusion.release_operations import backup_private,restore_private,monitor_local

root=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
b=s.add_parser('backup');b.add_argument('--source',type=Path,required=True);b.add_argument('--archive',type=Path,required=True)
r=s.add_parser('restore');r.add_argument('--archive',type=Path,required=True);r.add_argument('--destination',type=Path,required=True)
m=s.add_parser('monitor');m.add_argument('--storage',type=Path,default=root/'experiments/local-viewer');m.add_argument('--output',type=Path,required=True)
a=p.parse_args()
if a.action=='backup':result=backup_private(a.source,a.archive)
elif a.action=='restore':result=restore_private(a.archive,a.destination)
else:result=monitor_local(root,a.storage)
if a.action=='monitor':
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
if a.action=='monitor' and not result['healthy']:raise SystemExit(2)
