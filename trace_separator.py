#!/usr/bin/env python3
"""
trace_separator.py

Splits a large SoCWatch time-based-event trace CSV into per-event-type CSV files.

Each section in the trace looks like:

    <blank line>
    Event Name - Sub-Unit
    Sample #, Continuous Time (ms), ...
    <data rows starting with digit>

Sections are grouped by their *base event type* (the part before the first " - ").
For example:
    "Core C-State (OS) - CPU/Package_0/Core_0"  →  Core_C-State_(OS).csv
    "CPU P-state - CPU/Package_0/Core_0"         →  CPU_P-state.csv
    "Memory Subsystem (MEMSS) P-state - MEMSS"   →  Memory_Subsystem_(MEMSS)_P-state.csv

Every output CSV includes a leading "Section" column with the original full section
name so you know which core / channel each row came from.

Usage:
    python trace_separator.py <input_file> [output_dir]
    python trace_separator.py <input_file> --out <output_dir>
    python trace_separator.py <input_file> --list      # just list event types, no output
"""

import re
import sys
import argparse
from collections import defaultdict
from pathlib import Path


# ── helpers ────────────────────────────────────────────────────────────────────

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*()]')
_MULTI_SPACE   = re.compile(r'\s+')
_DATA_ROW      = re.compile(r'^\s*\d+\s*,')   # "   1,  ..." or "1, ..."


def sanitize_filename(name: str) -> str:
    """Turn an event-type string into a safe filename (no extension)."""
    name = _INVALID_CHARS.sub('_', name)
    name = _MULTI_SPACE.sub('_', name.strip())
    return name[:120]


def event_base(section_name: str) -> str:
    """Return the base event type (text before the first ' - ')."""
    return section_name.split(' - ', 1)[0].strip()


# ── core logic ─────────────────────────────────────────────────────────────────

def list_events(src: Path) -> None:
    """Print every unique event type found in the file without writing any output."""
    counts: dict[str, int] = defaultdict(int)
    prev = ''
    with src.open('r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\r\n').strip()
            if not line:
                continue
            if line.startswith('Sample #,'):
                counts[event_base(prev)] += 1
            prev = line

    print(f"\nFound {len(counts)} event type(s) in {src.name}:\n")
    for base in sorted(counts):
        print(f"  [{counts[base]:>4}x]  {base}")


def separate_trace(src: Path, dst: Path) -> None:
    """Stream through *src* and write per-event-type CSVs into *dst*."""
    dst.mkdir(parents=True, exist_ok=True)

    print(f"Input : {src}")
    print(f"Output: {dst}")
    print("Processing... (may take a minute for large files)\n")

    open_files:      dict[str, object]  = {}           # base → file handle
    written_headers: set[str]           = set()        # bases with header written
    col_headers:     dict[str, str]     = {}           # base → "Sample #, ..." line
    section_counts:  dict[str, int]     = defaultdict(int)
    row_counts:      dict[str, int]     = defaultdict(int)

    cur_base:    str | None = None
    cur_section: str | None = None
    prev:        str        = ''        # last non-blank, stripped line
    in_data:     bool       = False     # have we seen the first "Sample #," yet?
    line_no:     int        = 0
    PROGRESS     = 500_000             # print a dot every N lines

    with src.open('r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            line_no += 1
            if line_no % PROGRESS == 0:
                written = sum(row_counts.values())
                print(f"  … {line_no:,} lines read, {written:,} rows written", flush=True)

            line    = raw.rstrip('\r\n')
            stripped = line.strip()

            if not stripped:
                continue                         # skip blank lines

            # ── New section header ──────────────────────────────────────────
            if stripped.startswith('Sample #,'):
                in_data     = True
                cur_section = prev               # prev non-blank line is the name
                cur_base    = event_base(cur_section)
                col_header  = stripped

                section_counts[cur_base] += 1

                # Open output file on first encounter
                if cur_base not in open_files:
                    fname = sanitize_filename(cur_base) + '.csv'
                    fh    = (dst / fname).open('w', encoding='utf-8', newline='')
                    open_files[cur_base]  = fh
                    col_headers[cur_base] = col_header

            # ── Data row ────────────────────────────────────────────────────
            elif in_data and cur_base and _DATA_ROW.match(stripped):
                fh = open_files[cur_base]

                # Write CSV header once per event type
                if cur_base not in written_headers:
                    written_headers.add(cur_base)
                    fh.write(f'Section,{col_headers[cur_base]}\n')

                fh.write(f'"{cur_section}",{stripped}\n')
                row_counts[cur_base] += 1

            # (any other non-blank line is metadata / annotation — ignored)

            prev = stripped

    for fh in open_files.values():
        fh.close()

    # ── Summary ────────────────────────────────────────────────────────────────
    col_w = max((len(b) for b in open_files), default=10)
    header = f"{'Event Type':<{col_w}}  {'Sections':>8}  {'Rows':>12}  File"
    print(f"\n{header}")
    print('-' * len(header))
    for base in sorted(open_files):
        fname = sanitize_filename(base) + '.csv'
        print(f"{base:<{col_w}}  {section_counts[base]:>8,}  {row_counts[base]:>12,}  {fname}")

    total = sum(row_counts.values())
    print(f"\nTotal rows written : {total:,}")
    print(f"Output directory   : {dst}")


# ── entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Separate a SoCWatch trace CSV into per-event-type files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('input',          help='Path to the _trace.csv file')
    parser.add_argument('out', nargs='?', help='Output directory (optional positional)')
    parser.add_argument('--out',    dest='out_flag', metavar='DIR',
                        help='Output directory (optional flag)')
    parser.add_argument('--list',   action='store_true',
                        help='List event types only; do not write output files')

    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        parser.error(f"File not found: {src}")

    if args.list:
        list_events(src)
        return

    out_dir = args.out_flag or args.out
    dst = Path(out_dir) if out_dir else src.parent / (src.stem + '_separated')
    separate_trace(src, dst)


if __name__ == '__main__':
    main()
