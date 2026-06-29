# Trace CSV Separator (trace_separator)

Splits a large SoCWatch `_trace.csv` into individual per-event-type CSV files for easier analysis and plotting.

## Problem Solved

SoCWatch time-based-event trace files can grow to hundreds of MB and millions of rows because every event type (CPU P-state, MEMSS P-state, Core C-state, temperatures, bandwidth, …) is concatenated into a single file. This tool separates each event type into its own CSV so you can open, filter, and plot just the data you need.

## Features

- 📂 **Single-pass streaming** — reads the file line by line, never loads it all into memory; handles files of any size
- 🔍 **Auto-discovers all event types** — no configuration required
- 🗂️ **Groups sub-units together** — e.g. all 16 `Core C-State (OS) - Core_N` sections land in one `Core_C-State__OS_.csv`
- 🏷️ **Section column** — every output row gets a `Section` column with the original full section name (e.g. `"Core C-State (OS) - CPU/Package_0/Core_3"`) so you can filter by core/channel in Excel or pandas
- 📋 **`--list` mode** — fast scan that prints all event types without writing any files
- 📊 **Summary table** — shows section count, row count, and output filename for every event type
- 📈 **Progress reporting** — prints a status line every 500 000 lines read

## Requirements

- Python 3.9 or higher
- No third-party packages — uses only the standard library

## Usage

### List event types only (fast scan, no output files)

```bash
python trace_separator.py <trace_csv> --list
```

### Separate into per-event CSVs (default output dir next to input file)

```bash
python trace_separator.py <trace_csv>
```

Output is written to `<input_stem>_separated/` in the same folder as the input file.

### Specify a custom output directory

```bash
python trace_separator.py <trace_csv> --out C:\my\output\dir
# or as a positional argument
python trace_separator.py <trace_csv> C:\my\output\dir
```

## Examples

```bash
# 1. Discover all event types in the trace
python trace_separator.py "temp\20260626T151418-socwatch-default_trace.csv" --list

# 2. Separate the full trace (outputs to ..._separated\ folder)
python trace_separator.py "temp\20260626T151418-socwatch-default_trace.csv"

# 3. Write to a specific folder
python trace_separator.py "temp\20260626T151418-socwatch-default_trace.csv" --out D:\analysis\separated
```

## Output Format

Each output CSV has:

| Column | Description |
|--------|-------------|
| `Section` | Full original section name, e.g. `"Core C-State (OS) - CPU/Package_0/Core_3"` |
| `Sample #` | Per-section sample index (resets to 1 for each sub-unit) |
| `Continuous Time (usec)` | Timestamp in the native unit reported by SoCWatch |
| *(event columns)* | All remaining columns from the original section header |

### Example — `Memory_Subsystem__MEMSS__P-State.csv`

```
Section,Sample #,Continuous Time (usec),Duration (ms),Frequency (MHz)
"Memory Subsystem (MEMSS) P-State - MEMSS",1,313443.20,313.44,1584.0
"Memory Subsystem (MEMSS) P-State - MEMSS",2,404569.50,91.13,1584.0
...
```

## How Section Grouping Works

SoCWatch section names follow the pattern:

```
<Event Type> - <Sub-Unit>
```

For example:
- `Core C-State (OS) - CPU/Package_0/Core_0`
- `Core C-State (OS) - CPU/Package_0/Core_1`

The separator extracts the part **before** the first ` - ` as the *base event type* and writes all matching sections into one file, adding the full section name in the `Section` column.

## Typical Event Types Found in a SoCWatch Trace

| Base Event Type | Typical Sub-Units | Rows (example) |
|---|---|---|
| Memory Subsystem (MEMSS) P-State | 1 (MEMSS) | ~811 |
| CPU P-State/Frequency | 32 (2 threads × 16 cores) | ~15 800 |
| Core P-State/Frequency (OS) | 16 (one per core) | ~4 900 000 |
| Core C-State (OS) | 16 (one per core) | ~4 900 000 |
| Temperature Metrics | 16 (one per core) | ~7 900 |
| Display P-State | 1 | ~811 |
| PCIe LPM | 11 (one per device) | ~8 185 |

## Performance

| Metric | Observed |
|---|---|
| Input file | ~500 MB, 25 M lines |
| Processing time | ~3 min (single-threaded Python I/O) |
| Peak memory | < 50 MB (streaming) |
| Output files | 76 CSVs |
| Total rows written | ~25 M |
