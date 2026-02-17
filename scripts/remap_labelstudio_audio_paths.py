#!/usr/bin/env python3
"""Create a copy of a Label Studio export with remapped audio filenames/links."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def extract_filename(value: str) -> str:
    """Extract a clean filename from hashed Label Studio names."""
    base = Path(value).name
    match = re.search(r"-([^/]+\.mp3)$", base, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return base


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy Label Studio JSON and remap audio filenames to local MP3 names."
    )
    parser.add_argument("input_json", type=Path, help="Path to Label Studio export JSON")
    parser.add_argument("output_json", type=Path, help="Path for rewritten JSON copy")
    parser.add_argument(
        "--audio-dir",
        type=Path,
        help="Directory containing target MP3 files (default: input JSON directory)",
    )
    parser.add_argument(
        "--audio-url-template",
        default="/data/local-files/?d=data/train/{filename}",
        help=(
            "Template for data.audio. Use {filename} placeholder. "
            "Default: /data/local-files/?d=data/train/{filename}"
        ),
    )
    args = parser.parse_args()

    audio_dir = args.audio_dir or args.input_json.parent

    with args.input_json.open("r", encoding="utf-8") as f:
        tasks = json.load(f)

    if not isinstance(tasks, list):
        raise ValueError("Expected top-level JSON array of tasks")

    missing_files = []

    for task in tasks:
        source_name = str(task.get("file_upload") or task.get("data", {}).get("audio", ""))
        if not source_name:
            continue

        filename = extract_filename(source_name)

        if not (audio_dir / filename).exists():
            missing_files.append(filename)

        task["file_upload"] = filename
        task.setdefault("data", {})
        task["data"]["audio"] = args.audio_url_template.format(filename=filename)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    print(f"Wrote {args.output_json}")
    if missing_files:
        unique = sorted(set(missing_files))
        print(f"Warning: {len(unique)} mapped files not found in {audio_dir}")
        for name in unique:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
