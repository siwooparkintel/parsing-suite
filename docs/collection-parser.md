# Collection_Parser - Collection-Based Collateral Generation

Advanced parser for generating detailed platform collateral from pre-selected data collections.

## Overview

Collection_Parser is designed for generating publication-quality collateral after data selection. It combines Power, Socwatch, and PCIe-only Socwatch data with per-core CPU P-state visualization.

## Use Cases

Collection_Parser is used **after** data selection via ParseAll:

1. Review aggregated data from ParseAll
2. Identify specific Power, Socwatch, and PCIe files
3. Create collection configuration (JSON or inline)
4. Run Collection_Parser for detailed analysis

## Features

- **Multi-Source Combination**: Integrates Power, Socwatch, and PCIe metrics
- **Per-Core P-State Analysis**: CPU P-states presented on a per-core basis
- **Collapsible Visualization**: Hide secondary cores to highlight key data
- **Flexible Input**: JSON configuration or Python hardcoded
- **Compact/Expanded Modes**: Choose data visualization style
- **Projection-Ready**: Structured for stakeholder review
- **High-Resolution Output**: Excel files with professional formatting

## Usage

```bash
python Collection_Parser.py -i <config.json> -o <output_path> [options]
```

### Required Arguments

| Argument | Description |
|----------|-------------|
| `-i, --input` | JSON config file OR omit to use hardcoded collection |

### Optional Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-o, --output` | Output Excel file prefix | Generated from config |
| `-d, --daq` | DAQ power rail config (JSON) | Built-in defaults |
| `-st, --swtarget` | Socwatch targets (JSON) | Built-in defaults |

## Examples

### Using JSON Configuration File

```bash
python Collection_Parser.py -i .\config\collection.json -o .\results\collateral
```

### Using Hardcoded Configuration

```bash
# Edit Collection_Parser.py, then run:
python Collection_Parser.py -o .\results\collateral
```

### With Custom DAQ and Socwatch Configs

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
| `data_summary_type` | String | Yes | "compact" or "expanded" |
| `power_summary_path` | String | Yes | Path to Power summary file |
| `socwatch_summary_path` | String | Yes | Path to Socwatch summary file |
| `PCIe_socwatch_summary_path` | String | No | Path to PCIe Socwatch (optional) |

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

## Python Hardcoded Configuration

Edit directly in Collection_Parser.py:

```python
collection = [
    {
        "data_label": "CataV3 UHX1",
        "condition": "CataV3+UHX1",
        "data_summary_type": "compact",
        "power_summary_path": r"\\server\data\power\UHX1_power.xlsx",
        "socwatch_summary_path": r"\\server\data\socwatch\UHX1_socwatch.xlsx",
        "PCIe_socwatch_summary_path": r"\\server\data\pcie\UHX1_pcie.xlsx"
    },
    {
        "data_label": "CataV3 UHX1 LC",
        "condition": "CataV3+UHX1+LC",
        "data_summary_type": "compact",
        "power_summary_path": r"\\server\data\power\UHX1_LC_power.xlsx",
        "socwatch_summary_path": r"\\server\data\socwatch\UHX1_LC_socwatch.xlsx",
        "PCIe_socwatch_summary_path": r"\\server\data\pcie\UHX1_LC_pcie.xlsx"
    },
    {
        "data_label": "CataV3 UHX2",
        "condition": "CataV3+UHX2",
        "data_summary_type": "expanded",
        "power_summary_path": r"\\server\data\power\UHX2_power.xlsx",
        "socwatch_summary_path": r"\\server\data\socwatch\UHX2_socwatch.xlsx"
    }
]
```

**Advantages of hardcoding:**
- Avoids Windows path escape issues using `r` prefix
- Easier parametrization for repeated runs
- Version control friendly
- No separate configuration file needed

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

### Step 3: Create Configuration

Option A - JSON File:
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

Option B - Python Hardcoded:
Edit Collection_Parser.py directly with file paths

### Step 4: Run Collection_Parser

```bash
# Using JSON
python Collection_Parser.py -i config.json -o collateral.xlsx

# Using hardcoded (after editing file)
python Collection_Parser.py -o collateral.xlsx
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

## Configuration Details

### DAQ Power Rail Configuration (-d, --daq)

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

### Socwatch Targets Configuration (-st, --swtarget)

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
