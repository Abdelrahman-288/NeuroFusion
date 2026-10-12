"""Import explicitly mapped pilot scans; report missing/failed cases without inference."""
import argparse
import json
from pathlib import Path
from neurofusion.external_import import import_pilot


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('root','pilot','manifest','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=import_pilot(args.root,json.loads(args.pilot.read_text()),
                        json.loads(args.manifest.read_text()),args.output)
    print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
    if result['failed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
