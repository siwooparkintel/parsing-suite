# swjson_parser.py - Usage Guide (Socwatch 2025.3.0 or older, SWJSON Structure)

This guide is for [parsing-suite/swjson_parser.py](parsing-suite/swjson_parser.py), which parses the newer SocWatch JSON layout.

## Supported Input Structure

The parser expects:

- Root `data` dictionary with event names as keys
- Per event:
  - `metaData` (can include `states` list)
  - `data` dictionary of series
- Per series:
  - `points` list with entries like:

```json
{
  "x": 39564,
  "x1": 39565,
  "y": {
    "70": 1.0
  }
}
```

## State Index Decoding

When `y` uses numeric keys and `metaData.states` exists:

- Key `"70"` maps to `metaData.states[70]`
- If index is invalid or states are missing, the original key is kept

This enables readable labels for traced/state-style events.

## Chart Routing

The parser routes each event to a chart function based on event characteristics:

- `timeline` chart:
  - Wakeups, C-state, P-state, traced events with state-heavy labels
- `numeric` chart:
  - Bandwidth, power, frequency, voltage, and value-style metrics

Each processed event generates one chart plus one summary JSON.

## CLI

```bash
python swjson_parser.py [options]
```

Options:

- `-i, --input` input `.swjson` / `.json`
- `-o, --output` output folder path (default: `<input_stem>_analysis`)
- `-e, --events` specific event names to process
- `--list-events` list events in file and exit
- `--max-series` max series rendered per event chart (default: `16`)
- `--max-points-per-series` max sampled points per series before charting (default: `3000`)

## Examples

### 1) List all event names

```bash
python swjson_parser.py -i "temp/yt_si2.s5.pretty.json" --list-events
```

### 2) Parse one state-style event

```bash
python swjson_parser.py -i "temp/yt_si2.s5.pretty.json" -e "Core Wakeups (OS)"
```

### 3) Parse two selected events

```bash
python swjson_parser.py -i "temp/yt_si2.s5.pretty.json" -e "Core Wakeups (OS)" "IO Bandwidth"
```

### 4) Process all events to a target folder

```bash
python swjson_parser.py -i "temp/yt_si2.s5.pretty.json" -o "temp/new_swjson_parser_test"
```

### 5) Limit chart load for very large traces

```bash
python swjson_parser.py -i "temp/yt_si2.s5.pretty.json" --max-series 8 --max-points-per-series 1000
```

## Output Files

For each event:

- Timeline chart: `*_timeline_chart.png`
- Numeric chart: `*_value_chart.png`
- Summary: `*_summary.json`

Summary includes:

- `event_name`, `meta_type`, `chart_type`
- `total_records`, `series_count`, `metric_label_count`
- `states_count` with preview fields
- `start_ts`, `end_ts`

## Dependencies

- Python 3.8+
- `matplotlib` for charts

Install:

```bash
pip install matplotlib
```

If `matplotlib` is missing, parser will skip chart generation with warning.
