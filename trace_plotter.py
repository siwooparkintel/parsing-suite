#!/usr/bin/env python3
"""
trace_plotter.py

Plots time-based-event CSVs produced by trace_separator.py.

A PLOT_REGISTRY maps event-type base names to PlotConfig objects that control
how each event is rendered. Add entries to extend support for new events.

Usage
-----
  # Auto-detect event type and plot with defaults
  python trace_plotter.py <csv_file>

  # Override time unit on X axis
  python trace_plotter.py <csv_file> --time sec
  python trace_plotter.py <csv_file> --time ms

  # Filter to specific sections (partial name match, space-separated)
  python trace_plotter.py <csv_file> --sections Core_0 Core_1 Core_2 Core_3

  # Override which column to plot on Y axis
  python trace_plotter.py <csv_file> --y-col "Temperature (oC)"

  # Override plot style
  python trace_plotter.py <csv_file> --plot-type line

  # Save to file instead of opening a window
  python trace_plotter.py <csv_file> --output plot.png

  # List all registered event configs
  python trace_plotter.py --list
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd


# ─── Plot configuration model ──────────────────────────────────────────────────

@dataclass
class PlotConfig:
    """Describes how to render one SoCWatch event type."""

    # ---- what to plot ----
    y_cols:            list[str]     # column(s) to put on the Y axis

    # ---- time axis ----
    x_col:             str   = "Continuous Time (usec)"
    x_native_unit:     str   = "usec"   # unit stored in the CSV column
    default_time_unit: str   = "sec"    # preferred display unit

    # ---- chart style ----
    # "step"  – staircase; ideal for P-states / discrete events
    # "line"  – connected points; ideal for temperatures, bandwidth
    # "scatter" – individual marks; ideal for sparse event times
    plot_type:         str   = "step"
    step_where:        str   = "post"   # "pre" | "mid" | "post"
    alpha:             float = 0.85
    linewidth:         float = 1.2

    # ---- labels ----
    y_label:           str          = ""
    col_label_map:     dict[str, str] = field(default_factory=dict)  # col → axis label
    title:             str          = ""

    # ---- grouping ----
    group_by_section:  bool = True   # separate line/color per Section sub-unit
    overlay_threshold: int  = 6      # sections ≤ this → overlay; else subplots

    # ---- Y-axis hints ----
    y_ticks:           Optional[list] = None  # explicit tick locations
    y_lim:             Optional[tuple] = None  # (ymin, ymax)


# ─── Time-unit arithmetic ──────────────────────────────────────────────────────

_TO_USEC: dict[str, float] = {
    "usec": 1.0,
    "us":   1.0,
    "ms":   1_000.0,
    "msec": 1_000.0,
    "sec":  1_000_000.0,
    "s":    1_000_000.0,
}
_FROM_USEC: dict[str, float] = {k: 1.0 / v for k, v in _TO_USEC.items()}

TIME_UNIT_LABEL: dict[str, str] = {
    "usec": "µs", "us": "µs",
    "ms": "ms",   "msec": "ms",
    "sec": "s",   "s": "s",
}


def time_factor(native: str, target: str) -> float:
    """Multiplier to convert *native* units → *target* units."""
    return _TO_USEC.get(native, 1.0) * _FROM_USEC.get(target, 1.0)


# ─── Plot registry ─────────────────────────────────────────────────────────────
#
# Key   = base event-type name (text before the first " - " in the Section column)
# Value = PlotConfig
#
# Add/edit entries here to control how any event type is displayed.

PLOT_REGISTRY: dict[str, PlotConfig] = {

    # ── Memory ──────────────────────────────────────────────────────────────────
    "Memory Subsystem (MEMSS) P-State": PlotConfig(
        y_cols            = ["Frequency (MHz)"],
        x_col             = "Continuous Time (usec)",
        x_native_unit     = "usec",
        default_time_unit = "sec",
        plot_type         = "step",
        step_where        = "post",
        y_label           = "Frequency (MHz)",
        title             = "Memory Subsystem (MEMSS) P-State",
        group_by_section  = False,    # only one sub-unit: MEMSS
        y_ticks           = [594, 1188, 1584, 2112],
    ),

    # ── CPU / Core P-states ──────────────────────────────────────────────────────
    "Core P-State/Frequency (OS)": PlotConfig(
        y_cols            = ["Frequency(Mhz)"],   # note: no space in CSV column name
        x_col             = "Continuous Time (ms)",
        x_native_unit     = "ms",
        default_time_unit = "sec",
        plot_type         = "step",
        step_where        = "post",
        y_label           = "Frequency (MHz)",
        title             = "Core P-State / Frequency (OS)",
        group_by_section  = True,
        overlay_threshold = 4,
    ),

    "Thread P-State/Frequency (OS)": PlotConfig(
        y_cols            = ["Frequency(Mhz)"],
        x_col             = "Continuous Time (ms)",
        x_native_unit     = "ms",
        default_time_unit = "sec",
        plot_type         = "step",
        step_where        = "post",
        y_label           = "Frequency (MHz)",
        title             = "Thread P-State / Frequency (OS)",
        group_by_section  = True,
        overlay_threshold = 4,
    ),

    "Package P-State/Frequency (OS)": PlotConfig(
        y_cols            = ["Frequency(Mhz)"],
        x_col             = "Continuous Time (ms)",
        x_native_unit     = "ms",
        default_time_unit = "sec",
        plot_type         = "step",
        step_where        = "post",
        y_label           = "Frequency (MHz)",
        title             = "Package P-State / Frequency (OS)",
        group_by_section  = False,
    ),

    # CPU P-State: residency histogram per sample window – one value column per P-state
    # plotted as a weighted-average effective frequency (sum(freq×time) / total_time)
    "CPU P-State/Frequency": PlotConfig(
        y_cols            = [],       # resolved dynamically (all Pxx columns)
        x_col             = "Continuous Time (usec)",
        x_native_unit     = "usec",
        default_time_unit = "sec",
        plot_type         = "line",
        y_label           = "Residency (usec)",
        title             = "CPU P-State/Frequency Residency",
        group_by_section  = True,
        overlay_threshold = 2,
    ),

    # ── Display ──────────────────────────────────────────────────────────────────
    "Display P-State": PlotConfig(
        y_cols            = ["Frequency (MHz)"],
        x_col             = "Continuous Time (usec)",
        x_native_unit     = "usec",
        default_time_unit = "sec",
        plot_type         = "step",
        step_where        = "post",
        y_label           = "Frequency (MHz)",
        title             = "Display P-State Frequency",
        group_by_section  = False,
    ),

    "Media P-State": PlotConfig(
        y_cols            = ["Frequency (MHz)"],
        x_col             = "Continuous Time (usec)",
        x_native_unit     = "usec",
        default_time_unit = "sec",
        plot_type         = "step",
        step_where        = "post",
        y_label           = "Frequency (MHz)",
        title             = "Media P-State Frequency",
        group_by_section  = False,
    ),

    # ── C-States ─────────────────────────────────────────────────────────────────
    "Core C-State (OS)": PlotConfig(
        y_cols            = ["Duration (ms)"],
        x_col             = "Continuous Time (ms)",
        x_native_unit     = "ms",
        default_time_unit = "sec",
        plot_type         = "scatter",
        y_label           = "Duration (ms)",
        title             = "Core C-State (OS) Duration",
        group_by_section  = True,
        overlay_threshold = 4,
    ),

    "Thread C-State (OS)": PlotConfig(
        y_cols            = ["Duration (ms)"],
        x_col             = "Continuous Time (ms)",
        x_native_unit     = "ms",
        default_time_unit = "sec",
        plot_type         = "scatter",
        y_label           = "Duration (ms)",
        title             = "Thread C-State (OS) Duration",
        group_by_section  = True,
        overlay_threshold = 4,
    ),

    "Package C-State": PlotConfig(
        y_cols            = ["Duration (ms)"],
        x_col             = "Continuous Time (usec)",
        x_native_unit     = "usec",
        default_time_unit = "sec",
        plot_type         = "scatter",
        y_label           = "Duration (ms)",
        title             = "Package C-State Duration",
        group_by_section  = True,
        overlay_threshold = 4,
    ),

    # ── Temperature ──────────────────────────────────────────────────────────────
    "Temperature Metrics": PlotConfig(
        y_cols            = ["Temperature (oC)"],
        x_col             = "Continuous Time (usec)",
        x_native_unit     = "usec",
        default_time_unit = "sec",
        plot_type         = "line",
        y_label           = "Temperature (°C)",
        title             = "Temperature Metrics",
        group_by_section  = True,
        overlay_threshold = 8,
    ),

    # ── HWP ──────────────────────────────────────────────────────────────────────
    "HWP Capabilities": PlotConfig(
        y_cols            = [],       # resolved dynamically (numeric data column)
        x_col             = "Continuous Time (usec)",
        x_native_unit     = "usec",
        default_time_unit = "sec",
        plot_type         = "step",
        step_where        = "post",
        y_label           = "Value",
        title             = "HWP Capabilities",
        group_by_section  = True,
        overlay_threshold = 4,
    ),

    # ── Bandwidth events ─────────────────────────────────────────────────────────
    # DDR BW has a dedicated two-panel plot (totals line + per-subchannel scatter).
    # The '… : Instantaneous rate' sub-section is used (values already in MB/s).
    "DDR Bandwidth Requests by Component": PlotConfig(
        y_cols            = [],       # handled entirely by plot_ddr_bw
        x_col             = "Continuous Time (usec)",
        x_native_unit     = "usec",
        default_time_unit = "sec",
        plot_type         = "ddr_bw",  # routed to plot_ddr_bw()
        y_label           = "Bandwidth (GB/s)",
        title             = "DDR Bandwidth Requests by Component",
        group_by_section  = False,
    ),
}

# ─── Fallback for unregistered events ─────────────────────────────────────────
_DEFAULT_CONFIG = PlotConfig(
    y_cols            = [],
    x_col             = "Continuous Time (usec)",
    x_native_unit     = "usec",
    default_time_unit = "sec",
    plot_type         = "line",
    y_label           = "",
    title             = "",
    group_by_section  = True,
    overlay_threshold = 6,
)


# ─── Event-type detection ──────────────────────────────────────────────────────

def detect_event(df: pd.DataFrame) -> tuple[str, PlotConfig]:
    """Infer event type from the Section column; look it up in PLOT_REGISTRY."""
    if "Section" not in df.columns or df.empty:
        return ("Unknown", _DEFAULT_CONFIG)

    raw  = str(df["Section"].dropna().iloc[0])
    base = raw.split(" - ", 1)[0].strip()

    if base in PLOT_REGISTRY:
        return (base, PLOT_REGISTRY[base])

    # Substring / prefix fallback
    for key in PLOT_REGISTRY:
        if base.startswith(key) or key in base:
            return (base, PLOT_REGISTRY[key])

    return (base, _DEFAULT_CONFIG)


# ─── Column resolution ─────────────────────────────────────────────────────────

def resolve_y_cols(df: pd.DataFrame, cfg: PlotConfig) -> list[str]:
    """Return the actual column(s) to plot, verifying they exist in *df*."""
    skip = {"Section", "Sample #", cfg.x_col, "Duration (ms)", "Duration (usec)"}

    if cfg.y_cols:
        found = [c for c in cfg.y_cols if c in df.columns]
        if found:
            return found

    # Auto-detect: first numeric column that isn't the time or sample column
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    auto = [c for c in numeric if c not in skip and "Sample" not in c]
    return auto[:1] if auto else []


def resolve_x_col(df: pd.DataFrame, cfg: PlotConfig) -> tuple[str, str]:
    """
    Return (actual_x_col, actual_x_native_unit) by checking what time column
    exists in *df*. Handles the usec/ms ambiguity across event types.
    """
    if cfg.x_col in df.columns:
        return cfg.x_col, cfg.x_native_unit

    # Fallback: try the other common time columns
    for col, unit in [
        ("Continuous Time (usec)", "usec"),
        ("Continuous Time (ms)",   "ms"),
        ("Continuous Time (sec)",  "sec"),
    ]:
        if col in df.columns:
            return col, unit

    return cfg.x_col, cfg.x_native_unit   # will raise KeyError later with a clear message


# ─── Section helpers ───────────────────────────────────────────────────────────

def short_label(full: str) -> str:
    """'Event Name - CPU/Package_0/Core_3'  →  'Core_3'."""
    if " - " in full:
        sub = full.split(" - ", 1)[1].strip()
        return sub.split("/")[-1]
    return full


def filter_sections(df: pd.DataFrame, patterns: list[str]) -> pd.DataFrame:
    if not patterns:
        return df
    mask = df["Section"].str.contains("|".join(patterns), case=False, na=False)
    return df[mask]


# ─── Drawing helpers ──────────────────────────────────────────────────────────

# Color palette: tab10 + Set2 gives 18 distinct colours before cycling
_COLORS = list(plt.cm.tab10.colors) + list(plt.cm.Set2.colors)  # type: ignore[attr-defined]


def _draw(ax: plt.Axes, x: np.ndarray, y: np.ndarray,
          label: str, cfg: PlotConfig, color: str, pt: str) -> None:
    kw: dict = dict(label=label, color=color, alpha=cfg.alpha)
    if pt == "step":
        ax.step(x, y, where=cfg.step_where, linewidth=cfg.linewidth, **kw)
    elif pt == "scatter":
        ax.scatter(x, y, s=6, **kw)
    else:
        ax.plot(x, y, linewidth=cfg.linewidth, **kw)


def _style(ax: plt.Axes, cfg: PlotConfig,
           x_label: str, y_col: str, legend: bool) -> None:
    ax.set_xlabel(x_label, fontsize=9)
    y_lbl = cfg.col_label_map.get(y_col, cfg.y_label or y_col)
    ax.set_ylabel(y_lbl, fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(True, linestyle="--", alpha=0.30)
    if cfg.y_ticks is not None:
        ax.set_yticks(cfg.y_ticks)
        ax.set_yticklabels([str(v) for v in cfg.y_ticks], fontsize=8)
    if cfg.y_lim:
        ax.set_ylim(cfg.y_lim)
    if legend:
        ax.legend(fontsize=7, ncol=2, loc="upper left",
                  framealpha=0.55, borderpad=0.4)


# ─── Main plot function ────────────────────────────────────────────────────────

def plot_event(
    df:             pd.DataFrame,
    cfg:            PlotConfig,
    event_name:     str,
    time_unit:      str,
    y_cols:         list[str],
    plot_type:      str,
    section_filter: list[str],
    output:         Optional[Path],
) -> None:
    if section_filter:
        df = filter_sections(df, section_filter)
        if df.empty:
            print(f"No rows match section filter: {section_filter}", file=sys.stderr)
            return

    x_col, x_unit = resolve_x_col(df, cfg)
    tf      = time_factor(x_unit, time_unit)
    x_label = f"Time ({TIME_UNIT_LABEL.get(time_unit, time_unit)})"
    title   = cfg.title or event_name

    # Build (label, sub-df) groups
    if cfg.group_by_section and "Section" in df.columns:
        groups = [
            (short_label(sec), grp.reset_index(drop=True))
            for sec, grp in df.groupby("Section", sort=False)
        ]
    else:
        groups = [("", df.reset_index(drop=True))]

    n = len(groups)
    use_subplots = n > cfg.overlay_threshold

    for y_col in y_cols:
        if y_col not in df.columns:
            print(f"  Column '{y_col}' not found — skipping.", file=sys.stderr)
            continue

        full_title = f"{title}  —  {y_col}" if len(y_cols) > 1 else title

        # ---- layout --------------------------------------------------------
        if use_subplots:
            ncols = min(4, n)
            nrows = (n + ncols - 1) // ncols
            fig, axes = plt.subplots(
                nrows, ncols,
                figsize=(5 * ncols, 3.2 * nrows),
                sharey=True, sharex=True,
            )
            axes_flat: list[plt.Axes] = list(np.array(axes).flatten())
        else:
            fig, ax0 = plt.subplots(figsize=(14, 5))
            axes_flat = [ax0] * n

        fig.suptitle(full_title, fontsize=11, fontweight="bold", y=1.01)

        # ---- draw ----------------------------------------------------------
        for i, (lbl, grp) in enumerate(groups):
            ax    = axes_flat[i]
            color = _COLORS[i % len(_COLORS)]
            x     = grp[x_col].to_numpy(dtype=float) * tf
            y     = grp[y_col].to_numpy(dtype=float)

            _draw(ax, x, y, label=lbl, cfg=cfg, color=color, pt=plot_type)

            if use_subplots:
                ax.set_title(lbl, fontsize=8, pad=3)
                _style(ax, cfg, x_label, y_col, legend=False)

        if not use_subplots:
            _style(axes_flat[0], cfg, x_label, y_col, legend=(n > 1))

        # hide spare subplot cells
        if use_subplots:
            for j in range(n, len(axes_flat)):
                axes_flat[j].set_visible(False)

        fig.tight_layout()

        # ---- save / show ---------------------------------------------------
        if output:
            stem = output.stem + (f"_{y_col.replace(' ', '_')}" if len(y_cols) > 1 else "")
            out_path = output.with_stem(stem)
            fig.savefig(out_path, dpi=150, bbox_inches="tight")
            print(f"Saved: {out_path}")
        else:
            plt.show()


# ─── DDR Bandwidth plot ──────────────────────────────────────────────────────

_READS_PAT  = re.compile(r'-READS\s*\(bytes\)$',  re.IGNORECASE)
_WRITES_PAT = re.compile(r'-WRITES\s*\(bytes\)$', re.IGNORECASE)


def _subchannel_name(col: str) -> str:
    """'MC0-CH0-SUBCH1-READS (bytes)' → 'MC0-CH0-SUBCH1'."""
    return re.sub(r'[- ](READS|WRITES).*', '', col, flags=re.IGNORECASE).strip()


def plot_ddr_bw(
    df:             pd.DataFrame,
    cfg:            PlotConfig,
    event_name:     str,
    time_unit:      str,
    section_filter: list[str],
    output:         Optional[Path],
) -> None:
    """
    Two-panel DDR Bandwidth chart:
      Top    — line:    Total Read / Total Write / Total R+W  (GB/s)
      Bottom — scatter: each MCx-CHx-SUBCHx combined R+W     (GB/s)

    Uses the '… : Instantaneous rate' sub-section (values already in MB/s)
    so only a /1000 conversion is needed to reach GB/s.
    """
    # Prefer the instantaneous-rate rows (already MB/s — no byte-to-rate math needed)
    inst_mask = df["Section"].str.contains("Instantaneous rate", case=False, na=False)
    df_plot   = df[inst_mask].copy() if inst_mask.any() else df.copy()

    if section_filter:
        df_plot = filter_sections(df_plot, section_filter)
        if df_plot.empty:
            print(f"No rows match section filter: {section_filter}", file=sys.stderr)
            return

    x_col, x_unit = resolve_x_col(df_plot, cfg)
    tf      = time_factor(x_unit, time_unit)
    x_label = f"Time ({TIME_UNIT_LABEL.get(time_unit, time_unit)})"
    x       = df_plot[x_col].to_numpy(dtype=float) * tf

    # Identify READ / WRITE columns
    read_cols  = [c for c in df_plot.columns if _READS_PAT.search(c)]
    write_cols = [c for c in df_plot.columns if _WRITES_PAT.search(c)]

    if not read_cols and not write_cols:
        print("No READS/WRITES columns found in DDR BW CSV.", file=sys.stderr)
        return

    MB_TO_GB = 1.0 / 1000.0

    # ── Totals ───────────────────────────────────────────────────────────────
    total_r  = df_plot[read_cols].sum(axis=1).to_numpy(dtype=float)  * MB_TO_GB
    total_w  = df_plot[write_cols].sum(axis=1).to_numpy(dtype=float) * MB_TO_GB
    total_rw = total_r + total_w

    # ── Per sub-channel (MCx-CHx-SUBCHx): sum reads + writes ─────────────────
    all_cols       = read_cols + write_cols
    subchan_names  = sorted(set(_subchannel_name(c) for c in all_cols))
    subchan_bw: dict[str, np.ndarray] = {}
    for sc in subchan_names:
        cols = [c for c in all_cols if _subchannel_name(c) == sc]
        subchan_bw[sc] = df_plot[cols].sum(axis=1).to_numpy(dtype=float) * MB_TO_GB

    # ── Layout: 2 stacked subplots sharing X axis ─────────────────────────────
    fig, (ax_tot, ax_sub) = plt.subplots(
        2, 1, figsize=(14, 8), sharex=True,
        gridspec_kw={"height_ratios": [1.4, 1]},
    )
    fig.suptitle(cfg.title or event_name, fontsize=12, fontweight="bold")

    # ── Top: total read / write / combined (line) ────────────────────────────
    ax_tot.plot(x, total_r,  linewidth=1.8, color="#2196F3", label="Total Read")
    ax_tot.plot(x, total_w,  linewidth=1.8, color="#FF5722", label="Total Write")
    ax_tot.plot(x, total_rw, linewidth=2.2, color="#4CAF50", label="Total (R+W)",
                linestyle="--")
    ax_tot.set_ylabel("Bandwidth (GB/s)", fontsize=9)
    ax_tot.set_title("Total Read / Write / Combined", fontsize=9, pad=4)
    ax_tot.legend(fontsize=8, loc="upper left", framealpha=0.6, ncol=3)
    ax_tot.grid(True, linestyle="--", alpha=0.30)
    ax_tot.tick_params(labelsize=8)
    ax_tot.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v:.1f}")
    )

    # ── Bottom: per sub-channel R+W (scatter) ────────────────────────────────
    for i, (sc, bw) in enumerate(subchan_bw.items()):
        ax_sub.scatter(x, bw, s=8, color=_COLORS[i % len(_COLORS)],
                       label=sc, alpha=0.75)

    ax_sub.set_xlabel(x_label, fontsize=9)
    ax_sub.set_ylabel("Bandwidth (GB/s)", fontsize=9)
    ax_sub.set_title("Per Sub-Channel (R+W)", fontsize=9, pad=4)
    ax_sub.legend(fontsize=7, ncol=4, loc="upper left", framealpha=0.55)
    ax_sub.grid(True, linestyle="--", alpha=0.30)
    ax_sub.tick_params(labelsize=8)
    ax_sub.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v:.1f}")
    )

    fig.tight_layout()

    if output:
        fig.savefig(output, dpi=150, bbox_inches="tight")
        print(f"Saved: {output}")
    else:
        plt.show()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot SoCWatch event CSVs produced by trace_separator.py.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("csv", nargs="?", metavar="CSV_FILE",
                        help="Separated event CSV to plot")
    parser.add_argument("--time", dest="time_unit", default=None,
                        choices=list(_TO_USEC),
                        help="X-axis time unit (default: per-event config)")
    parser.add_argument("--sections", nargs="+", metavar="PATTERN",
                        help="Keep only sections whose name contains PATTERN "
                             "(space-separated, case-insensitive)")
    parser.add_argument("--plot-type", dest="plot_type", default=None,
                        choices=["step", "line", "scatter"],
                        help="Override the chart style")
    parser.add_argument("--y-col", dest="y_col", default=None,
                        help="Override which column to plot on the Y axis")
    parser.add_argument("--output", type=Path, default=None, metavar="FILE",
                        help="Save figure to file (png/pdf/svg) instead of "
                             "opening an interactive window")
    parser.add_argument("--list", action="store_true",
                        help="Print all registered event configs and exit")

    args = parser.parse_args()

    # ---- --list mode -------------------------------------------------------
    if args.list:
        name_w = max(len(k) for k in PLOT_REGISTRY) + 2
        print(f"\n{'Event Type':<{name_w}} {'Plot':>8}  {'Time':>5}  Y Column(s)")
        print("─" * (name_w + 50))
        for name, cfg in sorted(PLOT_REGISTRY.items()):
            y_str = ", ".join(cfg.y_cols) if cfg.y_cols else "(auto-detect)"
            print(f"{name:<{name_w}} {cfg.plot_type:>8}  {cfg.default_time_unit:>5}  {y_str}")
        return

    if not args.csv:
        parser.error("CSV_FILE is required (or use --list).")

    src = Path(args.csv)
    if not src.exists():
        parser.error(f"File not found: {src}")

    # ---- load --------------------------------------------------------------
    print(f"Loading {src.name} …")
    df = pd.read_csv(src)
    df.columns = df.columns.str.strip()
    print(f"  {len(df):,} rows   columns: {list(df.columns)}")

    # ---- detect / resolve --------------------------------------------------
    event_name, cfg = detect_event(df)
    print(f"  Event type   : {event_name}")

    time_unit = args.time_unit or cfg.default_time_unit
    plot_type = args.plot_type or cfg.plot_type
    y_cols    = [args.y_col] if args.y_col else resolve_y_cols(df, cfg)

    if not y_cols and plot_type != "ddr_bw":
        parser.error(
            "Could not determine which column to plot. "
            "Use --y-col to specify one explicitly.\n"
            f"Available columns: {list(df.columns)}"
        )

    print(f"  Y column(s)  : {y_cols}")
    print(f"  Time unit    : {time_unit}")
    print(f"  Plot type    : {plot_type}")
    if args.sections:
        print(f"  Section filter: {args.sections}")

    # When saving to a file we don't need a display; switch to the non-interactive
    # Agg backend before pyplot creates any figure objects.
    if args.output:
        matplotlib.use("Agg")
    else:
        # Try to get an interactive window; fall back gracefully if no display is
        # available (e.g. headless CI / SSH session without X forwarding).
        try:
            matplotlib.use("TkAgg")
            import tkinter  # noqa: F401 — triggers ImportError early if Tk missing
        except (ImportError, Exception):
            print("  Note: Tkinter not available — switching to Qt5Agg backend.")
            try:
                matplotlib.use("Qt5Agg")
            except Exception:
                matplotlib.use("Agg")
                print("  Warning: No interactive backend found. Use --output to save the chart.")

    if cfg.plot_type == "ddr_bw":
        plot_ddr_bw(
            df             = df,
            cfg            = cfg,
            event_name     = event_name,
            time_unit      = time_unit,
            section_filter = args.sections or [],
            output         = args.output,
        )
    else:
        plot_event(
            df             = df,
            cfg            = cfg,
            event_name     = event_name,
            time_unit      = time_unit,
            y_cols         = y_cols,
            plot_type      = plot_type,
            section_filter = args.sections or [],
            output         = args.output,
        )


if __name__ == "__main__":
    main()
