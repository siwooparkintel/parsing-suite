# Collection_Parser - Collection-Based Collateral Generation

Advanced parser for generating detailed platform collateral from pre-selected data collections.

## Overview

Collection_Parser is designed for generating publication-quality collateral after data selection. It combines Power, Socwatch, and PCIe-only Socwatch data with per-core CPU P-state visualization.

## Use Cases

Collection_Parser is used **after** data selection via ParseAll:

1. Review aggregated data from ParseAll
2. Identify specific Power, Socwatch, and PCIe files
3. Create collection configuration JSON
4. Run Collection_Parser for detailed analysis

## Features

- **Multi-Source Combination**: Integrates Power, Socwatch, and PCIe metrics
- **Per-Core P-State Analysis**: CPU P-states presented on a per-core basis
- **Collapsible Visualization**: Hide secondary cores to highlight key data
- **Flexible Input**: JSON configuration file or interactive file dialog
- **Compact/Expanded Modes**: Choose data visualization style
- **Projection-Ready**: Structured for stakeholder review
- **High-Resolution Output**: Excel files with professional formatting

## Usage

```bash
python Collection_Parser.py [-c <platform.config>] [-i <collection.json>] [-o <output_path>] [options]
```

### Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-c, --config` | Platform config file (JSON). Sets socwatch/PCIe/DAQ targets and second folder list | `config/LNL_default.config` |
| `-i, --input` | Collection JSON file listing datasets to parse. If omitted, a file dialog opens for interactive selection | File dialog |
| `-o, --output` | Output Excel file prefix. If omitted, writes to system temp dir and auto-copies result to the input JSON's parent folder | Auto (temp + copy) |
| `-d, --daq` | DAQ power rail config (JSON). Overrides value from `-c` config | From `-c` config |
| `-st, --swtarget` | Socwatch targets (JSON). Overrides value from `-c` config | From `-c` config |

## Examples

### Using JSON Configuration File

```bash
python Collection_Parser.py -i .\config\collection.json -o .\results\collateral
```

### Using File Dialog (Interactive Selection)

Omit `-i` to open a file picker and select the collection JSON:

```bash
python Collection_Parser.py -o .\results\collateral
```

### Auto Output Path (No `-o`)

Omit `-o` to write the result automatically to the same folder as the input JSON:

```bash
python Collection_Parser.py -i .\config\collection.json
# Output: <collection.json parent folder>\collection_summary_collection.xlsx
```

### With Custom Platform Config

```bash
python Collection_Parser.py -c .\config\PTL_default.config -i collection.json -o .\results\collateral
```

### With Override DAQ and Socwatch Configs

```bash
python Collection_Parser.py -i config.json -d .\daq_targets.json -st .\socwatch_targets.json
```

## Configuration Format

### JSON Configuration File

```json
[
    {
        "data_label": "Baseline Configuration",
        "condition": "CataV3+Baseline",
        "data_summary_type": "compact",
        "power_summary_path": "\\server\data\power_baseline.xlsx",
        "socwatch_summary_path": "\\server\data\socwatch_baseline.xlsx",
        "PCIe_socwatch_summary_path": "\\server\data\pcie_baseline.xlsx"
    },
    {
        "data_label": "Optimized Configuration",
        "condition": "CataV3+Optimized",
        "data_summary_type": "expanded",
        "power_summary_path": "\\server\data\power_optimized.xlsx",
        "socwatch_summary_path": "\\server\data\socwatch_optimized.xlsx",
        "PCIe_socwatch_summary_path": "\\server\data\pcie_optimized.xlsx"
    }
]
```

### Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data_label` | String | Yes | Unique identifier for this dataset |
| `condition` | String | Yes | Display name for collateral |
| `data_summary_type` | String | Yes | `"compact"` or `"expanded"` |
| `power_summary_path` | String | No | Path to DAQ power summary CSV |
| `socwatch_summary_path` | String | No | Path to Socwatch summary file |
| `PCIe_socwatch_summary_path` | String | No | Path to PCIe-only Socwatch summary |
| `trace_path` | String | No | Path to DAQ power trace CSV (for per-sample trace data) |

### Data Summary Types

**compact**: 
- 2nd to last core P-states hidden by default
- Baseline and latest progression emphasized
- Cleaner visual presentation
- Easier to highlight differences

**expanded**:
- All CPU cores visible
- Detailed per-core analysis
- Complete performance picture
- Comprehensive documentation

## Output

The output is a single Excel workbook named `<prefix>_collection.xlsx`. When `-o` is omitted, the file is written to the system temp directory first and then automatically copied alongside the input collection JSON.

## Workflow

### Step 1: Data Selection with ParseAll

```bash
python ParseAll.py -i \\data\location\ -o .\results\aggregated.xlsx
```

### Step 2: Review and Identify Datasets

Open generated Excel file and identify:
- Power, Socwatch, and PCIe summary files
- Data quality and completeness
- Configurations for comparison

### Step 3: Create Collection JSON

```json
[
    {
        "data_label": "Config A",
        "condition": "Baseline",
        "data_summary_type": "compact",
        "power_summary_path": "...",
        "socwatch_summary_path": "...",
        "PCIe_socwatch_summary_path": "..."
    }
]
```

### Step 4: Run Collection_Parser

```bash
# Provide input and output explicitly
python Collection_Parser.py -i config.json -o collateral

# Omit -i to pick the JSON via file dialog
python Collection_Parser.py -o collateral

# Omit -o to auto-write result next to the input JSON
python Collection_Parser.py -i config.json
```

### Step 5: Review Collateral

Open generated Excel to verify:
- Data completeness
- Visual presentation
- Per-core analysis accuracy

## Output Format

### Excel Workbook Structure

| Sheet | Content |
|-------|---------|
| **Summary** | Dataset comparison overview |
| **Power Analysis** | Power metrics by configuration |
| **Per-Core P-States** | CPU P-state data (compact/expanded) |
| **Socwatch Metrics** | Performance monitoring data |
| **PCIe Analysis** | PCIe bandwidth metrics (if provided) |
| **Comparison** | Side-by-side metrics |
| **Metadata** | File sources and timestamps |

## Platform Config File (`-c, --config`)

The platform config file (`.config` or `.json`) centralises settings that are independent of the collection being analysed. It is loaded once at startup and can be overridden per-run with `-d` or `-st`.

Default: `config/LNL_default.config` (relative to the script directory).

### Keys used from the config

| Key | Description |
|-----|-------------|
| `socwatch_targets` | List of Socwatch metric definitions (same format as `-st`) |
| `PCIe_targets` | List of PCIe metric definitions |
| `DAQ_target` | DAQ power rail name dictionary (same format as `-d`) |
| `Second_folder_list` | Additional folder paths scanned for supplementary data |

---



## Configuration Details

### DAQ Power Rail Configuration (`-d, --daq`)

```json
{
  "P_SSD": -1,
  "P_VCC_PCORE": -1,
  "P_VCC_ECORE": -1,
  "P_VCCSA": -1,
  "P_VCCGT": -1,
  "P_VCCL2": -1,
  "P_SOC+MEMORY": -1,
  "Run Time": -1
}
```

### Socwatch Targets Configuration (`-st, --swtarget`)

```json
[
  {
    "key": "CPU_Pstate",
    "lookup": "CPU P-State/Frequency Summary: Residency (Percentage and Time)",
    "buckets": ["0", "400", "401-1799", "1800-2049", "2050"]
  },
  {
    "key": "Core_Cstate",
    "lookup": "Core C-State Summary: Residency (Percentage and Time)"
  },
  {
    "key": "DDR_BW",
    "lookup": "DDR Bandwidth Requests by Component Summary: Average Rate and Total"
  }
]
```

## CPU P-State Visualization

### Compact Mode (Default)

```
Dataset: Baseline
  Core_0:  P-state distribution
  Core_1:  P-state distribution
  [Core_2 to Core_N-1 hidden by default]
  Core_N:  P-state distribution
```

Users can expand hidden rows in Excel to see all cores.

### Expanded Mode

All CPU cores displayed individually with complete P-state information.

## Best Practices

1. **Organization**: Group related configurations together in JSON
2. **Naming**: Use clear, descriptive `data_label` values
3. **Paths**: Use raw strings (`r"..."`) in Python to avoid escaping issues
4. **Uniqueness**: Ensure `data_label` is unique per dataset
5. **Validation**: Verify file paths before running
6. **Documentation**: Include conditions/configurations in `condition` field

## Troubleshooting

### Issue: File Not Found

**Solution:**
- Verify all file paths exist and are accessible
- Check for typos in path names
- Use absolute paths for network files
- Test path accessibility separately

### Issue: Invalid JSON Format

**Solution:**
- Validate JSON using online tools
- Check quotes and commas
- Ensure proper array/object structure
- Use Python JSON validator

### Issue: Data Mismatch Errors

**Solution:**
- Verify Power, Socwatch, and PCIe files are from same run
- Check data consistency and alignment
- Review file timestamps
- Ensure compatible file formats

### Issue: Memory Errors

**Solution:**
- Process fewer datasets per run
- Split large comparisons into multiple jobs
- Reduce data complexity
- Close other applications

### Issue: Incorrect P-State Display

**Solution:**
- Verify Socwatch P-state metric names
- Check bucketing configuration matches data
- Validate Socwatch target definitions
- Test with single dataset first

## Performance Tips

1. **Pre-validation**: Verify all file paths exist before running
2. **Batch Processing**: Group related comparisons
3. **Memory Efficiency**: Process datasets in manageable sets
4. **Caching**: Reuse configurations for similar analyses

## Related Tools

- [ParseAll](./parseall.md) - Initial data aggregation
- [CatapultV3_Full_Parser](./catapultv3-full-parser.md) - Full platform analysis
- [Phi_summary](./phi-summary.md) - Phi model-specific analysis

---

[Back to main README](../README.md)
