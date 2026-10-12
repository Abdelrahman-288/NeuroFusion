import argparse
import json
from pathlib import Path

from neurofusion.data import audit, build_manifest, save_json, split_patients


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NeuroFusion research foundation")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("doctor", help="Check dependencies and exercise GPU forward/backward")
    check.add_argument("--require-cuda", action="store_true")
    check.add_argument("--output", type=Path, required=True)
    manifest = commands.add_parser("manifest", help="Validate indexed NIfTI studies and fingerprint content")
    manifest.add_argument("--index", type=Path, required=True)
    manifest.add_argument("--root", type=Path, required=True)
    manifest.add_argument("--dataset-id", required=True)
    manifest.add_argument("--output", type=Path, required=True)
    split = commands.add_parser("split", help="Create patient partitions only if leakage audit passes")
    split.add_argument("--manifest", type=Path, required=True)
    split.add_argument("--seed", type=int, default=42)
    split.add_argument("--output", type=Path, required=True)
    check_data = commands.add_parser("audit", help="Audit a manifest and saved patient partitions")
    check_data.add_argument("--manifest", type=Path, required=True)
    check_data.add_argument("--splits", type=Path, required=True)
    check_data.add_argument("--output", type=Path, required=True)
    demo = commands.add_parser("demo", help="Run the data pipeline on clearly labeled synthetic fixtures")
    demo.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("Output already exists; choose a new path to preserve previous artifacts")
        if args.command == "doctor":
            from neurofusion.environment import doctor
            result = doctor(args.require_cuda)
        elif args.command == "manifest":
            result = build_manifest(args.index, args.root, args.dataset_id)
        elif args.command == "split":
            manifest_data = json.loads(args.manifest.read_text(encoding="utf-8"))
            result = split_patients(manifest_data, args.seed)
            report = audit(manifest_data, result)
            if not report["passed"]:
                print(json.dumps(report, indent=2))
                return 1
        elif args.command == "audit":
            result = audit(json.loads(args.manifest.read_text(encoding="utf-8")),
                           json.loads(args.splits.read_text(encoding="utf-8")))
        else:
            from neurofusion.demo import create_demo
            root = args.output / "synthetic_data"
            index = create_demo(root)
            manifest_data = build_manifest(index, root, "synthetic-demo-not-clinical")
            splits = split_patients(manifest_data)
            result = audit(manifest_data, splits)
            save_json(args.output / "manifest.json", manifest_data)
            save_json(args.output / "splits.json", splits)
            save_json(args.output / "audit.json", result)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
        save_json(args.output, result)
        print(json.dumps(result if args.command != "manifest" else {
            "studies": len(result["studies"]), "output": str(args.output)}, indent=2))
        return 0 if result.get("passed", True) else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
