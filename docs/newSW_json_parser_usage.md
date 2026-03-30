# newSW_json_parser - Usage Guide

Current `newSW_json_parser.py` uses a **two-stage pipeline** with **streaming split as default**.

> **Note:** `.swjson` support has been removed. Only `.json` files are accepted as input.

## Current Workflow

1. **Stage-1 split (default: streaming)**
   - Reads source `.json`
   - Splits by event category (`cat`)
   - Writes per-event files as `*_events.jsonl`

2. **Stage-2 chart generation**
   - Reads split files one event type at a time
   - Generates chart PNG files

This design minimizes memory usage for large traces.

## CLI Options

```bash
python newSW_json_parser.py [options]
```

Key options:

- `-i, --input` input `.json`
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
python newSW_json_parser.py -i "path/to/file.json" --list-events
```

### 2) Split only (default streaming)
```bash
python newSW_json_parser.py -i "path/to/file.json" --split-only --split-dir "temp/json_split_stream"
```

### 3) Split only for selected events
```bash
python newSW_json_parser.py -i "path/to/file.json" --split-only -e "CPU P-State/Frequency" "Temperature Metrics"
```

### 4) Generate charts from existing split files
```bash
python newSW_json_parser.py --from-split "temp/json_split_stream" -o "temp/json_analysis"
```

### 5) Full pipeline in one run
```bash
python newSW_json_parser.py -i "path/to/file.json" -o "temp/gameSOTR_analysis"
```

### 6) Force overwrite split files
```bash
python newSW_json_parser.py -i "path/to/file.json" --split-only --split-dir "temp/json_split_stream" --force
```

### 7) Legacy behavior for comparison
```bash
python newSW_json_parser.py -i "path/to/file.json" --split-only --in-memory-split
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

---

# newSW_json_event_sampler - Usage Guide

`newSW_json_event_sampler.py` has two independent functions:

| Function | Purpose | Input |
|---|---|---|
| **Sampling** | Grab N raw events per category to inspect data structure | `-i source.json` |
| **Charting** | Generate scatter-plot PNGs from the **full** event data | `-i source.json --chart` or `--from-split <dir>` |

> **Important:** Charts are built from the **complete** parsed event data — not from the small sample files. Sampling and charting are independent; you can run either or both.

## CLI Options

```bash
python newSW_json_event_sampler.py [options]
```

| Option | Description |
|---|---|
| `-i, --input` | Input `.json` source file |
| `-o, --output` | Output prefix path |
| `-e, --events` | One or more event names to process (default: all) |
| `--list-events` | List available event categories and exit |
| `--sample-size N` | Raw samples to collect per event for structure inspection (default: 10) |
| `--force` | Overwrite existing sample files |
| `--chart` | Generate chart PNGs from full event data (works with `-i` or `--from-split`) |
| `--from-split <dir>` | Directory of pre-split `*_events.jsonl` files; reads all events and charts — no source `.json` needed |

## Sampling — inspect event structure

Sampling collects a small number of **raw, unmodified** events spread evenly across the full event list. Use this to understand field names, units, and data shape before writing a parser or analysis script.

```bash
# Sample 10 events per category (default)
python newSW_json_event_sampler.py -i "path/to/trace.json"

# Sample 50 events per category
python newSW_json_event_sampler.py -i "path/to/trace.json" --sample-size 50

# Sample specific events only
python newSW_json_event_sampler.py -i "path/to/trace.json" \
  -e "DDR Bandwidth Requests by Component" "Temperature Metrics"

# Force re-collect even if sample files already exist
python newSW_json_event_sampler.py -i "path/to/trace.json" --force
```

Sampling output (`*_samples.json`) is **not** used by charting. It is only for human inspection.

## Charting — visualize full event data

Charts are generated from **all events** in the source — the full `.json` or the full contents of a pre-split `.jsonl` file. Sampling is not involved.

### From a source `.json`

```bash
# Chart all events (reads full trace)
python newSW_json_event_sampler.py -i "path/to/trace.json" --chart --sample-size 0

# Chart and sample in one pass
python newSW_json_event_sampler.py -i "path/to/trace.json" --chart

# Chart specific events only
python newSW_json_event_sampler.py -i "path/to/trace.json" --chart --sample-size 0 \
  -e "DDR Bandwidth Requests by Component" "CPU Package Power"
```

### From pre-split `*_events.jsonl` files (recommended for large traces)

Use `newSW_json_parser.py --split-only` once to split a large trace into per-event `.jsonl` files, then chart any event directly without re-reading the full source.

```bash
# List available events in split directory
python newSW_json_event_sampler.py \
  --from-split "temp/20260312T101034-socwatch-default_analysis_events_stream" \
  --list-events

# Chart all events from split directory
python newSW_json_event_sampler.py \
  --from-split "temp/20260312T101034-socwatch-default_analysis_events_stream"

# Chart specific events
python newSW_json_event_sampler.py \
  --from-split "temp/20260312T101034-socwatch-default_analysis_events_stream" \
  -e "DDR Bandwidth Requests by Component" "CPU Package Power"

# Custom output folder
python newSW_json_event_sampler.py \
  --from-split "temp/20260312T101034-socwatch-default_analysis_events_stream" \
  -o "temp/my_charts"
```

## Recommended Workflow

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 1 — Split the trace once  (newSW_json_parser.py)                │
│   python newSW_json_parser.py -i trace.json --split-only             │
│           --split-dir temp/trace_events_stream                        │
│                                                                      │
│ STEP 2 — Inspect data structure  (sampling, optional)                │
│   python newSW_json_event_sampler.py -i trace.json                   │
│   → writes *_samples.json with N raw events per category             │
│   → open the JSON to understand field names, units, value ranges     │
│                                                                      │
│ STEP 3 — Chart events of interest  (full data, no sampling needed)   │
│   python newSW_json_event_sampler.py                                 │
│           --from-split temp/trace_events_stream                      │
│           -e "DDR Bandwidth Requests by Component"                   │
│   → reads ALL events from the .jsonl file and renders chart PNG      │
└──────────────────────────────────────────────────────────────────────┘
```

## Output Files

| File | Produced when | Built from | Description |
|---|---|---|---|
| `*_samples.json` | `-i` (sampling) | N evenly-spaced raw events | Structure inspection only — not used for charts |
| `*_chart.png` | `--chart` or `--from-split` | **All** events in source/JSONL | Scatter plot of full event data over time |

### Sample file structure (`*_samples.json`)

```json
{
  "event_name": "DDR Bandwidth Requests by Component",
  "total_events": 12450,
  "sample_count": 10,
  "sample_strategy": "evenly_distributed",
  "sample_indices": [0, 1382, 2764, ...],
  "samples": [ { "cat": "...", "ts": 0, "args": {...} }, ... ]
}
```

> `samples` contains **raw, unmodified** event objects — purely for inspecting structure.

## Dependencies

- Python 3.7+
- `matplotlib` (required for `--chart`)

```bash
pip install matplotlib
```

If `matplotlib` is missing, sampling still works; chart generation is skipped with a warning.
