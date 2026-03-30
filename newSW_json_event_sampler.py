"""
SW JSON Event Sampler - Analyze and visualize data from .json trace files
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

import parsers.tools as tools


@dataclass
class EventMetrics:
    """Container for event analysis metrics."""
    event_name: str = ""
    total_events: int = 0
    peak_value: float = 0
    start_time: float = float('inf')
    end_time: float = 0
    duration: float = 0
    accumulated: Dict[str, float] = field(default_factory=dict)
    chart_data: List[Tuple[float, float, str]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert metrics to dictionary format for JSON export."""
        peak_str = f"{round(self.peak_value / 1e6, 2)} MB" if self.peak_value >= 1e6 else f"{round(self.peak_value, 2)}"
        
        result = {
            "event_name": self.event_name,
            "total_event_number": self.total_events,
            "peak_value": peak_str,
            "event_start": self.start_time,
            "event_end": self.end_time,
            "duration": self.duration,
            "accumulated_event": self.accumulated,
            "events_for_charts": self.chart_data
        }
        
        # Add bandwidth metrics if applicable
        if "Bandwidth" in self.event_name:
            total_bandwidth = sum(v for k, v in self.accumulated.items() 
                                if k not in ["Total_Memory_Bandwidth", "Average_Memory_BW_(GB/s)"])
            if total_bandwidth > 0 and self.duration > 0:
                duration_seconds = self.duration / 1e6
                result["accumulated_event"]["Total_Memory_Bandwidth"] = total_bandwidth
                result["accumulated_event"]["Average_Memory_BW_(GB/s)"] = round(
                    (total_bandwidth / 1e9) / duration_seconds, 2
                )
        
        return result


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog='SW JSON Event Sampler',
        description='Parse and analyze .json trace files for event metrics and visualization'
    )
    parser.add_argument(
        '-i', '--input',
        help='Input .json file path'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output path for results (without extension)'
    )
    parser.add_argument(
        '-e', '--events',
        nargs='+',
        help='Event names to analyze (space-separated). If not provided, all events will be analyzed.'
    )
    parser.add_argument(
        '--list-events',
        action='store_true',
        help='List all available event names in the file and exit'
    )
    parser.add_argument(
        '-hb', '--hobl',
        action='store_true',
        help='HOBL mode: look for .PASS or .FAIL file in folder'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=10,
        help='Number of raw samples to collect per event category (default: 10)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-collect and overwrite sample JSON files, ignoring existing-sample skip checks'
    )
    parser.add_argument(
        '--chart',
        action='store_true',
        help='Generate charts for each event (works with -i source file or --from-split)'
    )
    parser.add_argument(
        '--from-split',
        metavar='DIR',
        help='Directory containing pre-split *_events.jsonl files; generate charts without re-reading source'
    )
    return parser.parse_args()


def select_file_dialog(script_dir: Path) -> Optional[Path]:
    """Show file selection dialog and return selected file path."""
    import tkinter as tk
    from tkinter import filedialog
    
    root = tk.Tk()
    root.withdraw()
    
    last_folder_file = script_dir / "src" / "last_opened_folder.txt"
    initial_dir = None
    
    # Load last opened folder
    if last_folder_file.exists():
        try:
            initial_dir = last_folder_file.read_text().strip()
        except Exception as e:
            print(f"Warning: Could not read last folder: {e}")
    
    # Show file dialog
    file_path = filedialog.askopenfilename(
        title="Select a .json file",
        initialdir=initial_dir,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    
    if file_path:
        # Save last opened folder
        tools.saveLastOpenedFolder(str(Path(file_path).parent))
        return Path(file_path)
    
    return None


def load_swjson(file_path: Path) -> Optional[dict]:
    """Load and parse a .json file."""
    if file_path.suffix != '.json':
        print(f"Error: Invalid file extension. Expected .json, got {file_path.suffix}")
        return None
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON - {e}")
        return None
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        return None


def parse_trace_events(data: dict) -> Dict[str, List[dict]]:
    """Parse trace events and organize by category."""
    if "traceEvents" not in data or not data["traceEvents"]:
        print("Warning: No trace events found in file")
        return {}
    
    events_by_category = {}
    for event in data["traceEvents"]:
        if "cat" in event:
            category = event["cat"]
            if category not in events_by_category:
                events_by_category[category] = []
            events_by_category[category].append(event)
    
    print(f"Found {len(events_by_category)} event categories")
    return events_by_category


def analyze_events(events: List[dict], event_name: str) -> EventMetrics:
    """Analyze events and calculate metrics for any event type."""
    metrics = EventMetrics(event_name=event_name)
    
    for event in events:
        timestamp = event.get("ts", 0)
        
        # Update time range
        metrics.start_time = min(metrics.start_time, timestamp)
        metrics.end_time = max(metrics.end_time, timestamp)
        
        # Process event arguments
        if "args" in event and event["args"]:
            metrics.total_events += 1
            
            for metric_name, value in event["args"].items():
                # Accumulate values per metric
                if metric_name not in metrics.accumulated:
                    metrics.accumulated[metric_name] = 0
                metrics.accumulated[metric_name] += value
                
                # Track peak value
                metrics.peak_value = max(metrics.peak_value, value)
                
                # Store data for charting
                metrics.chart_data.append((timestamp, value, metric_name))
    
    # Calculate derived metrics
    metrics.duration = metrics.end_time - metrics.start_time
    
    return metrics


def create_event_chart(metrics: EventMetrics, output_path: Path):
    """Create scatter plot for any event type."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"Warning: matplotlib not installed, skipping chart for {metrics.event_name}")
        return

    if not metrics.chart_data:
        print(f"Warning: No chart data available for {metrics.event_name}")
        return
    
    # Organize data by metric/channel
    metric_data = {}
    for timestamp, value, metric_name in metrics.chart_data:
        if metric_name not in metric_data:
            metric_data[metric_name] = {'time': [], 'values': []}
        metric_data[metric_name]['time'].append(timestamp / 1e6)  # Convert to seconds
        
        # Smart unit conversion based on value magnitude
        if "Bandwidth" in metrics.event_name and value >= 1e6:
            metric_data[metric_name]['values'].append(value / 1e6)  # Convert to MB/s
        elif value >= 1e9:
            metric_data[metric_name]['values'].append(value / 1e9)  # Convert to GB
        elif value >= 1e6:
            metric_data[metric_name]['values'].append(value / 1e6)  # Convert to MB
        else:
            metric_data[metric_name]['values'].append(value)
    
    # Determine appropriate Y-axis label
    y_label = "Value"
    if "Bandwidth" in metrics.event_name:
        if metrics.peak_value >= 1e6:
            y_label = "Bandwidth (MB/s)"
        else:
            y_label = "Bandwidth (B/s)"
    elif "Power" in metrics.event_name:
        y_label = "Power (W)"
    elif "Frequency" in metrics.event_name:
        y_label = "Frequency (MHz)"
    elif "Voltage" in metrics.event_name:
        y_label = "Voltage (V)"
    elif "Temperature" in metrics.event_name:
        y_label = "Temperature (°C)"
    elif "P-State" in metrics.event_name:
        y_label = "P-State"
    elif "C-State" in metrics.event_name:
        y_label = "Residency (µs)"
    
    # For Bandwidth events: compute total BW per timestamp (sum of all channels at same ts)
    is_bandwidth = "Bandwidth" in metrics.event_name
    total_bw_series = None
    if is_bandwidth and len(metric_data) >= 1:
        from collections import defaultdict
        total_by_ts: dict = defaultdict(float)
        for timestamp, value, _ in metrics.chart_data:
            converted = value / 1e6 if value >= 1e6 else value
            total_by_ts[timestamp / 1e6] += converted
        if total_by_ts:
            sorted_ts = sorted(total_by_ts.keys())
            total_bw_series = (sorted_ts, [total_by_ts[t] for t in sorted_ts])

    # Create plot
    plt.figure(figsize=(14, 8))

    for metric_name, data in metric_data.items():
        label = metric_name if metric_name else metrics.event_name
        plt.scatter(data['time'], data['values'], label=label, s=10, alpha=0.5)

    # Overlay Total Memory BW as a bold line on top (Bandwidth events only)
    if total_bw_series is not None:
        plt.plot(
            total_bw_series[0],
            total_bw_series[1],
            label="Total Memory BW",
            color="black",
            linewidth=1.5,
            alpha=0.85,
            zorder=10,
        )

    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel(y_label, fontsize=12)

    # Clean title
    title = metrics.event_name.replace("(", "").replace(")", "")
    plt.title(f'{title} Over Time', fontsize=14, fontweight='bold')

    # Always show legend for bandwidth (total line is always added)
    if len(metric_data) > 1 or total_bw_series is not None:
        plt.legend(loc='best', fontsize=9, ncol=2)

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save chart with sanitized filename
    safe_name = metrics.event_name.replace("/", "_").replace("(", "").replace(")", "").replace(" ", "_")
    chart_path = output_path.with_name(f"{output_path.stem}_{safe_name}_chart.png")
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    print(f"Chart saved: {chart_path.name}")
    plt.close()


def load_events_from_jsonl(jsonl_path: Path) -> List[dict]:
    """Load all events from a per-event JSONL split file."""
    events = []
    try:
        with open(jsonl_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping malformed line {line_num} in {jsonl_path.name}: {e}")
    except FileNotFoundError:
        print(f"Error: Split file not found - {jsonl_path}")
    return events


def list_events_from_split_dir(split_dir: Path) -> Dict[str, Path]:
    """Discover per-event JSONL files in a split directory.

    Returns a dict mapping event_name -> jsonl_path.
    Event name is inferred from the filename suffix pattern *_events.jsonl.
    """
    event_files: Dict[str, Path] = {}
    for jsonl_file in sorted(split_dir.glob('*_events.jsonl')):
        # Filename: <stem>_events.jsonl  -> strip trailing _events
        stem = jsonl_file.stem  # e.g. "DDR_Bandwidth_Requests_by_Component_events"
        if stem.endswith('_events'):
            safe_name = stem[:-len('_events')]
        else:
            safe_name = stem
        # Reverse sanitization: underscores may represent spaces or slashes;
        # use the cat field from the first line for the real event name.
        try:
            with open(jsonl_file, 'r') as f:
                first_line = f.readline().strip()
            if first_line:
                first_event = json.loads(first_line)
                event_name = first_event.get('cat', safe_name)
            else:
                event_name = safe_name
        except Exception:
            event_name = safe_name
        event_files[event_name] = jsonl_file
    return event_files


def generate_charts_from_events(
    events_by_category: Dict[str, List[dict]],
    target_events: List[str],
    output_path: Path,
):
    """Analyze events and generate a chart PNG for each target event."""
    print(f"\nGenerating charts for {len(target_events)} event type(s)...")
    for event_name in target_events:
        events = events_by_category.get(event_name, [])
        if not events:
            print(f"Warning: No events found for '{event_name}', skipping chart")
            continue
        metrics = analyze_events(events, event_name)
        create_event_chart(metrics, output_path)


def save_event_results(metrics: EventMetrics, output_path: Path):
    """Save analysis results to JSON file."""
    safe_name = metrics.event_name.replace("/", "_").replace("(", "").replace(")", "").replace(" ", "_")
    summary_path = output_path.with_name(f"{output_path.stem}_{safe_name}_summary.json")
    
    with open(summary_path, 'w') as f:
        json.dump(metrics.to_dict(), f, indent=4)
    print(f"Summary saved: {summary_path.name}")


def save_event_samples(
    events_by_category: Dict[str, List[dict]],
    target_events: List[str],
    output_path: Path,
    sample_size: int = 10,
    force: bool = False,
):
    """Save up to N raw events per event category to separate JSON files."""
    print(f"\nSaving up to {sample_size} sample event(s) per category for structure check...")
    if force:
        print("Force mode enabled: existing sample files will be overwritten")

    def select_spread_samples(event_list: List[dict], n_samples: int) -> Tuple[List[dict], List[int]]:
        """Select evenly distributed samples across the full event list (O(n_samples))."""
        total = len(event_list)
        if total == 0 or n_samples <= 0:
            return [], []
        if total <= n_samples:
            return event_list, list(range(total))

        # Evenly spaced indices from start to end for better variety than head-only sampling.
        indices = sorted(
            {
                int(round(i * (total - 1) / (n_samples - 1)))
                for i in range(n_samples)
            }
        )

        # Guard against rare duplicate rounding collisions.
        if len(indices) < n_samples:
            seen = set(indices)
            cursor = 0
            while len(indices) < n_samples and cursor < total:
                if cursor not in seen:
                    indices.append(cursor)
                    seen.add(cursor)
                cursor += 1
            indices.sort()

        return [event_list[idx] for idx in indices], indices

    for event_name in target_events:
        events = events_by_category.get(event_name, [])
        samples, sample_indices = select_spread_samples(events, sample_size)
        required_samples = min(sample_size, len(events))

        safe_name = event_name.replace("/", "_").replace("(", "").replace(")", "").replace(" ", "_")
        sample_path = output_path.with_name(f"{output_path.stem}_{safe_name}_samples.json")

        # Resume support: skip if this event already has enough collected samples
        if sample_path.exists() and not force:
            try:
                with open(sample_path, 'r') as f:
                    existing_payload = json.load(f)
                existing_samples = existing_payload.get("samples", [])
                if isinstance(existing_samples, list) and len(existing_samples) >= required_samples:
                    print(
                        f"Samples skipped: {sample_path.name} "
                        f"({len(existing_samples)}/{required_samples} already collected)"
                    )
                    continue
            except Exception as e:
                print(f"Warning: Could not read existing sample file {sample_path.name}: {e}. Rewriting...")

        sample_payload = {
            "event_name": event_name,
            "total_events": len(events),
            "sample_count": len(samples),
            "sample_size_limit": sample_size,
            "sample_strategy": "evenly_distributed",
            "sample_indices": sample_indices,
            "samples": samples,
        }

        try:
            with open(sample_path, 'w') as f:
                json.dump(sample_payload, f, indent=4)
            print(f"Samples saved: {sample_path.name} ({len(samples)}/{len(events)})")
        except Exception as e:
            print(f"Warning: Failed to save samples for {event_name}: {e}")


def main():
    """Main execution flow."""
    args = parse_arguments()
    script_dir = Path(__file__).parent

    # ------------------------------------------------------------------ #
    # Mode A: --from-split  (chart from pre-split JSONL files, no source) #
    # ------------------------------------------------------------------ #
    if args.from_split:
        split_dir = Path(args.from_split)
        if not split_dir.is_dir():
            tools.errorAndExit(f"Split directory not found: {split_dir}")

        print(f"Loading split events from: {split_dir}")
        event_files = list_events_from_split_dir(split_dir)
        if not event_files:
            tools.errorAndExit(f"No *_events.jsonl files found in: {split_dir}")

        print(f"Found {len(event_files)} event file(s)")

        # Handle --list-events for split dir
        if args.list_events:
            print(f"\nAvailable events in split directory ({len(event_files)}):")
            for i, name in enumerate(sorted(event_files.keys()), 1):
                print(f"  {i:2d}. {name}")
            return

        # Filter to requested events if -e was given
        if args.events:
            target_events = [e for e in args.events if e in event_files]
            missing = [e for e in args.events if e not in event_files]
            for m in missing:
                print(f"Warning: Event '{m}' not found in split directory")
            if not target_events:
                tools.errorAndExit("None of the specified events were found")
        else:
            target_events = list(event_files.keys())

        # Set output path
        output_path = Path(args.output) if args.output else split_dir.parent / f"{split_dir.name}_charts"
        output_path.mkdir(parents=True, exist_ok=True)
        output_base = output_path / split_dir.name

        # Load each JSONL and generate chart
        print(f"\nGenerating charts for {len(target_events)} event type(s)...")
        for event_name in target_events:
            print(f"  Loading: {event_files[event_name].name}")
            events = load_events_from_jsonl(event_files[event_name])
            if not events:
                print(f"  Warning: No events loaded for '{event_name}', skipping")
                continue
            metrics = analyze_events(events, event_name)
            create_event_chart(metrics, output_base)

        print(f"\n✓ Charts saved to: {output_path}")
        return

    # ------------------------------------------------------------------ #
    # Mode B: -i source.json  (sample and/or chart from source file)      #
    # ------------------------------------------------------------------ #

    # Get input file path
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = select_file_dialog(script_dir)
        if not input_path:
            tools.errorAndExit("No file selected")

    if not input_path.exists():
        tools.errorAndExit(f"File not found: {input_path}")

    print(f"Processing: {input_path.name}")

    # Load and parse data
    data = load_swjson(input_path)
    if not data:
        tools.errorAndExit(f"Failed to load {input_path}")

    events_by_category = parse_trace_events(data)
    if not events_by_category:
        tools.errorAndExit("No events found in file")

    # Handle --list-events flag
    if args.list_events:
        print(f"\nAvailable event categories ({len(events_by_category)}):")
        for i, category in enumerate(sorted(events_by_category.keys()), 1):
            event_count = len(events_by_category[category])
            print(f"  {i:2d}. {category} ({event_count} events)")
        return

    # Set output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_analysis"

    # Determine which events to process
    if args.events:
        target_events = []
        for event_name in args.events:
            if event_name in events_by_category:
                target_events.append(event_name)
            else:
                print(f"Warning: Event '{event_name}' not found in file")
        if not target_events:
            print("\nAvailable events:")
            for category in sorted(events_by_category.keys()):
                print(f"  - {category}")
            tools.errorAndExit("None of the specified events were found")
    else:
        target_events = list(events_by_category.keys())

    # Generate charts if requested
    if args.chart:
        generate_charts_from_events(events_by_category, target_events, output_path)

    # Save raw samples (unless we're only charting and sample_size == 0)
    if args.sample_size > 0:
        print(f"\nCollecting samples for {len(target_events)} event type(s)...")
        save_event_samples(
            events_by_category,
            target_events,
            output_path,
            sample_size=args.sample_size,
            force=args.force,
        )
        print(f"\n✓ Sample collection complete! Results saved to: {output_path.parent}")
    elif not args.chart:
        tools.errorAndExit("--sample-size must be > 0 (or use --chart to only generate charts)")


if __name__ == "__main__":
    main()
