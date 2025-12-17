# bm_llama_parser - Llama Model Workload Analysis

Specialized parser for analyzing Llama language model inference performance with integrated metrics.

## Overview

The Llama parser is designed for analyzing Llama model inference workloads, aggregating performance, power, thermal, and resource utilization metrics into comprehensive reports.

## Purpose

Analyze Llama model deployments with:
- Model inference performance (throughput, latency)
- Power consumption analysis
- Token generation metrics
- Memory bandwidth utilization
- Thermal characteristics
- Scaling efficiency

## Features

- **Model-Specific Metrics**: Llama-optimized performance analysis
- **Token-Level Analysis**: Tokens per second, latency per token
- **Memory Efficiency**: Memory bandwidth and capacity analysis
- **Thermal Monitoring**: Temperature profiles during inference
- **Batch Processing**: Handle multiple model sizes and batch sizes
- **Comparative Analysis**: Compare different model configurations
- **Excel Output**: Professional formatted reports

## Usage

```bash
python bm_llama_parser.py -i <input_path> -o <output_path> [options]
```

### Basic Example

```bash
python bm_llama_parser.py -i \\server\data\llama_runs\ -o .\results\llama_analysis.xlsx
```

## Supported Model Sizes

- Llama 7B
- Llama 13B
- Llama 30B
- Llama 65B
- Llama 70B (2nd Gen)
- Custom sizes

## Input Data Requirements

The parser expects data with:
- **Inference Results**: Model output and performance metrics
- **Power Data**: Power consumption during inference
- **Thermal Data**: Temperature monitoring
- **Resource Metrics**: Memory, bandwidth, cache utilization

### Expected Folder Structure

```
llama_runs/
├── llama_7b/
│   ├── batch_1/
│   │   ├── inference_output.txt
│   │   ├── power_metrics.csv
│   │   └── thermal_data.csv
│   ├── batch_4/
│   └── batch_8/
├── llama_13b/
│   ├── batch_1/
│   ├── batch_4/
│   └── batch_8/
└── llama_70b/
    ├── batch_1/
    └── batch_4/
```

## Output Metrics

### Performance Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| **Throughput** | tokens/sec | Generation speed |
| **Latency** | ms/token | Time per token |
| **Time to First Token** | ms | Prefill phase latency |
| **Generation Time** | ms | Decoding phase duration |
| **Tokens Generated** | count | Total output tokens |

### Power Metrics

| Metric | Description |
|--------|-------------|
| **Average Power** | Mean power during inference |
| **Peak Power** | Maximum power consumption |
| **Energy per Token** | Total energy / tokens generated |
| **Power Efficiency** | Tokens per second per watt |

### Memory Metrics

| Metric | Description |
|--------|-------------|
| **Model Size** | Parameter count |
| **Memory Used** | GPU/System memory consumed |
| **Bandwidth Utilization** | Memory bandwidth usage percentage |
| **Cache Hit Rate** | L3 cache effectiveness |

### Thermal Metrics

| Metric | Description |
|--------|-------------|
| **Peak Temperature** | Maximum die temperature |
| **Average Temperature** | Mean temperature during run |
| **Throttling Events** | Number of thermal throttles |
| **Thermal Headroom** | Distance from throttle point |

## Workflow

### Step 1: Prepare Data

Organize Llama model results hierarchically:

```
llama_experiments/
├── model_size_config/
│   └── batch_config/
│       ├── Model output files
│       ├── Power metrics
│       └── Thermal data
```

### Step 2: Run Parser

```bash
python bm_llama_parser.py -i .\llama_experiments\ -o .\results\analysis.xlsx
```

### Step 3: Review Results

Analyze generated Excel file for:
- Model scaling efficiency
- Batch size impact on performance
- Power vs. performance trade-offs
- Thermal characteristics

## Analysis Examples

### Model Size Comparison

```
Llama 7B:   1200 tokens/sec, 45W avg
Llama 13B:   750 tokens/sec, 65W avg
Llama 70B:   180 tokens/sec, 150W avg
```

### Batch Size Impact

```
Batch 1:   100 tokens/sec, 200ms latency
Batch 4:   350 tokens/sec, 180ms latency
Batch 8:   450 tokens/sec, 200ms latency
```

### Power Efficiency

```
Llama 7B:   26.7 tok/sec/W  (1200 tok/sec ÷ 45W)
Llama 13B:  11.5 tok/sec/W  (750 tok/sec ÷ 65W)
Llama 70B:   1.2 tok/sec/W  (180 tok/sec ÷ 150W)
```

## Configuration

### Custom Metrics Definition

Create custom metrics by editing the parser or providing configuration:

```json
{
  "metrics": {
    "throughput": {
      "name": "tokens/second",
      "unit": "tokens/sec"
    },
    "latency": {
      "name": "milliseconds/token",
      "unit": "ms/tok"
    },
    "efficiency": {
      "name": "tokens/watt",
      "unit": "tok/W"
    }
  }
}
```

## Performance Analysis

### Scaling Efficiency

Measures how well performance scales with:
- Model size increases
- Batch size changes
- Hardware improvements

### Efficiency Metrics

```
Scaling Efficiency = Performance Increase / Resource Increase
```

Example:
- Batch 1→4: 3.5× throughput, 2× memory = 1.75 scaling
- 7B→13B: 0.62× throughput, 1.86× memory = 0.33 scaling

## Comparison Examples

### Model Comparison

```bash
# Generate separate analysis for each model
python bm_llama_parser.py -i .\llama_7b\ -o results_7b.xlsx
python bm_llama_parser.py -i .\llama_70b\ -o results_70b.xlsx
# Compare results manually or with external tools
```

### Platform Comparison

Compare same model across different:
- Hardware (GPU types, CPU models)
- Software configurations
- Optimization levels

## Troubleshooting

### Issue: Model Not Recognized

**Solution:**
- Verify model size in configuration
- Check file naming conventions
- Ensure consistent model identification
- Review parser documentation for supported models

### Issue: Missing Metrics

**Solution:**
- Verify all required data files present
- Check file format compatibility
- Validate metric naming matches expected values
- Review input data structure

### Issue: Throughput Calculation Errors

**Solution:**
- Check timing data accuracy
- Verify token count measurements
- Validate power measurement synchronization
- Review calculation formulas

## Optimization Tips

1. **Batch Size Tuning**: Test multiple batch sizes for optimal throughput
2. **Model Precision**: Compare FP32 vs. FP16 vs. INT8
3. **Memory Bandwidth**: Monitor and optimize memory access patterns
4. **Thermal Management**: Monitor throttling frequency
5. **Power Budget**: Optimize within power constraints

## Related Parsers

- [Phi_summary](./phi-summary.md) - Phi model analysis
- [ParseAll](./parseall.md) - Multi-source aggregation
- [Collection_Parser](./collection-parser.md) - Collection-based analysis

## Additional Resources

- Llama Model Documentation
- Hardware Performance Analysis
- Power Measurement Best Practices
- Thermal Management Guidelines

---

[Back to main README](../README.md)
