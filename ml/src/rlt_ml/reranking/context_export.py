import argparse
import json
import shutil
from pathlib import Path

from rlt_ml.common import sha256, write_json


def export_context(runtime: Path, statistics: Path, report: Path, out: Path):
    manifest = json.loads((runtime / "runtime.json").read_text())
    verification = json.loads(report.read_text())
    if not verification["passed"] or verification["mode"] != "metadata":
        raise ValueError("Metadata serving parity is not verified")
    if verification["model_sha256"] != manifest["files"]["ranker.cbm"]:
        raise ValueError("Verification belongs to another model")
    if verification["customer_stats_sha256"] != sha256(statistics):
        raise ValueError("Customer statistics differ from verification")
    for name, checksum in manifest["files"].items():
        if Path(name).name != name or sha256(runtime / name) != checksum:
            raise ValueError("Invalid runtime artifact")
    out.mkdir(parents=True, exist_ok=False)
    for name in manifest["files"]:
        shutil.copyfile(runtime / name, out / name)
    shutil.copyfile(statistics, out / "customer_stats.parquet")
    manifest["files"]["customer_stats.parquet"] = sha256(out / "customer_stats.parquet")
    manifest["serving_verification"] = verification
    write_json(out / "runtime.json", manifest)


def main():
    parser = argparse.ArgumentParser()
    for name in ("runtime", "statistics", "report", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    export_context(args.runtime, args.statistics, args.report, args.out)


if __name__ == "__main__":
    main()
