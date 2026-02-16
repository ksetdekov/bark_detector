#!/usr/bin/env python3
import argparse
import csv
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class ConversionResult:
    source: str
    target: str
    status: str
    error: str = ""


def find_ffmpeg() -> Optional[str]:
    env_ffmpeg = os.environ.get("FFMPEG_BINARY")
    if env_ffmpeg and Path(env_ffmpeg).exists():
        return env_ffmpeg

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if Path(candidate).exists():
            return candidate

    return None


def convert_file(src: Path, dst: Path, ffmpeg_bin: str) -> ConversionResult:
    if dst.exists():
        return ConversionResult(
            source=str(src),
            target=str(dst),
            status="skipped",
            error="target_exists",
        )

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(src),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(dst),
    ]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return ConversionResult(
            source=str(src),
            target=str(dst),
            status="failed",
            error=str(exc),
        )

    if completed.returncode == 0:
        return ConversionResult(
            source=str(src),
            target=str(dst),
            status="converted",
        )

    err = (completed.stderr or "").strip() or f"ffmpeg exited with code {completed.returncode}"
    return ConversionResult(
        source=str(src),
        target=str(dst),
        status="failed",
        error=err,
    )


def ensure_ffmpeg() -> Optional[str]:
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        return None
    return (
        "ffmpeg not found. Install with Homebrew (`brew install ffmpeg`) or set "
        "FFMPEG_BINARY to the full ffmpeg path."
    )


def write_json_report(report_path: Path, run_payload: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if report_path.exists():
        try:
            existing = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {"runs": []}
    else:
        existing = {"runs": []}

    existing.setdefault("runs", []).append(run_payload)
    report_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def write_csv_report(csv_path: Path, results: list[ConversionResult]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "target", "status", "error"])
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "source": r.source,
                    "target": r.target,
                    "status": r.status,
                    "error": r.error,
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert .m4a files to .mp3 and track conversion status."
    )
    parser.add_argument(
        "--input-dir",
        default="data/train",
        help="Directory containing .m4a files (default: data/train)",
    )
    parser.add_argument(
        "--report-json",
        default="data/train/conversion_report.json",
        help="Path for JSON report history",
    )
    parser.add_argument(
        "--report-csv",
        default="data/train/last_conversion_report.csv",
        help="Path for CSV report of the latest run",
    )

    args = parser.parse_args()
    input_dir = Path(args.input_dir)
    report_json = Path(args.report_json)
    report_csv = Path(args.report_csv)

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input directory does not exist: {input_dir}")
        return 1

    ffmpeg_error = ensure_ffmpeg()
    if ffmpeg_error:
        print(ffmpeg_error)
        return 1
    ffmpeg_bin = find_ffmpeg()
    if ffmpeg_bin is None:
        print("ffmpeg lookup failed unexpectedly")
        return 1

    sources = sorted(input_dir.rglob("*.m4a"))
    results: list[ConversionResult] = []

    for src in sources:
        dst = src.with_suffix(".mp3")
        result = convert_file(src, dst, ffmpeg_bin)
        results.append(result)

    converted = sum(1 for r in results if r.status == "converted")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "failed")

    run_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(input_dir),
        "totals": {
            "found_m4a": len(results),
            "converted": converted,
            "skipped": skipped,
            "failed": failed,
        },
        "results": [
            {
                "source": r.source,
                "target": r.target,
                "status": r.status,
                "error": r.error,
            }
            for r in results
        ],
    }

    write_json_report(report_json, run_payload)
    write_csv_report(report_csv, results)

    print(f"Found: {len(results)} .m4a files")
    print(f"Using ffmpeg: {ffmpeg_bin}")
    print(f"Converted: {converted}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"JSON report (history): {report_json}")
    print(f"CSV report (last run): {report_csv}")

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
