"""
SWJSON Parser - Analyze and visualize data from .swjson trace files
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

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
        prog='SWJSON Parser',
        description='Parse and analyze .swjson or .json trace files for event metrics and visualization'
    )
    parser.add_argument(
        '-i', '--input',
        help='Input .swjson or .json file path'
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
        title="Select a .swjson or .json file",
        initialdir=initial_dir,
        filetypes=[("JSON files", "*.swjson *.json"), ("SWJSON files", "*.swjson"), ("JSON files", "*.json"), ("All files", "*.*")]
    )
    
    if file_path:
        # Save last opened folder
        tools.saveLastOpenedFolder(str(Path(file_path).parent))
        return Path(file_path)
    
    return None


def load_swjson(file_path: Path) -> Optional[dict]:
    """Load and parse a .swjson or .json file."""
    if file_path.suffix not in ['.swjson', '.json']:
        print(f"Error: Invalid file extension. Expected .swjson or .json, got {file_path.suffix}")
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
    
    # Create plot
    plt.figure(figsize=(14, 8))
    
    for metric_name, data in metric_data.items():
        label = metric_name if metric_name else metrics.event_name
        plt.scatter(data['time'], data['values'], label=label, s=10, alpha=0.7)
    
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    
    # Clean title
    title = metrics.event_name.replace("(", "").replace(")", "")
    plt.title(f'{title} Over Time', fontsize=14, fontweight='bold')
    
    # Only show legend if there are multiple metrics
    if len(metric_data) > 1:
        plt.legend(loc='best', fontsize=9, ncol=2)
    
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save chart with sanitized filename
    safe_name = metrics.event_name.replace("/", "_").replace("(", "").replace(")", "").replace(" ", "_")
    chart_path = output_path.with_name(f"{output_path.stem}_{safe_name}_chart.png")
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    print(f"Chart saved: {chart_path.name}")
    plt.close()


def save_event_results(metrics: EventMetrics, output_path: Path):
    """Save analysis results to JSON file."""
    safe_name = metrics.event_name.replace("/", "_").replace("(", "").replace(")", "").replace(" ", "_")
    summary_path = output_path.with_name(f"{output_path.stem}_{safe_name}_summary.json")
    
    with open(summary_path, 'w') as f:
        json.dump(metrics.to_dict(), f, indent=4)
    print(f"Summary saved: {summary_path.name}")


def main():
    """Main execution flow."""
    args = parse_arguments()
    script_dir = Path(__file__).parent
    
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
    
    # Determine which events to analyze
    if args.events:
        # User specified event names
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
        # Analyze all events
        target_events = list(events_by_category.keys())
    
    print(f"\nAnalyzing {len(target_events)} event type(s)...")
    
    # Analyze each event type
    for event_name in target_events:
        print(f"\n[{event_name}]")
        events = events_by_category[event_name]
        
        # Analyze events
        metrics = analyze_events(events, event_name)
        
        # Save results
        save_event_results(metrics, output_path)
        
        # Generate chart
        create_event_chart(metrics, output_path)
        
        # Print summary
        print(f"  Events: {metrics.total_events}")
        print(f"  Duration: {metrics.duration / 1e6:.2f} seconds")
        if metrics.peak_value > 0:
            if metrics.peak_value >= 1e6:
                print(f"  Peak: {metrics.peak_value / 1e6:.2f} MB")
            else:
                print(f"  Peak: {metrics.peak_value:.2f}")
    
    print(f"\n✓ Analysis complete! Results saved to: {output_path.parent}")


if __name__ == "__main__":
    main()
