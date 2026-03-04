# SWJSON Parser - Usage Guide

Current `swjson_parser.py` uses a **two-stage pipeline** with **streaming split as default**.

## Current Workflow

1. **Stage-1 split (default: streaming)**
   - Reads source `.swjson` / `.json`
   - Splits by event category (`cat`)
   - Writes per-event files as `*_events.jsonl`

2. **Stage-2 chart generation**
   - Reads split files one event type at a time
   - Generates chart PNG files

This design minimizes memory usage for large traces.

## CLI Options

```bash
python swjson_parser.py [options]
```

Key options:

- `-i, --input` input `.swjson` / `.json`
- `-o, --output` output prefix path
- `-e, --events` specific event names to include
- `--list-events` list event categories in input
- `--split-only` run stage-1 only (no chart generation)
- `--from-split <dir>` run stage-2 from existing split files
- `--split-dir <dir>` output directory for split files
- `--force` overwrite existing split files
- `--in-memory-split` use legacy in-memory split (default is streaming split)

## Examples

### 1) List events
```bash
python swjson_parser.py -i "path/to/file.swjson" --list-events
```

### 2) Split only (default streaming)
```bash
python swjson_parser.py -i "path/to/file.swjson" --split-only --split-dir "temp/swjson_split_stream"
```

### 3) Split only for selected events
```bash
python swjson_parser.py -i "path/to/file.swjson" --split-only -e "CPU P-State/Frequency" "Temperature Metrics"
```

### 4) Generate charts from existing split files
```bash
python swjson_parser.py --from-split "temp/swjson_split_stream" -o "temp/swjson_analysis"
```

### 5) Full pipeline in one run
```bash
python swjson_parser.py -i "path/to/file.swjson" -o "temp/gameSOTR_analysis"
```

### 6) Force overwrite split files
```bash
python swjson_parser.py -i "path/to/file.swjson" --split-only --split-dir "temp/swjson_split_stream" --force
```

### 7) Legacy behavior for comparison
```bash
python swjson_parser.py -i "path/to/file.swjson" --split-only --in-memory-split
```

## Output Files

### Split stage output

- Streaming default: `*_events.jsonl`
- Legacy mode: `*_events.json`

### Chart stage output

- `{output_stem}_{Event_Name}_chart.png`

> Chart drawing is event-type aware (bandwidth/state/sensor/generic dispatch).

## Timers

The parser prints timing information:

- `[timer] start`, `[timer] end`, `[timer] total sec`
- stage-level timers such as split/chart/from-split

Use these to compare streaming vs in-memory performance.

## Dependencies

- Python 3.7+
- `ijson` (recommended for true streaming split)
- `matplotlib` (required only for chart generation)

Install recommended packages:

```bash
pip install ijson matplotlib
```

If `matplotlib` is missing, split mode still works; chart stage is skipped with warning.
