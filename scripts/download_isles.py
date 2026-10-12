"""Download the pinned public ISLES release with resume, checksums and provenance."""
from neurofusion.download_policy import require_dataset_download
require_dataset_download()
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import time
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "downloads" / "isles-2022-v2.3.1"
API = "https://zenodo.org/api/records/7960856"


def fetch_file(item):
    target = DEST / item["key"]
    partial = target.with_suffix(target.suffix + ".part")
    if Path(item["key"]).name != item["key"]:
        raise ValueError("Unexpected remote filename")
    if not target.exists():
        for attempt in range(4):
            offset = partial.stat().st_size if partial.exists() else 0
            if offset == item["size"]:
                break
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            try:
                request = urllib.request.Request(item["links"]["self"], headers=headers)
                with urllib.request.urlopen(request, timeout=60) as response:
                    resumed = offset > 0 and response.status == 206
                    if resumed and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                        raise ValueError("Unexpected server resume range")
                    written = offset if resumed else 0
                    last = time.monotonic()
                    with partial.open("ab" if resumed else "wb") as stream:
                        while block := response.read(1024 * 1024):
                            stream.write(block)
                            written += len(block)
                            if time.monotonic() - last >= 20:
                                print(f"{item['key']}: {written / item['size']:.1%} ({written // 1048576} MiB)", flush=True)
                                last = time.monotonic()
                if written != item["size"]:
                    raise OSError("Incomplete download")
                break
            except (OSError, TimeoutError) as error:
                print(f"Download attempt {attempt + 1}: {error}", flush=True)
                if attempt == 3:
                    raise
        check_path = partial
    else:
        check_path = target
    md5, sha256 = hashlib.md5(), hashlib.sha256()
    with check_path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(block)
            sha256.update(block)
    if check_path.stat().st_size != item["size"] or "md5:" + md5.hexdigest() != item["checksum"]:
        raise ValueError(f"Checksum/size mismatch for {item['key']}; preserved for inspection")
    if check_path == partial:
        partial.rename(target)
    return {"filename": target.name, "bytes": target.stat().st_size,
            "md5": md5.hexdigest(), "sha256": sha256.hexdigest(), "source": item["links"]["self"]}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(API, timeout=30) as response:
        record = json.load(response)
    if record["metadata"]["access_right"] != "open" or record["metadata"]["license"]["id"] != "cc-by-4.0":
        raise ValueError("Release access/license differs from reviewed public CC-BY-4.0 release")
    (DEST / "zenodo-record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    results = [fetch_file(item) for item in record["files"]]
    provenance = {"record": API, "version": record["metadata"]["version"],
                  "license": record["metadata"]["license"], "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                  "files": results, "attribution": record["metadata"]["creators"],
                  "citation": record["metadata"].get("references", [])}
    (DEST / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    output = (ROOT / "data/raw/isles-2022").resolve()
    marker = output / ".extraction_complete.json"
    if not marker.exists():
        with zipfile.ZipFile(DEST / "ISLES-2022.zip") as archive:
            for item in archive.infolist():
                name = PurePosixPath(item.filename)
                target = (output / item.filename).resolve()
                if name.is_absolute() or not target.is_relative_to(output) or stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError("Unsafe ZIP entry")
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists() and target.stat().st_size == item.file_size:
                        # Do not trust size alone when resuming an interrupted extraction.
                        import zlib
                        with target.open("rb") as stream:
                            crc = 0
                            for block in iter(lambda: stream.read(1024 * 1024), b""):
                                crc = zlib.crc32(block, crc)
                        if crc == item.CRC:
                            continue
                    with archive.open(item) as source, target.open("wb") as dest:
                        shutil.copyfileobj(source, dest)
        marker.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(json.dumps({"download_verified": True, "extracted_to": str(output), "files": results}, indent=2), flush=True)


if __name__ == "__main__":
    main()
