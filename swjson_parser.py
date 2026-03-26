#!/usr/bin/env python3
"""
SWJSON Parser for new SocWatch JSON structure.

Expected structure:
- root["data"] is a dict of event names
- each event has:
  - metaData (including optional states list)
  - data (series dictionary)
- each series has points list with objects like:
  {"x": <start>, "x1": <end>, "y": {"<state_or_metric_key>": <value>}}

This parser decodes y keys via metaData.states (when available),
then routes each event to a suitable chart type.
"""

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import parsers.tools as tools


@dataclass
class PointRecord:
    series: str
    x_start: float
    x_end: float
    metric_key: str
    metric_label: str
    value: float


@dataclass
class EventBundle:
    event_name: str
    meta_type: str
    states: List[str] = field(default_factory=list)
    records: List[PointRecord] = field(default_factory=list)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="swjson_parser.py",
        description="Parse new .swjson event structure and generate event charts",
    )
    parser.add_argument("-i", "--input", help="Input .swjson/.json path")
    parser.add_argument("-o", "--output", help="Output prefix path (default: <input_stem>_analysis)")
    parser.add_argument("-e", "--events", nargs="+", help="Specific event names to process")
    parser.add_argument("--list-events", action="store_true", help="List event names and exit")
    parser.add_argument("--split-only", action="store_true", help="Run stage-1 only (no chart generation)")
    parser.add_argument("--from-split", help="Directory containing split event files to chart from")
    parser.add_argument("--split-dir", help="Output directory for split files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing split files")
    parser.add_argument(
        "--in-memory-split",
        action="store_true",
        help="Use legacy in-memory split format (JSON) instead of default JSONL split files",
    )
    parser.add_argument(
        "--max-series",
        type=int,
        default=16,
        help="Max series per event to include in chart (default: 16)",
    )
    parser.add_argument(
        "--max-points-per-series",
        type=int,
        default=3000,
        help="Cap per-series points before charting (default: 3000)",
    )
    return parser.parse_args()


def select_file_dialog(script_dir: Path) -> Optional[Path]:
    initial_dir = str(script_dir / "temp") if (script_dir / "temp").is_dir() else str(script_dir)

    file_path = tools.tk_dialogs(
        dialog_type="open_file",
        title="Select a .swjson or .json file",
        initial_dir=initial_dir,
        filetypes=[("JSON files", "*.swjson *.json"), ("All files", "*.*")],
    )

    # Fallback to direct tkinter usage if helper is unavailable.
    if not file_path:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(
                title="Select a .swjson or .json file",
                initialdir=initial_dir,
                filetypes=[("JSON files", "*.swjson *.json"), ("All files", "*.*")],
            )
            root.destroy()
        except Exception:
            file_path = None

    if not file_path:
        return None

    tools.saveLastOpenedFolder(str(Path(file_path).parent))
    return Path(file_path)


def load_json(input_path: Path) -> dict:
    if input_path.suffix not in [".swjson", ".json"]:
        tools.errorAndExit(f"Unsupported extension: {input_path.suffix}")

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        tools.errorAndExit(f"Failed to parse JSON: {exc}")
    except OSError as exc:
        tools.errorAndExit(f"Failed to read file: {exc}")


def safe_name(value: str) -> str:
    return value.replace("/", "_").replace("(", "").replace(")", "").replace(" ", "_")


def resolve_state_label(states: List[str], metric_key: str) -> str:
    if not states:
        return metric_key
    try:
        idx = int(metric_key)
    except (TypeError, ValueError):
        return metric_key

    if 0 <= idx < len(states):
        state = states[idx]
        if isinstance(state, str) and state.strip():
            return state
    return metric_key


def spread_sample(items: List[Any], limit: int) -> List[Any]:
    total = len(items)
    if limit <= 0 or total <= limit:
        return items
    if limit == 1:
        return [items[0]]

    indices = sorted({int(round(i * (total - 1) / (limit - 1))) for i in range(limit)})
    return [items[i] for i in indices]


def parse_new_swjson(data: dict, max_points_per_series: int) -> Dict[str, EventBundle]:
    root = data.get("data")
    if not isinstance(root, dict) or not root:
        tools.errorAndExit('Invalid new swjson format: missing top-level "data" object')

    events: Dict[str, EventBundle] = {}

    for event_name, event_payload in root.items():
        if not isinstance(event_payload, dict):
            continue

        meta = event_payload.get("metaData", {})
        states = meta.get("states", []) if isinstance(meta, dict) else []
        if not isinstance(states, list):
            states = []

        bundle = EventBundle(
            event_name=event_name,
            meta_type=str(meta.get("type", "")) if isinstance(meta, dict) else "",
            states=[str(x) for x in states],
        )

        series_map = event_payload.get("data", {})
        if not isinstance(series_map, dict):
            events[event_name] = bundle
            continue

        for series_key, series_payload in series_map.items():
            if not isinstance(series_payload, dict):
                continue

            series_name = str(series_payload.get("friendlyName") or series_payload.get("name") or series_key)
            points = series_payload.get("points", [])
            if not isinstance(points, list):
                continue

            sampled_points = spread_sample(points, max_points_per_series)

            for point in sampled_points:
                if not isinstance(point, dict):
                    continue

                x_start = float(point.get("x", 0))
                x_end = float(point.get("x1", x_start))
                y_payload = point.get("y", {})

                if isinstance(y_payload, dict):
                    kv_items = y_payload.items()
                elif y_payload is None:
                    kv_items = []
                else:
                    kv_items = [("value", y_payload)]

                for metric_key_raw, metric_value_raw in kv_items:
                    metric_key = str(metric_key_raw)
                    try:
                        metric_value = float(metric_value_raw)
                    except (TypeError, ValueError):
                        continue

                    bundle.records.append(
                        PointRecord(
                            series=series_name,
                            x_start=x_start,
                            x_end=x_end,
                            metric_key=metric_key,
                            metric_label=resolve_state_label(bundle.states, metric_key),
                            value=metric_value,
                        )
                    )

        events[event_name] = bundle

    return events


def _bundle_to_payload(bundle: EventBundle) -> dict:
    return {
        "event_name": bundle.event_name,
        "meta_type": bundle.meta_type,
        "states": bundle.states,
        "records": [
            {
                "series": r.series,
                "x_start": r.x_start,
                "x_end": r.x_end,
                "metric_key": r.metric_key,
                "metric_label": r.metric_label,
                "value": r.value,
            }
            for r in bundle.records
        ],
    }


def _payload_to_bundle(payload: dict) -> EventBundle:
    bundle = EventBundle(
        event_name=str(payload.get("event_name", "")),
        meta_type=str(payload.get("meta_type", "")),
        states=[str(x) for x in payload.get("states", []) if isinstance(x, (str, int, float))],
    )
    records = payload.get("records", [])
    if not isinstance(records, list):
        return bundle

    for row in records:
        if not isinstance(row, dict):
            continue
        try:
            bundle.records.append(
                PointRecord(
                    series=str(row.get("series", "")),
                    x_start=float(row.get("x_start", 0)),
                    x_end=float(row.get("x_end", 0)),
                    metric_key=str(row.get("metric_key", "")),
                    metric_label=str(row.get("metric_label", "")),
                    value=float(row.get("value", 0)),
                )
            )
        except (TypeError, ValueError):
            continue
    return bundle


def split_events_to_files(
    events: Dict[str, EventBundle],
    split_dir: Path,
    target_events: Optional[List[str]] = None,
    force: bool = False,
    in_memory_split: bool = False,
) -> int:
    split_dir.mkdir(parents=True, exist_ok=True)
    selected = target_events if target_events else sorted(events.keys())
    written = 0

    for event_name in selected:
        if event_name not in events:
            print(f"Warning: Event not found for split: {event_name}")
            continue

        bundle = events[event_name]
        safe_event = safe_name(event_name)
        out_path = split_dir / f"{safe_event}_events.{ 'json' if in_memory_split else 'jsonl' }"

        if out_path.exists() and not force:
            print(f"Split skipped: {out_path.name} (already exists)")
            continue

        payload = _bundle_to_payload(bundle)
        if in_memory_split:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                header = {
                    "event_name": payload["event_name"],
                    "meta_type": payload["meta_type"],
                    "states": payload["states"],
                }
                f.write(json.dumps({"__meta__": header}, ensure_ascii=False) + "\n")
                for record in payload["records"]:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

        written += 1
        print(f"Split saved: {out_path.name} ({len(bundle.records)} records)")

    return written


def load_bundles_from_split(split_dir: Path) -> Dict[str, EventBundle]:
    if not split_dir.exists() or not split_dir.is_dir():
        tools.errorAndExit(f"Split directory not found: {split_dir}")

    files = sorted(list(split_dir.glob("*_events.json")) + list(split_dir.glob("*_events.jsonl")))
    if not files:
        tools.errorAndExit(f"No split files found in: {split_dir}")

    loaded: Dict[str, EventBundle] = {}
    for path in files:
        try:
            if path.suffix == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                bundle = _payload_to_bundle(payload)
            else:
                meta = {"event_name": path.stem.replace("_events", "").replace("_", " "), "meta_type": "", "states": []}
                records: List[dict] = []
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        obj = json.loads(line)
                        if isinstance(obj, dict) and "__meta__" in obj:
                            if isinstance(obj["__meta__"], dict):
                                meta.update(obj["__meta__"])
                            continue
                        if isinstance(obj, dict):
                            records.append(obj)

                payload = {
                    "event_name": meta.get("event_name", ""),
                    "meta_type": meta.get("meta_type", ""),
                    "states": meta.get("states", []),
                    "records": records,
                }
                bundle = _payload_to_bundle(payload)

            if not bundle.event_name:
                bundle.event_name = path.stem.replace("_events", "").replace("_", " ")

            loaded[bundle.event_name] = bundle
        except Exception as exc:
            print(f"Warning: failed to load split file {path.name}: {exc}")

    return loaded


def detect_chart_type(bundle: EventBundle) -> str:
    name = bundle.event_name.lower()

    if "ddr bandwidth requests by component" in name:
        return "ddr_scatter"

    if "memory subsystem (memss) p-state" in name:
        return "duration_frequency"

    if "wake" in name or "state" in name or "c-state" in name or "p-state" in name:
        return "timeline"
    if bundle.meta_type.upper() == "TRACED_EVENT" and bundle.states:
        return "timeline"

    if "bandwidth" in name or "power" in name or "frequency" in name or "voltage" in name:
        return "numeric"

    # Fallback by data shape: many metric labels often means state-like traces.
    unique_labels = {r.metric_label for r in bundle.records}
    if len(unique_labels) > 20 and bundle.states:
        return "timeline"

    return "numeric"


def render_duration_frequency_chart(bundle: EventBundle, output_dir: Path, max_series: int) -> Optional[Path]:
    """Render duration-based frequency segments: y=value, x spans [x_start, x_end]."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"Warning: matplotlib not installed, skipping chart for {bundle.event_name}")
        return None

    series_counts: Dict[str, int] = {}
    for r in bundle.records:
        series_counts[r.series] = series_counts.get(r.series, 0) + 1

    top_series = [s for s, _ in sorted(series_counts.items(), key=lambda kv: kv[1], reverse=True)[:max_series]]
    allowed = set(top_series)
    records = [r for r in bundle.records if r.series in allowed]
    if not records:
        return None

    cmap = plt.get_cmap("tab10")
    series_color = {series: cmap(i % 10) for i, series in enumerate(top_series)}

    fig, ax = plt.subplots(figsize=(16, 9))
    for r in records:
        x0 = r.x_start / 1e6
        x1 = r.x_end / 1e6
        if x1 < x0:
            x1 = x0
        ax.hlines(y=r.value, xmin=x0, xmax=x1, color=series_color.get(r.series, "tab:blue"), linewidth=2.5, alpha=0.9)

    ax.set_title(f"{bundle.event_name} - Frequency Over Duration")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Frequency")
    ax.grid(True, alpha=0.25)

    if len(top_series) > 1:
        handles = [plt.Line2D([0], [0], color=series_color[s], lw=2.5, label=s) for s in top_series]
        ax.legend(handles=handles, loc="best", fontsize=8, ncol=2)

    fig.tight_layout()
    out_path = output_dir / f"{safe_name(bundle.event_name)}_duration_frequency_chart.png"
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out_path


def render_ddr_scatter_chart(bundle: EventBundle, output_dir: Path, max_series: int) -> Optional[Path]:
    """Render DDR bandwidth as scatter points with MB/s on Y-axis."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"Warning: matplotlib not installed, skipping chart for {bundle.event_name}")
        return None

    per_series: Dict[str, List[Tuple[float, float]]] = {}
    total_read_by_time: Dict[float, float] = {}
    total_write_by_time: Dict[float, float] = {}
    for r in bundle.records:
        if r.series not in per_series:
            per_series[r.series] = []
        # Use interval midpoint as the sample time for scatter plotting.
        midpoint = ((r.x_start + r.x_end) * 0.5) / 1e6
        per_series[r.series].append((midpoint, r.value))

        label_upper = r.series.upper()
        if "READ" in label_upper:
            total_read_by_time[midpoint] = total_read_by_time.get(midpoint, 0.0) + r.value
        if "WRITE" in label_upper:
            total_write_by_time[midpoint] = total_write_by_time.get(midpoint, 0.0) + r.value

    if not per_series:
        return None

    top_series = sorted(per_series.keys(), key=lambda s: len(per_series[s]), reverse=True)[:max_series]

    fig, ax = plt.subplots(figsize=(16, 9))
    for series in top_series:
        points = sorted(per_series[series], key=lambda p: p[0])
        x = [p[0] for p in points]
        y = [p[1] for p in points]
        ax.scatter(x, y, s=24, alpha=0.82, label=series)

    if total_read_by_time:
        read_points = sorted(total_read_by_time.items(), key=lambda p: p[0])
        read_x = [p[0] for p in read_points]
        read_y = [p[1] for p in read_points]
        ax.plot(
            read_x,
            read_y,
            color="black",
            linewidth=2.4,
            marker="o",
            markersize=4,
            label="Total READ",
            zorder=5,
        )

    if total_write_by_time:
        write_points = sorted(total_write_by_time.items(), key=lambda p: p[0])
        write_x = [p[0] for p in write_points]
        write_y = [p[1] for p in write_points]
        ax.plot(
            write_x,
            write_y,
            color="dimgray",
            linewidth=2.4,
            marker="s",
            markersize=4,
            label="Total WRITE",
            zorder=5,
        )

    ax.set_title(f"{bundle.event_name} - DDR Bandwidth Scatter")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("MB/s")
    ax.grid(True, alpha=0.25)
    if len(top_series) > 1:
        ax.legend(loc="best", fontsize=8, ncol=2)

    fig.tight_layout()
    out_path = output_dir / f"{safe_name(bundle.event_name)}_scatter_chart.png"
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out_path


def render_timeline_chart(bundle: EventBundle, output_dir: Path, max_series: int) -> Optional[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"Warning: matplotlib not installed, skipping chart for {bundle.event_name}")
        return None

    # Keep chart readable by limiting to top series by event count.
    series_counts: Dict[str, int] = {}
    for r in bundle.records:
        series_counts[r.series] = series_counts.get(r.series, 0) + 1

    top_series = [s for s, _ in sorted(series_counts.items(), key=lambda kv: kv[1], reverse=True)[:max_series]]
    allowed = set(top_series)
    records = [r for r in bundle.records if r.series in allowed]
    if not records:
        return None

    series_index = {s: i for i, s in enumerate(top_series)}

    # Assign deterministic colors by metric label.
    labels = sorted({r.metric_label for r in records})
    cmap = plt.get_cmap("tab20")
    color_map = {label: cmap(i % 20) for i, label in enumerate(labels)}

    fig, ax = plt.subplots(figsize=(16, 9))

    for r in records:
        y = series_index[r.series]
        x0 = r.x_start / 1e6
        x1 = r.x_end / 1e6
        if x1 < x0:
            x1 = x0
        ax.hlines(y=y, xmin=x0, xmax=x1, color=color_map[r.metric_label], linewidth=3, alpha=0.9)

    ax.set_title(f"{bundle.event_name} - Timeline")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Series")
    ax.set_yticks(list(series_index.values()))
    ax.set_yticklabels(top_series)
    ax.grid(True, axis="x", alpha=0.25)

    # Limit legend size to keep chart readable.
    legend_labels = labels[:12]
    handles = [plt.Line2D([0], [0], color=color_map[label], lw=3, label=label) for label in legend_labels]
    if handles:
        ax.legend(handles=handles, loc="best", fontsize=8, ncol=2)

    fig.tight_layout()
    out_path = output_dir / f"{safe_name(bundle.event_name)}_timeline_chart.png"
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out_path


def render_numeric_chart(bundle: EventBundle, output_dir: Path, max_series: int) -> Optional[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"Warning: matplotlib not installed, skipping chart for {bundle.event_name}")
        return None

    # Aggregate value per point timestamp per series (sum over y keys in same point already split as records).
    per_series: Dict[str, List[Tuple[float, float]]] = {}
    for r in bundle.records:
        if r.series not in per_series:
            per_series[r.series] = []
        per_series[r.series].append((r.x_start / 1e6, r.value))

    if not per_series:
        return None

    top_series = sorted(per_series.keys(), key=lambda s: len(per_series[s]), reverse=True)[:max_series]

    fig, ax = plt.subplots(figsize=(16, 9))
    for series in top_series:
        points = sorted(per_series[series], key=lambda p: p[0])
        x = [p[0] for p in points]
        y = [p[1] for p in points]
        ax.plot(x, y, marker="o", markersize=2, linewidth=1, alpha=0.85, label=series)

    ax.set_title(f"{bundle.event_name} - Value Trend")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Value")
    ax.grid(True, alpha=0.25)
    if len(top_series) > 1:
        ax.legend(loc="best", fontsize=8, ncol=2)

    fig.tight_layout()
    out_path = output_dir / f"{safe_name(bundle.event_name)}_value_chart.png"
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out_path


def save_event_summary(bundle: EventBundle, output_dir: Path, chart_type: str) -> Path:
    labels = sorted({r.metric_label for r in bundle.records})
    series = sorted({r.series for r in bundle.records})

    summary = {
        "event_name": bundle.event_name,
        "meta_type": bundle.meta_type,
        "chart_type": chart_type,
        "total_records": len(bundle.records),
        "series_count": len(series),
        "metric_label_count": len(labels),
        "metric_labels_preview": labels[:50],
        "states_count": len(bundle.states),
        "states_preview": bundle.states[:50],
        "start_ts": min((r.x_start for r in bundle.records), default=0),
        "end_ts": max((r.x_end for r in bundle.records), default=0),
    }

    out_path = output_dir / f"{safe_name(bundle.event_name)}_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return out_path


def main() -> None:
    args = parse_arguments()
    script_dir = Path(__file__).parent

    if args.max_series <= 0:
        tools.errorAndExit("--max-series must be > 0")

    if args.max_points_per_series <= 0:
        tools.errorAndExit("--max-points-per-series must be > 0")

    input_path: Optional[Path] = None
    events: Dict[str, EventBundle] = {}

    if args.from_split:
        split_dir = Path(args.from_split)
        events = load_bundles_from_split(split_dir)
        if not events:
            tools.errorAndExit("No events loaded from split directory")
        output_dir = Path(args.output) if args.output else split_dir.parent / f"{split_dir.name}_analysis"
    else:
        if args.input:
            input_path = Path(args.input)
        else:
            input_path = select_file_dialog(script_dir)
            if not input_path:
                tools.errorAndExit("No file selected")

        if not input_path.exists():
            tools.errorAndExit(f"File not found: {input_path}")

        output_dir = Path(args.output) if args.output else input_path.parent / f"{input_path.stem}_analysis"
        print(f"Processing: {input_path}")
        data = load_json(input_path)
        events = parse_new_swjson(data, max_points_per_series=args.max_points_per_series)
        if not events:
            tools.errorAndExit("No events found under root data object")

    output_dir.mkdir(parents=True, exist_ok=True)

    all_event_names = sorted(events.keys())

    if args.list_events:
        print(f"\nAvailable events ({len(all_event_names)}):")
        for i, event_name in enumerate(all_event_names, 1):
            print(f"  {i:2d}. {event_name}")
        return

    if args.events:
        target_events = [e for e in args.events if e in events]
        for e in args.events:
            if e not in events:
                print(f"Warning: Event not found: {e}")
        if not target_events:
            tools.errorAndExit("None of the requested events exist in input")
    else:
        target_events = all_event_names

    if args.from_split is None:
        default_split_dir = output_dir.parent / f"{output_dir.stem}_events_stream"
        split_dir = Path(args.split_dir) if args.split_dir else default_split_dir
        split_written = split_events_to_files(
            events,
            split_dir=split_dir,
            target_events=target_events,
            force=args.force,
            in_memory_split=args.in_memory_split,
        )
        print(f"\nSplit stage complete. Files written: {split_written}. Dir: {split_dir}")

        if args.split_only:
            print("Split-only mode: skipping chart generation.")
            return

    print(f"\nGenerating charts for {len(target_events)} event(s)...")
    generated = 0

    for event_name in target_events:
        bundle = events[event_name]
        if not bundle.records:
            print(f"[{event_name}] skipped (no records)")
            continue

        chart_type = detect_chart_type(bundle)
        print(f"[{event_name}] records={len(bundle.records)} chart={chart_type}")

        if chart_type == "timeline":
            chart_path = render_timeline_chart(bundle, output_dir, args.max_series)
        elif chart_type == "duration_frequency":
            chart_path = render_duration_frequency_chart(bundle, output_dir, args.max_series)
        elif chart_type == "ddr_scatter":
            chart_path = render_ddr_scatter_chart(bundle, output_dir, args.max_series)
        else:
            chart_path = render_numeric_chart(bundle, output_dir, args.max_series)

        summary_path = save_event_summary(bundle, output_dir, chart_type)
        if chart_path:
            generated += 1
            print(f"  chart  : {chart_path.name}")
        print(f"  summary: {summary_path.name}")

    print(f"\nDone. Charts generated: {generated}. Output: {output_dir}")


if __name__ == "__main__":
    main()
