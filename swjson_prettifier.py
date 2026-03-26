#!/usr/bin/env python3
"""
SWJSON Prettifier

Reads a compact single-line .swjson (or .json) file and writes a
human-readable indented copy next to the original.

Optionally reduces each series' "points" array to N evenly-spaced samples
so the output is small enough to read and understand the data structure.

Output file:
  <stem>.pretty.json           (full data)
  <stem>.s<N>.pretty.json      (when --sample-points N is used)

Usage:
    python swjson_prettifier.py                              # file-picker dialog
    python swjson_prettifier.py -i path/to/file.swjsonrename "swjson2_event_sampler.py" to "swjson_event_sampler.py"
    python swjson_prettifier.py -i file.swjson -o out.json
    python swjson_prettifier.py -i file.swjson --indent 4
    python swjson_prettifier.py -i file.swjson --sample-points 10
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='swjson_prettifier',
        description='Prettify a compact .swjson/.json file into indented, human-readable JSON'
    )
    parser.add_argument(
        '-i', '--input',
        help='Input .swjson or .json file path'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: <input_stem>.pretty.json beside the input)'
    )
    parser.add_argument(
        '--indent',
        type=int,
        default=2,
        metavar='N',
        help='Number of spaces for indentation (default: 2)'
    )
    parser.add_argument(
        '--sample-points',
        type=int,
        default=0,
        metavar='N',
        help=(
            'Reduce each series points array to N evenly-spaced samples '
            '(0 = keep all, default: 0)'
        )
    )
    return parser.parse_args()


def select_file_dialog(initial_dir: Optional[Path] = None) -> Optional[Path]:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title='Select a .swjson or .json file to prettify',
        initialdir=str(initial_dir) if initial_dir else None,
        filetypes=[
            ('SWJSON / JSON files', '*.swjson *.json'),
            ('All files', '*.*'),
        ],
    )
    root.destroy()
    return Path(file_path) if file_path else None


def _spread_sample(points: list, n: int) -> Tuple[list, int]:
    """Return (sampled_list, original_count) with N evenly-spaced items."""
    total = len(points)
    if n <= 0 or total <= n:
        return points, total
    indices = sorted({
        int(round(i * (total - 1) / (n - 1)))
        for i in range(n)
    })
    return [points[idx] for idx in indices], total


def reduce_points(data: dict, n: int) -> Dict[str, Tuple[int, int]]:
    """
    Reduce points arrays in-place to at most N evenly-spaced samples.
    Returns a stats dict: { label: (kept, original) }
    Handles both the new swjson metric format and legacy traceEvents format.
    """
    stats: Dict[str, Tuple[int, int]] = {}

    # New swjson format: data -> <category> -> data -> <series> -> points
    metric_root = data.get('data')
    if isinstance(metric_root, dict):
        for cat_name, cat_payload in metric_root.items():
            if not isinstance(cat_payload, dict):
                continue
            series_map = cat_payload.get('data', {})
            if not isinstance(series_map, dict):
                continue
            for series_key, series_payload in series_map.items():
                if not isinstance(series_payload, dict):
                    continue
                points = series_payload.get('points')
                if not isinstance(points, list):
                    continue
                sampled, original = _spread_sample(points, n)
                series_payload['points'] = sampled
                label = f'{cat_name} / {series_key}'
                stats[label] = (len(sampled), original)
        return stats

    # Legacy Chrome trace format: traceEvents flat list
    trace_events = data.get('traceEvents')
    if isinstance(trace_events, list):
        sampled, original = _spread_sample(trace_events, n)
        data['traceEvents'] = sampled
        stats['traceEvents'] = (len(sampled), original)

    return stats


def prettify(input_path: Path, output_path: Path, indent: int, sample_points: int = 0) -> None:
    print(f'Reading : {input_path}')

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise SystemExit(f'Error: Failed to parse JSON — {e}')
    except OSError as e:
        raise SystemExit(f'Error: Cannot read file — {e}')

    if sample_points > 0:
        print(f'Sampling: keeping up to {sample_points} points per series ...')
        stats = reduce_points(data, sample_points)
        total_kept = sum(k for k, _ in stats.values())
        total_orig = sum(o for _, o in stats.values())
        for label, (kept, original) in sorted(stats.items()):
            if original != kept:
                print(f'  {label}: {original:,} -> {kept:,} points')
        if total_orig:
            print(f'  Total : {total_orig:,} -> {total_kept:,} points '
                  f'({100 * total_kept / total_orig:.1f}% kept)')

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        print(f'Saved   : {output_path}')
        print(f'Size    : {output_path.stat().st_size:,} bytes')
    except OSError as e:
        raise SystemExit(f'Error: Cannot write output — {e}')


def main() -> None:
    args = parse_arguments()

    # Resolve input path
    if args.input:
        input_path = Path(args.input)
    else:
        script_dir = Path(__file__).parent
        # Default initial dir to temp/ if it exists
        default_dir = script_dir / 'temp' if (script_dir / 'temp').is_dir() else script_dir
        input_path = select_file_dialog(default_dir)
        if not input_path:
            raise SystemExit('No file selected.')

    if not input_path.exists():
        raise SystemExit(f'Error: File not found — {input_path}')

    if input_path.suffix not in ('.swjson', '.json'):
        raise SystemExit(
            f'Error: Expected a .swjson or .json file, got "{input_path.suffix}"'
        )

    if args.sample_points < 0:
        raise SystemExit('Error: --sample-points must be >= 0')

    # Resolve output path
    if args.output:
        output_path = Path(args.output)
    else:
        if args.sample_points > 0:
            stem = f'{input_path.stem}.s{args.sample_points}.pretty'
        else:
            stem = f'{input_path.stem}.pretty'
        output_path = input_path.with_name(f'{stem}.json')

    if output_path.resolve() == input_path.resolve():
        raise SystemExit('Error: Output path is the same as input — refusing to overwrite.')

    prettify(input_path, output_path, indent=args.indent, sample_points=args.sample_points)
    print('Done.')


if __name__ == '__main__':
    main()
