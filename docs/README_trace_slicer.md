# Power Trace Slicer

A tool to slice power trace CSV files by selecting specific power rails and time ranges.

## Features

- **Interactive file selection** with GUI dialog (no trace file argument needed)
- Extract specific power rails from large trace files
- Support multiple time ranges in a single run
- Automatically calculate **average** and **peak** power for each sliced range
- Sequential output file numbering with descriptive names
- Configuration via JSON file or command-line arguments
- Remembers last opened directory for convenience

## Usage

### Interactive Mode (GUI File Selection)

Simply run without a trace file argument to open a file selection dialog:

```bash
python trace_power_slicer.py --config config_example.json
```

Or with command-line arguments:

```bash
python trace_power_slicer.py --rails P_CPU P_SOC --time-ranges "0:10" "20:40"
```

### Using Configuration File

```bash
python trace_power_slicer.py test/Geekbench6_003_pacs-traces-100sr.csv --config config_example.json
```

### Using Command-Line Arguments

```bash
python trace_power_slicer.py test/Geekbench6_003_pacs-traces-100sr.csv \
    --rails P_VCCCORE P_VCCGT P_Memory \
    --time-ranges "0:10" "20:40" "50:70" \
    --output-dir ./my_sliced_output
```

## Input File Format

- CSV file with `-NNNsr.csv` suffix (NNN = sample rate in samples per second)
- First column: timestamp in seconds (e.g., 0.00, 0.01, 0.02...)
- Other columns: power rails in watts
- **Note:** Time values are automatically converted to milliseconds when loaded

Example: `Geekbench6_003_pacs-traces-100sr.csv`
- 100sr = 100 samples per second (one sample every 0.01 seconds = 10 milliseconds)

## Output Format

Files are named with format: `NNN_basename_startms_endms.csv` (time in milliseconds)

Examples:
- `000_Geekbench6_003_pacs-traces_0ms_10000ms.csv` (0-10 seconds)
- `001_Geekbench6_003_pacs-traces_20000ms_40000ms.csv` (20-40 seconds)
- `002_Geekbench6_003_pacs-traces_50000ms_70000ms.csv` (50-70 seconds)

Each output file contains:
- A header row at the top (for easy identification in data viewers)
- An "Average" row with mean values for each power rail
- A "Peak" row with maximum values for each power rail
- Another header row (separator before data)
- Followed by selected power rail columns with data within the specified time range

## Configuration File Format

```json
{
  "power_rails": [
    "P_VCCCORE",
    "P_VCCGT",
    "P_Memory"
  ],
  "time_ranges": [
    [0, 10000],
    [20000, 40000]
  ]
}
```

**Note:** Time ranges are in milliseconds (e.g., 10000 = 10 seconds).

## Command-Line Options

- `trace_file`: Path to the input trace CSV file (optional - if not provided, opens GUI file dialog)
- `--config`, `-c`: Path to JSON configuration file
- `--rails`, `-r`: Space-separated list of power rail names
- `--time-ranges`, `-t`: Time ranges in "start:end" format (in **milliseconds**)
- `--output-dir`, `-o`: Output directory (default: `./sliced_output`)

## Examples

### Example 1: Interactive mode with config file

```bash
python trace_power_slicer.py -c config_example.json
```
*Opens file dialog, then uses config file for rails and time ranges*

### Example 2: Interactive mode with command-line parameters

```bash
python trace_power_slicer.py --rails P_CPU P_SOC --time-ranges "0:50000"
```
*Opens file dialog, then uses specified rails and time range (0 to 50000 milliseconds = 0 to 50 seconds)*

### Example 3: Extract specific rails with config

```bash
python trace_power_slicer.py test/Geekbench6_003_pacs-traces-100sr.csv -c config_example.json
```

### Example 4: Single time slice

```bash
python trace_power_slicer.py test/Geekbench6_003_pacs-traces-100sr.csv \
    --rails P_CPU P_SOC \
    --time-ranges "10000:50000"
```
*Slices from 10000 to 50000 milliseconds (10 to 50 seconds)*

### Example 5: Multiple time slices

```bash
python trace_power_slicer.py test/Geekbench6_003_pacs-traces-100sr.csv \
    --rails P_VCCCORE P_Memory P_CPU \
    --time-ranges "0:30000" "40000:70000" "80000:110000"
```
*Creates 3 slices: 0-30s, 40-70s, and 80-110s (specified in milliseconds)*

## Requirements

- Python 3.6+
- pandas

Install dependencies:
```bash
pip install pandas
```
