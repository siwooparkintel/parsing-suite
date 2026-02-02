#!/usr/bin/env python3
"""
Power Trace Slicer

This script slices power trace files based on specified power rails and time ranges.
Trace files have -NNNsr.csv suffix, where NNN is the sample rate.
Time values in trace files are in seconds, but are converted to milliseconds for processing.
"""

import pandas as pd
import argparse
import os
import json
from pathlib import Path
from typing import List, Dict, Tuple
try:
    import openpyxl
except ImportError:
    openpyxl = None


def parse_sample_rate(filename: str) -> int:
    """Extract sample rate from filename (e.g., -100sr.csv)"""
    if '-' in filename and 'sr.csv' in filename:
        parts = filename.split('-')
        for part in parts:
            if 'sr.csv' in part:
                return int(part.replace('sr.csv', ''))
    return 100  # default


def load_trace_file(filepath: str) -> pd.DataFrame:
    """Load the power trace CSV file and convert time to milliseconds"""
    df = pd.read_csv(filepath)
    # Convert time from seconds to milliseconds
    time_col = df.columns[0]
    df[time_col] = df[time_col] * 1000
    print(f"Loaded trace file with {len(df)} rows and {len(df.columns)} columns")
    print(f"Time range: {df[time_col].min():.2f} to {df[time_col].max():.2f} ms")
    print(f"Columns: {list(df.columns[:5])}... (showing first 5)")
    return df


def slice_trace(df: pd.DataFrame, 
                power_rails: List[str], 
                time_ranges: List[Dict]) -> List[Tuple[pd.DataFrame, Dict]]:
    """
    Slice the trace file by power rails and time ranges.
    
    Args:
        df: Input DataFrame (with time in milliseconds)
        power_rails: List of power rail column names to include
        time_ranges: List of dicts with 'start', 'end', 'name' keys in milliseconds
        
    Returns:
        List of (sliced_df, time_range_dict) tuples
    """
    results = []
    
    # Validate power rails
    time_col = df.columns[0]  # First column is timestamp
    available_rails = df.columns[1:].tolist()
    
    # Filter valid power rails
    valid_rails = []
    for rail in power_rails:
        if rail in available_rails:
            valid_rails.append(rail)
        else:
            print(f"Warning: Power rail '{rail}' not found in trace file")
    
    if not valid_rails:
        print(f"Error: None of the specified power rails found. Available rails: {available_rails[:10]}...")
        return results
    
    # Process each time range
    for tr in time_ranges:
        start_ms = tr['start']
        end_ms = tr['end']
        name = tr.get('name', '')
        # Filter by time range
        mask = (df[time_col] >= start_ms) & (df[time_col] <= end_ms)
        sliced = df.loc[mask, [time_col] + valid_rails].copy()
        
        if len(sliced) == 0:
            print(f"Warning: No data found in time range [{start_ms}, {end_ms}] ({name})")
            continue
        
        # Calculate averages and peaks for each power rail
        # Create summary rows to insert at the beginning
        header_row_summary = {col: col for col in sliced.columns}
        header_row_summary[time_col] = 'Power Rail Name'  # For summary section
        
        header_row_data = {col: col for col in sliced.columns}  # For data section (keeps "Time")
        
        avg_row = {}
        avg_row[time_col] = 'Average'
        for rail in valid_rails:
            avg_row[rail] = sliced[rail].mean()
        
        peak_row = {}
        peak_row[time_col] = 'Peak'
        for rail in valid_rails:
            peak_row[rail] = sliced[rail].max()
        
        # Insert header (with Power Rail Name), average, peak, another header (with Time), then data
        summary_df = pd.DataFrame([header_row_summary, avg_row, peak_row, header_row_data])
        sliced = pd.concat([summary_df, sliced], ignore_index=True)
        
        results.append((sliced, tr))
        print(f"Sliced {len(sliced)-4} rows for time range [{start_ms}, {end_ms}] ms ({name})")
    
    return results


def create_summary_excel(slices: List[Tuple[pd.DataFrame, Dict]], 
                         output_dir: str,
                         base_filename: str):
    """
    Create a summary Excel file with transposed average data.
    
    Args:
        slices: List of (sliced_df, time_range_dict) tuples
        output_dir: Output directory
        base_filename: Base name for output files
    """
    if openpyxl is None:
        print("Warning: openpyxl not installed. Skipping Excel summary generation.")
        print("Install with: pip install openpyxl")
        return
    
    # Extract power rail names from first slice (excluding the 4 summary rows)
    first_df = slices[0][0]
    power_rails = list(first_df.columns)[1:]  # Skip Time column
    
    # Build summary data structure
    summary_data = {'Power Rail': power_rails}
    
    for idx, (sliced_df, tr) in enumerate(slices):
        start_ms = tr['start']
        end_ms = tr['end']
        name = tr.get('name', '')
        # Use name if available, otherwise use time range
        col_name = name if name else f"Slice_{idx}_({int(start_ms)}-{int(end_ms)}ms)"
        # Average row is at index 1 (after first header row)
        avg_values = sliced_df.iloc[1, 1:].values  # Skip first column (Power Rail Name/Average)
        summary_data[col_name] = avg_values
    
    # Add WL_start, WL_end, WL_duration columns
    # These represent the time ranges for each slice (same for all power rails)
    wl_starts = []
    wl_ends = []
    wl_durations = []
    
    for sliced_df, tr in slices:
        wl_starts.append(tr['start'])
        wl_ends.append(tr['end'])
        wl_durations.append(tr['end'] - tr['start'])
    
    # For each power rail, add the time range info (will be the same across rows but conceptually represents the workload)
    # Actually, let's add these as additional metadata rows instead
    
    # Create DataFrame
    summary_df = pd.DataFrame(summary_data)
    
    # Add workload metadata as separate rows at the bottom
    wl_start_row = ['WL_start (ms)'] + wl_starts + [None] * (len(summary_data) - len(wl_starts) - 1)
    wl_end_row = ['WL_end (ms)'] + wl_ends + [None] * (len(summary_data) - len(wl_ends) - 1)
    wl_duration_row = ['WL_duration (ms)'] + wl_durations + [None] * (len(summary_data) - len(wl_durations) - 1)
    
    # Save to Excel
    output_filename = f"{base_filename}_summary.xlsx"
    output_path = os.path.join(output_dir, output_filename)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='Power_Summary', index=False)
        
        # Add metadata rows
        workbook = writer.book
        worksheet = writer.sheets['Power_Summary']
        
        start_row = len(summary_df) + 3  # Add some space
        worksheet.append([])  # Empty row
        worksheet.append(wl_start_row)
        worksheet.append(wl_end_row)
        worksheet.append(wl_duration_row)
    
    print(f"Summary Excel created: {output_path}")


def save_slices(slices: List[Tuple[pd.DataFrame, Dict]], 
                output_dir: str,
                base_filename: str):
    """
    Save sliced data to CSV files with sequential numbering.
    
    Args:
        slices: List of (sliced_df, time_range_dict) tuples
        output_dir: Output directory
        base_filename: Base name for output files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    for idx, (sliced_df, tr) in enumerate(slices):
        start_ms = tr['start']
        end_ms = tr['end']
        name = tr.get('name', '')
        # Format: 000_basename_name_startms_endms.csv or 000_basename_startms_endms.csv
        if name:
            output_filename = f"{idx:03d}_{base_filename}_{name}_{start_ms:.0f}ms_{end_ms:.0f}ms.csv"
        else:
            output_filename = f"{idx:03d}_{base_filename}_{start_ms:.0f}ms_{end_ms:.0f}ms.csv"
        output_path = os.path.join(output_dir, output_filename)
        
        sliced_df.to_csv(output_path, index=False, header=False)
        print(f"Saved: {output_path}")


def load_config(config_path: str) -> Dict:
    """Load configuration from JSON file"""
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config


def save_last_opened_file(file_path: str):
    """Save the last opened file path for future use"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(script_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        last_file = os.path.join(src_dir, "last_opened_trace.txt")
        # Save the directory, not the file
        last_dir = os.path.dirname(file_path)
        with open(last_file, "w") as f:
            f.write(last_dir)
    except Exception as e:
        print(f"Failed to save last opened file: {e}")


def select_trace_file() -> str:
    """Open a file dialog to select a trace file"""
    import tkinter as tk
    from tkinter import filedialog
    
    root = tk.Tk()
    root.withdraw()
    
    # Try to load last opened directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    last_file = os.path.join(script_dir, "src", "last_opened_trace.txt")
    initial_dir = None
    
    try:
        with open(last_file, "r") as f:
            initial_dir = f.read().strip()
            if not os.path.exists(initial_dir):
                initial_dir = None
    except Exception:
        pass
    
    # Open file dialog
    if initial_dir:
        file_path = filedialog.askopenfilename(
            title="Select a power trace CSV file",
            initialdir=initial_dir,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
    else:
        file_path = filedialog.askopenfilename(
            title="Select a power trace CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
    
    if file_path:
        save_last_opened_file(file_path)
        return file_path
    else:
        return None


def main():
    parser = argparse.ArgumentParser(description='Slice power trace files by power rails and time ranges')
    parser.add_argument('trace_file', nargs='?', help='Path to the power trace CSV file (optional, will open file dialog if not provided)')
    parser.add_argument('--config', '-c', help='Path to JSON config file with power rails and time ranges')
    parser.add_argument('--rails', '-r', nargs='+', help='Power rail column names to include')
    parser.add_argument('--time-ranges', '-t', nargs='+', 
                        help='Time ranges in format "start:end" (in milliseconds), e.g., "0:10000" "20000:40000"')
    parser.add_argument('--output-dir', '-o', default='./sliced_output', 
                        help='Output directory for sliced files (default: ./sliced_output)')
    
    args = parser.parse_args()
    
    # Handle trace file selection
    trace_file = args.trace_file
    if trace_file is None:
        trace_file = select_trace_file()
        if trace_file is None:
            print("Error: No trace file selected")
            return
        print(f"Selected file: {trace_file}")
    
    # Load configuration
    if args.config:
        config = load_config(args.config)
        power_rails = config.get('power_rails', [])
        time_ranges = config.get('time_ranges', [])
        # Validate time_ranges format
        for tr in time_ranges:
            if not isinstance(tr, dict) or 'start' not in tr or 'end' not in tr:
                print(f"Error: Invalid time_range format: {tr}")
                print("Expected format: {{\"start\": <ms>, \"end\": <ms>, \"name\": <name>}}")
                return
    else:
        if not args.rails or not args.time_ranges:
            print("Error: Either --config or both --rails and --time-ranges must be provided")
            parser.print_help()
            return
        
        power_rails = args.rails
        time_ranges = []
        for idx, tr in enumerate(args.time_ranges):
            start, end = map(float, tr.split(':'))
            time_ranges.append({'start': start, 'end': end, 'name': f'Range_{idx}'})
    
    # Load trace file
    df = load_trace_file(trace_file)
    
    # Extract base filename
    base_filename = Path(trace_file).stem
    
    # Slice the trace
    slices = slice_trace(df, power_rails, time_ranges)
    
    if not slices:
        print("No slices generated. Please check your configuration.")
        return
    
    # Save slices
    save_slices(slices, args.output_dir, base_filename)
    
    # Create summary Excel
    create_summary_excel(slices, args.output_dir, base_filename)
    
    print(f"\nProcessing complete! Generated {len(slices)} slice(s)")


if __name__ == '__main__':
    main()
