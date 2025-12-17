# Phi_summary - Microsoft Phi-Silica SLM Workload Analysis

Specialized parser for analyzing Microsoft Phi-Silica Small Language Model (SLM) workloads with integrated Power, ETL, and performance metrics.

## Overview

Phi_summary is designed for workload analysis specific to Microsoft Phi-Silica SLM deployments. It aggregates power consumption data, model throughput metrics, ETL results, and Socwatch performance monitoring into a comprehensive Excel report.

## Purpose

Analyze Microsoft Phi-Silica SLM inference performance with:
- Power consumption metrics
- Model throughput and latency
- ETL (Early Termination Layer) data
- Socwatch performance monitoring
- Thermal characteristics
- Bandwidth utilization

## Features

- **Multi-source Integration**: Combines Power, ETL, Model throughput, and Socwatch
- **Recursive Detection**: Automatically discovers all files in input directory tree
- **Batch Processing**: Handles multiple Phi model runs efficiently
- **Comprehensive Metrics**: Power, performance, thermal, and bandwidth analysis
- **Excel Output**: Professional multi-sheet reports
- **Last Folder Memory**: Remembers last used folder for convenience

## Usage

```bash
python Phi_summary.py -i <input_path> -o <output_path> [options]
```

### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `-i, --input` | Input directory path (will search recursively) | `\\server\data\phi_models\` |

### Optional Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-o, --output` | Output Excel file location | Auto-generated in input directory |
| `-d, --daq` | DAQ power rail configuration (JSON) | Built-in defaults |
| `-st, --swtarget` | Socwatch target table definitions (JSON) | Built-in defaults |

## Examples

### Basic Usage

```bash
# Analyze Phi model data with default settings
python Phi_summary.py -i \\server\data\phi_experiments\
```

### With Output Specification

```bash
# Specify output location and filename
python Phi_summary.py -i \\server\data\phi_experiments\ -o \\server\results\phi_analysis.xlsx
```

### With Custom DAQ Configuration

```bash
# Use custom power rail definitions
python Phi_summary.py -i \\server\data\phi_experiments\ -d .\config\daq_phi.json -st .\config\socwatch_targets.json
```

### With HOBL Data

```bash
# Process data collected via HOBL with .PASS/.FAIL markers
python Phi_summary.py -i \\server\data\hobl_collection\ -hb
```

## Input Data Structure

### Expected File Types

Phi_summary automatically detects and processes:
- **Power Files**: Power summary CSV/Excel files
- **ETL Data**: ETL results and metrics
- **Model Output**: Throughput and latency data
- **Socwatch Summary**: Performance monitoring data

### Folder Organization

```
phi_experiments/
├── phi_model_v1/
│   ├── power_data.csv
│   ├── model_output.txt
│   ├── etl_results.csv
│   └── socwatch_summary.csv
├── phi_model_v2/
│   ├── power_data.csv
│   ├── model_output.txt
│   └── socwatch_summary.csv
└── phi_model_v3/
    ├── power_data.csv
    └── model_output.txt
```

## Output Format

### Excel Workbook Structure

The generated Excel file contains:

1. **Summary Sheet**
   - Overview of all Phi model runs
   - Aggregate metrics and statistics
   - Performance rankings

2. **Power Analysis**
   - Power consumption by model
   - Power rails breakdown
   - Energy per inference

3. **Model Performance**
   - Throughput metrics
   - Latency analysis
   - Performance scaling

4. **ETL Data**
   - Early Termination Layer results
   - Inference optimization metrics

5. **Socwatch Metrics**
   - Performance monitoring data
   - C-state/P-state analysis
   - CPU utilization
   - Thermal data

6. **Thermal Analysis**
   - Temperature profiles
   - Thermal efficiency
   - Hotspot identification

7. **Bandwidth Analysis**
   - Memory bandwidth utilization
   - I/O bandwidth metrics
   - System bandwidth correlations

## Configuration

### DAQ Power Rail Configuration (-d, --daq)

Customize power rails to track:

```json
{
  "P_SSD": -1,
  "V_VAL_VCC_PCORE": -1,
  "I_VAL_VCC_PCORE": -1,
  "P_VCC_PCORE": -1,
  "P_VCC_ECORE": -1,
  "P_VCCSA": -1,
  "P_VCCGT": -1,
  "P_SOC+MEMORY": -1,
  "Run Time": -1
}
```

**Notes:**
- Value of `-1` means auto-detect column
- Add "Run Time" to calculate total energy (Joules)
- Customize based on your DAQ naming conventions

### Socwatch Target Configuration (-st, --swtarget)

Define which Socwatch metrics to extract:

```json
[
  {"key": "CPU_model", "lookup": "CPU native model"},
  {"key": "CPU_Pstate", "lookup": "CPU P-State/Frequency Summary: Residency (Percentage and Time)"},
  {"key": "Core_Cstate", "lookup": "Core C-State Summary: Residency (Percentage and Time)"},
  {"key": "CPU_temp", "lookup": "Temperature Metrics Summary - Sampled: Min/Max/Avg"},
  {"key": "DDR_BW", "lookup": "DDR Bandwidth Requests by Component Summary: Average Rate and Total"}
]
```

**Note:** Order should match Socwatch output for optimal performance.

## Workflow

### Step 1: Prepare Data

Organize Phi model results in a folder with consistent structure:
```
experiments/
├── run_001/
├── run_002/
└── run_003/
```

### Step 2: Run Phi_summary

```bash
python Phi_summary.py -i .\experiments\ -o .\results\phi_analysis.xlsx
```

### Step 3: Review Results

Open the generated Excel file to analyze:
- Power efficiency
- Model performance
- Scaling characteristics
- Thermal profiles

### Step 4: Iterate

Modify configuration if needed and re-run analysis.

## Key Metrics

### Power Analysis
- **Average Power**: Mean power consumption during inference
- **Peak Power**: Maximum power during test
- **Energy per Inference**: Total energy divided by inference count
- **Power Efficiency**: Performance per watt

### Performance Metrics
- **Throughput**: Inferences per second
- **Latency**: Time per inference
- **Speedup**: Relative performance improvement
- **Scaling Efficiency**: Multi-core scaling effectiveness

### Thermal Metrics
- **Peak Temperature**: Maximum die temperature
- **Average Temperature**: Mean temperature during test
- **Thermal Headroom**: Distance from thermal limits
- **Throttling Events**: Number of thermal throttle instances

## HOBL Data Support

When data is collected via HOBL (Hardware On-Board Logger):

```bash
python Phi_summary.py -i \\hobl_data\ -hb
```

**Features:**
- Automatic .PASS/.FAIL file detection
- Data grouping by pass/fail status
- Improved data integrity validation
- Better error tracking

## Troubleshooting

### Issue: No data found

**Solution:**
- Verify input path and spelling
- Check files match expected naming patterns
- Ensure recursive folder search completes
- Check file permissions

### Issue: Memory errors with large datasets

**Solution:**
- Process data in smaller batches
- Split into multiple runs
- Reduce number of concurrent files
- Increase available system RAM

### Issue: Incorrect power rail values

**Solution:**
- Create custom DAQ configuration file
- Specify exact column names with `-d` flag
- Verify power file format and naming
- Check DAQ naming conventions

### Issue: Missing Socwatch metrics

**Solution:**
- Create custom Socwatch target file with `-st` flag
- Verify metric names match Socwatch output
- Check Socwatch version compatibility
- Ensure metrics exist in input data

## Performance Tips

1. **Match Socwatch Order**: Arrange targets in same order as Socwatch file for faster parsing
2. **Batch Processing**: Group multiple models in single input directory
3. **Memory Efficiency**: Process large datasets in chunks
4. **Data Cleanup**: Remove unnecessary files from input directory

## Related Parsers

- [ParseAll](./parseall.md) - Multi-source aggregation
- [Collection_Parser](./collection-parser.md) - Collection-based analysis
- [Llama Parser](./llama-parser.md) - Llama model analysis

---

[Back to main README](../README.md)
