# SWJSON Parser - Usage Guide

The upgraded `swjson_parser.py` can now analyze and visualize **any event type** from .swjson files, not just DDR bandwidth.

## Features

- ✅ Analyze multiple event types in a single run
- ✅ Generate charts for any event (NPU, GPU, CPU, Memory, etc.)
- ✅ Smart unit conversion (MB/s, MHz, W, °C, etc.)
- ✅ Command-line interface with multiple options
- ✅ List all available events in a file

## Basic Usage

### 1. List all available events in a file
```bash
python swjson_parser.py -i "path/to/file.swjson" --list-events
```

### 2. Analyze specific events
```bash
# Single event
python swjson_parser.py -i "path/to/file.swjson" -e "Neural Processing Unit (NPU) Power"

# Multiple events
python swjson_parser.py -i "path/to/file.swjson" -e "Neural Processing Unit (NPU) Power" "Neural Processing Unit (NPU) P-State" "Integrated Graphics P-State/Frequency"
```

### 3. Analyze all events (default)
```bash
python swjson_parser.py -i "path/to/file.swjson"
```

### 4. Specify output location
```bash
python swjson_parser.py -i "path/to/file.swjson" -o "C:\output\my_analysis"
```

### 5. Use file picker dialog (no -i parameter)
```bash
python swjson_parser.py
```

## Examples

### Example 1: Analyze NPU metrics
```bash
python swjson_parser.py -i "test/swjson_samples_upto5.json" -e "Neural Processing Unit (NPU) Power" "Neural Processing Unit (NPU) P-State" "Neural Processing Unit (NPU) Voltage"
```

Output:
- `test/swjson_samples_upto5_analysis_Neural_Processing_Unit_NPU_Power_summary.json`
- `test/swjson_samples_upto5_analysis_Neural_Processing_Unit_NPU_Power_chart.png`
- Similar files for P-State and Voltage

### Example 2: Analyze GPU and Memory
```bash
python swjson_parser.py -i "test/swjson_samples_upto5.json" -e "Integrated Graphics P-State/Frequency" "DDR Bandwidth Requests by Component" "Neural Processing Unit (NPU) to Memory Bandwidth"
```

### Example 3: List and pick events
```bash
# First, list all events
python swjson_parser.py -i "test/swjson_samples_upto5.json" --list-events

# Then run with desired events
python swjson_parser.py -i "test/swjson_samples_upto5.json" -e "CPU P-State/Frequency" "Temperature Metrics"
```

## Output Files

For each analyzed event, the parser generates:

1. **Summary JSON**: Contains metrics like total events, peak value, duration, accumulated values
2. **Chart PNG**: Scatter plot showing the metric over time with appropriate units

File naming pattern:
- `{input_name}_analysis_{Event_Name}_summary.json`
- `{input_name}_analysis_{Event_Name}_chart.png`

## Supported Event Types

The parser handles 50+ event types including:

- **NPU**: Power, P-State, Voltage, D-State, Bandwidth
- **GPU**: Integrated Graphics P-State/Frequency, Power, Voltage, Temperature, C-State
- **CPU**: P-State/Frequency, C-State, Temperature, Power
- **Memory**: DDR Bandwidth, IO Bandwidth, Various NoC Bandwidths
- **System**: Package C-State, Platform Monitoring, SoC Temperatures
- And many more...

## Smart Features

### Automatic Unit Conversion
- Bandwidth values: Converts to MB/s if >= 1MB
- Frequency: Displays in MHz
- Power: Displays in Watts
- Temperature: Displays in °C
- Voltage: Displays in Volts

### Intelligent Y-Axis Labels
The chart automatically determines the appropriate Y-axis label based on the event type:
- "Bandwidth (MB/s)" for bandwidth events
- "Frequency (MHz)" for frequency events
- "Power (W)" for power events
- "Temperature (°C)" for temperature events
- etc.

## Tips

1. **Use quotes** for event names with spaces:
   ```bash
   -e "Neural Processing Unit (NPU) Power"
   ```

2. **Tab completion**: Event names are case-sensitive and must match exactly

3. **Batch analysis**: Omit the `-e` parameter to analyze all events at once

4. **Performance**: Analyzing 50+ events may take a few seconds, be patient

## Requirements

- Python 3.7+
- matplotlib
- parsers.tools module (from parsing-suite)

Install matplotlib:
```bash
py -3.13 -m pip install matplotlib
```
