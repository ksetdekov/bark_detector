# bark_detector
bark detector training and inference

## Convert train audio from m4a to mp3

Use:

```bash
python3 scripts/convert_m4a_to_mp3.py
```

The script:
- Recursively scans `data/train` for `.m4a` files.
- Creates `.mp3` files next to each source file.
- Tracks each file as `converted`, `skipped` (if target exists), or `failed`.
- Writes reports:
  - JSON history: `data/train/conversion_report.json`
  - CSV for last run: `data/train/last_conversion_report.csv`

Prerequisite: `ffmpeg` must be installed and available in `PATH`.
