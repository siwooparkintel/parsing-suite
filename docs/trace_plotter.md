# Trace Plotter (trace_plotter)

Plots per-event-type CSVs produced by `trace_separator.py` with automatic event detection and a configurable `PLOT_REGISTRY` that controls how each event type is rendered.

## Features

- 🔍 **Auto-detects event type** from the `Section` column — no flags needed for known events
- 🗺️ **`PLOT_REGISTRY` switch map** — one dict entry per event type controls plot style, Y column, time unit, Y ticks, and grouping behavior
- 📈 **Four plot styles** — `step` (P-states), `line` (temperatures / bandwidth), `scatter` (C-state events), `ddr_bw` (dedicated two-panel DDR bandwidth chart)
- 🎛️ **CLI overrides** — any registry default can be overridden at the command line (`--time`, `--plot-type`, `--y-col`)
- 🖥️ **Multi-section support** — overlays sections on one axes when ≤ overlay threshold, auto-switches to subplots when there are more
- 🔎 **Section filter** — pick specific cores/channels with `--sections`
- 💾 **File output** — save to PNG / PDF / SVG with `--output`
- 📋 **`--list` mode** — print the full registry table

## Requirements

- Python 3.9 or higher
- `matplotlib >= 3.6`
- `pandas >= 1.5`
- `numpy`

Install dependencies:

```bash
pip install matplotlib pandas numpy
```

## Usage

```bash
# Plot with auto-detected settings (opens interactive window)
python trace_plotter.py <separated_csv>

# Override time unit on X axis
python trace_plotter.py <csv> --time sec        # seconds (default for most events)
python trace_plotter.py <csv> --time ms         # milliseconds
python trace_plotter.py <csv> --time usec       # microseconds

# Filter to specific sections (partial name match, space-separated)
python trace_plotter.py <csv> --sections Core_0 Core_1 Core_2 Core_3

# Override plot style
python trace_plotter.py <csv> --plot-type step
python trace_plotter.py <csv> --plot-type line
python trace_plotter.py <csv> --plot-type scatter

# Override which column appears on the Y axis
python trace_plotter.py <csv> --y-col "Temperature (oC)"

# Save to file instead of opening a window
python trace_plotter.py <csv> --output chart.png
python trace_plotter.py <csv> --output chart.pdf

# Show all registered event configs
python trace_plotter.py --list
```

## Examples

```bash
# MEMSS P-State frequency (step chart, time in seconds, Y ticks at discrete states)
python trace_plotter.py "temp\..._separated\Memory_Subsystem__MEMSS__P-State.csv"

# Core P-State — overlay 4 cores on one chart
python trace_plotter.py "temp\..._separated\Core_P-State_Frequency__OS_.csv" \
    --sections Core_0 Core_1 Core_2 Core_3

# Core P-State — all 16 cores as subplots (> overlay_threshold)
python trace_plotter.py "temp\..._separated\Core_P-State_Frequency__OS_.csv"

# Display P-State, X axis in milliseconds, save to PNG
python trace_plotter.py "temp\..._separated\Display_P-State.csv" \
    --time ms --output display_pstate.png

# Temperature, line chart with section filter
python trace_plotter.py "temp\..._separated\Temperature_Metrics.csv" \
    --sections Core_0 Core_4 Core_8 Core_12

# Force scatter plot on any event
python trace_plotter.py "temp\...._separated\Memory_Subsystem__MEMSS__P-State.csv" \
    --plot-type scatter

# DDR Bandwidth — two-panel chart (total lines + per-subchannel scatter)
python trace_plotter.py "temp\...._separated\DDR_Bandwidth_Requests_by_Component.csv"
python trace_plotter.py "temp\...._separated\DDR_Bandwidth_Requests_by_Component.csv" \
    --output ddr_bw.png
```

## PLOT_REGISTRY — The Switch Map

The registry is a plain Python `dict` at the top of `trace_plotter.py`. Each key is the *base event type* name (text before the first ` - ` in the `Section` column). To add or change how an event is rendered, edit its entry or add a new one.

```python
PLOT_REGISTRY: dict[str, PlotConfig] = {
    "Memory Subsystem (MEMSS) P-State": PlotConfig(
        y_cols            = ["Frequency (MHz)"],
        x_col             = "Continuous Time (usec)",
        x_native_unit     = "usec",
        default_time_unit = "sec",
        plot_type         = "step",
        step_where        = "post",
        y_label           = "Frequency (MHz)",
        title             = "Memory Subsystem (MEMSS) P-State",
        group_by_section  = False,
        y_ticks           = [594, 1188, 1584, 2112],
    ),
    ...
}
```

### PlotConfig fields

| Field | Type | Description |
|---|---|---|
| `y_cols` | `list[str]` | CSV column(s) to plot on Y axis. Empty list → auto-detect first numeric column |
| `x_col` | `str` | Time column name in the CSV |
| `x_native_unit` | `str` | Unit stored in the time column: `"usec"`, `"ms"`, `"sec"` |
| `default_time_unit` | `str` | Preferred display unit for the X axis |
| `plot_type` | `str` | `"step"` / `"line"` / `"scatter"` |
| `step_where` | `str` | Staircase anchor: `"pre"` / `"mid"` / `"post"` |
| `alpha` | `float` | Line/marker opacity (0–1) |
| `linewidth` | `float` | Line width in points |
| `y_label` | `str` | Y axis label (falls back to column name if empty) |
| `col_label_map` | `dict` | Override label per column: `{"Frequency(Mhz)": "Freq (MHz)"}` |
| `title` | `str` | Chart title (falls back to event name if empty) |
| `group_by_section` | `bool` | `True` → separate color per sub-unit; `False` → single series |
| `overlay_threshold` | `int` | Sections ≤ this value → overlay on one axes; more → auto-subplots |
| `y_ticks` | `list \| None` | Explicit Y tick locations (useful for discrete P-states) |
| `y_lim` | `tuple \| None` | `(ymin, ymax)` to pin the Y axis range |

### Plot type guide

| Event type | Recommended plot | Reason |
|---|---|---|
| P-State (MEMSS, Display, Media, …) | `step` | Discrete frequency levels held until next transition |
| CPU / Core / Thread P-State (OS) | `step` | Same — frequency is discrete |
| Core / Thread C-State (OS) | `scatter` | Sparse event-based data; duration as Y |
| Temperature Metrics | `line` | Continuous sampled values |
| DDR Bandwidth Requests | `ddr_bw` | Dedicated two-panel chart (see below) |
| Other bandwidth events | `line` | Continuous sampled values |
| HWP Capabilities | `step` | Discrete capability value |

## Registered Event Types

| Event Type | Plot | Time | Y Column(s) |
|---|---|---|---|
| Memory Subsystem (MEMSS) P-State | step | sec | Frequency (MHz) |
| Core P-State/Frequency (OS) | step | sec | Frequency(Mhz) |
| Thread P-State/Frequency (OS) | step | sec | Frequency(Mhz) |
| Package P-State/Frequency (OS) | step | sec | Frequency(Mhz) |
| CPU P-State/Frequency | line | sec | (auto-detect) |
| Display P-State | step | sec | Frequency (MHz) |
| Media P-State | step | sec | Frequency (MHz) |
| Core C-State (OS) | scatter | sec | Duration (ms) |
| Thread C-State (OS) | scatter | sec | Duration (ms) |
| Package C-State | scatter | sec | Duration (ms) |
| Temperature Metrics | line | sec | Temperature (oC) |
| HWP Capabilities | step | sec | (auto-detect) |
| **DDR Bandwidth Requests by Component** | **ddr_bw** | sec | see below |

Events not in the registry fall back to a generic `line` chart with auto-detected Y column.

## DDR Bandwidth Chart (`ddr_bw`)

The DDR event uses a dedicated two-panel layout instead of the generic plotter:

```
┌─────────────────────────────────────────────────────────┐
│  Total Read / Write / Combined  — line chart            │
│  Blue = Total Read   Orange = Total Write               │
│  Green (dashed) = Total R+W                             │
├─────────────────────────────────────────────────────────┤
│  Per Sub-Channel R+W  — scatter chart                   │
│  One colour per MCx-CHx-SUBCHx  (8 sub-channels)       │
└─────────────────────────────────────────────────────────┘
```

**Data source:** SoCWatch records two sub-sections per DDR event:

| Sub-section | Values |
|---|---|
| `… - DDR` | Raw bytes per sample window — requires ÷ duration to get rate |
| `… - DDR : Instantaneous rate` | Already in **MB/s** — used by the plotter |

The plotter always selects the `Instantaneous rate` sub-section and divides by 1000 to express results in **GB/s**.

**Columns used:**

| Pattern | Role |
|---|---|
| `MCx-CHx-SUBCHx-READS (bytes)` | Read MB/s per sub-channel (8 columns) |
| `MCx-CHx-SUBCHx-WRITES (bytes)` | Write MB/s per sub-channel (8 columns) |

Total Read = sum of all 8 READ columns; Total Write = sum of all 8 WRITE columns.
Per-sub-channel = READ + WRITE for that sub-channel.

**Typical range (LPDDR5X dual-MC):**

| Metric | Range observed |
|---|---|
| Total Read | 0 – 30 GB/s |
| Total Write | 0 – 13 GB/s |
| Total R+W | 0 – 43 GB/s |
| Per sub-channel R+W | 0 – 5 GB/s |

> Note: `--plot-type` is ignored for `ddr_bw` events because the two-panel layout is fixed. Use `--time` to change the X-axis unit.

## Multi-Section Behavior

When `group_by_section = True` the plotter reads the `Section` column and splits the data into groups:

- If the number of sections ≤ `overlay_threshold` (default 6) → all sections are drawn on **one axes** with different colors and a legend
- If the number of sections > `overlay_threshold` → **subplots** are created automatically (up to 4 columns, N rows)

Use `--sections` to pre-filter and force the overlay layout even for events with many sub-units:

```bash
# 16 cores would normally trigger subplots; filter to 4 to get overlay
python trace_plotter.py Core_P-State_Frequency__OS_.csv \
    --sections Core_0 Core_4 Core_8 Core_12
```

## Workflow

```
socwatch _trace.csv
        │
        ▼
trace_separator.py  ──→  <stem>_separated/
                              Memory_Subsystem__MEMSS__P-State.csv
                              Core_P-State_Frequency__OS_.csv
                              DDR_Bandwidth_Requests_by_Component.csv
                              Temperature_Metrics.csv
                              … (76 files)
        │
        ▼
trace_plotter.py  ──→  interactive window  or  chart.png
                         │
                         ├── step  chart   (P-states)
                         ├── line  chart   (temperature, bandwidth)
                         ├── scatter chart (C-states)
                         └── ddr_bw chart  (DDR: 2-panel totals + sub-channels)
```
