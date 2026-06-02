# Test Suite Reference — ParseAll.py & Collection_Parser.py

This document is the authoritative reference for understanding the focused integration
test suite and for extending it in the future. It covers architecture, fixture structure,
shared helpers, each test's intent, known production bugs that were fixed, and a
concrete guide for adding new tests.

---

## 1. Scope

The suite covers two top-level parsing scripts:

| Script | Output file suffix | Key reporter function |
|---|---|---|
| `ParseAll.py` | `_allPower_v.xlsx` | `rpt.writeParsedAllInExcel` → `rap.reportAllPowerAndType` → `create_V_H_Excel` |
| `Collection_Parser.py` | `_collection.xlsx` | `rpt.writeParsedCollection` → `rap.reportCollectionWithAutohide` |

Both scripts are run as **subprocesses** (not imported). Tests assert on exit code and
on the content of the written Excel file.

---

## 2. File Map

```
parsing-suite/
├── ParseAll.py                          # target script 1
├── Collection_Parser.py                 # target script 2
├── run_tests.bat                        # convenience runner: runs both test files with -v --tb=short
├── parsers/
│   ├── reporter_allpower.py             # ← PRODUCTION BUGS FIXED HERE (see section 7)
│   └── flattener.py
└── test/
    ├── conftest.py                      # shared path constants + run_parser() helper
    ├── test_parseall.py                 # 8 integration tests for ParseAll.py
    ├── test_collection_parser.py        # 9 integration tests for Collection_Parser.py
    └── fixtures/
        ├── config/
        │   └── test_config.json         # shared config for both parsers
        ├── parseall_input/              # input folder passed to ParseAll -i
        │   └── WW01_PTL_HW/
        │       ├── GPU_model_run/
        │       │   ├── pacs-summary.csv
        │       │   └── GPU_xpu_model_qdq_proxy_w8a16_output.txt   # MS AI model
        │       └── NPU_llama_run/
        │           ├── pacs-summary.csv
        │           └── NPU_llama-3.1-8b-instruct-npu-ov_2026-01-15.txt  # Llama BM
        ├── collection_power/            # CSV files referenced by Collection_Parser tests
        │   ├── run_baseline/pacs-summary.csv
        │   └── run_optimized/pacs-summary.csv
        ├── llama/                       # standalone llama fixture (not used by current tests)
        │   └── WW01_PTL_NPU_HW/NPU_run001/
        │       ├── NPU_llama-3.1-8b-instruct-npu-ov_2026-01-15_18-17-57.txt
        │       └── pacs-summary.csv
        ├── ms_model/                    # standalone MS model fixture (not used by current tests)
        │   └── WW01_PTL_NPU_HW/NPU_run001/
        │       ├── NPU_xpu_model_qdq_proxy_w8a16_output.txt
        │       └── pacs-summary.csv
        └── phi/                         # phi fixture (not used by current tests)
```

---

## 3. conftest.py — Shared Infrastructure

**File:** `test/conftest.py`

### Path constants (module-level, importable directly)

```python
TEST_DIR        = Path(__file__).resolve().parent          # .../parsing-suite/test
FIXTURES_DIR    = TEST_DIR / "fixtures"
PROJECT_ROOT    = TEST_DIR.parent                          # .../parsing-suite
TEST_CONFIG     = FIXTURES_DIR / "config" / "test_config.json"

FIXTURE_PARSEALL_INPUT = FIXTURES_DIR / "parseall_input"
FIXTURE_COLLECTION_PWR = FIXTURES_DIR / "collection_power"
FIXTURE_MS_MODEL       = FIXTURES_DIR / "ms_model"
FIXTURE_LLAMA          = FIXTURES_DIR / "llama"
FIXTURE_PHI            = FIXTURES_DIR / "phi"
```

Test files import constants directly: `from conftest import run_parser, TEST_CONFIG, FIXTURE_PARSEALL_INPUT`

### `run_parser(script_name, args, cwd=PROJECT_ROOT)`

Runs `python <PROJECT_ROOT>/<script_name> <args>` as a subprocess.
Returns `subprocess.CompletedProcess` (never raises on non-zero exit — use `result.returncode`).
`cwd` defaults to `PROJECT_ROOT` so relative imports inside parsers resolve correctly.

### pytest fixtures

All fixtures are `scope="session"` (computed once per pytest run):
- `project_root`, `fixtures_dir`, `test_config`
- `fixture_parseall_input`, `fixture_collection_power`
- `fixture_ms_model`, `fixture_llama`, `fixture_phi`
- `tmp_output` (function scope) — returns `tmp_path / "test_out"` as an output prefix

---

## 4. test_config.json — Shared Config File

**File:** `test/fixtures/config/test_config.json`

> **Convention note:** The `.config` extension is deprecated. All new and migrated config files use `.json`.
> Existing production configs (`PTL_default.config`, `LNL_default.config`) still use `.config` but
> future parsers will use `.json`. The test fixture follows the new convention.

Both `ParseAll.py` and `Collection_Parser.py` are run with `-c <path to test_config.json>`.

Key sections:
- **`DAQ_target`**: Rails `P_SOC`, `P_VCCCORE`, `P_VCCSA`, `P_VCCGT`, `Run Time`.
  `TARGET_COLUMN` = `"Average"` (matches the `Average` column in all fixture CSVs).
- **`socwatch_targets`**: One entry — `CPU_model` / `"CPU native model"`.
  Fixtures do NOT include socwatch files, so this never matches. Tests must tolerate empty socwatch.
- **`PCIe_targets`**: One entry — `PCIe_LPM`. Fixtures do NOT include PCIe socwatch files.
- **`AI_parsing_items`**: 12 items for MS model output parsing.
  Critical keys: `throughput` (unit=`FPS`), `latency_median` (unit=`ms`).
  Column name in Excel: `"throughput (FPS)"` (key + " (" + unit + ")").
- **`BM_parsing_items`**: 3 items for Llama BM output parsing.
  Required keys: `"Pipeline init time"`, `"Inference count"`, `"Average"`.
  The `Average` lookup is `"[ INFO ] [Average] P["` — the parser then splits on `]` index 1
  to get the throughput data string.
- **`Second_folder_list`**: `["ETL", "POWER", "SOCWATCH", "PCIE"]`
  Controls `getDatasetLabel()` in ParseAll — if the parent folder name is in this list,
  it goes one level higher for the dataset label.

---

## 5. Fixture Files

### pacs-summary.csv format

All power summary CSVs share the same structure:

```csv
Rail Name,Min,Max,Average
P_SOC,<float>,<float>,<float>
P_VCCCORE,<float>,<float>,<float>
P_VCCSA,<float>,<float>,<float>
P_VCCGT,<float>,<float>,<float>
Run Time,<float>,<float>,<float>
```

`power_summary_parser.parsePowerSummaryCSV()` reads the `Average` column (set by `TARGET_COLUMN`
in DAQ_target). It also computes `Energy (J) = P_SOC_avg * Run Time_avg` if both are present.

### MS AI model output format (`*_qdq_proxy_*_output.txt`)

File name must contain `_qdq_proxy_` OR `_output.txt` but NOT contain `llama` (else it routes to the Llama parser).

Required lines matched by `AI_parsing_items` lookups:
```
[ INFO ] Read model took 1234.50 ms
[ INFO ] Compile model took 5678.90 ms
[ INFO ] Start of compilation memory usage: Peak 102400 KB
[ INFO ] End of compilation memory usage: Peak 204800 KB
[ INFO ] Compile model ram used 102400 KB
[ INFO ] First inference took 450.00 ms
[ INFO ] Execution Devices: GPU
[ INFO ] Count:            100
[ INFO ] Duration:         45000.00 ms
[ INFO ]    Median:        450.00 ms
[ INFO ]    Average:       450.00 ms
[ INFO ] Throughput:       2.22 FPS
```

`model_output_parser.parseModelResults` checks `throughput[1] != ""` AND `latency_median[1] != ""`
to mark status as `"successful"`. Both must be present in the file.

### Llama BM output format

File name must contain `llama` (case-sensitive check: `"llama" in name`).

**CRITICAL FORMAT** — the Average line has NO colon-space after `P[0]`:
```
[ INFO ] Pipeline initialization time: 12.500 s
inference count: 100
[ INFO ] [Average] P[0]2nd tokens throughput: 15.23 tok/s, 2nd token latency: 65.67 ms, Inference count: 100
```

`bm_llama_output_parser.parseAverage` receives the text after `]` index 1 from the split
(`target_string.split("]")[1]`). If the line were `P[0]: 2nd tokens...` the split would
receive `: 2nd tokens...` — the key would parse as `""` and `2nd token latency` key would
be wrong. **Always use the no-colon-space format.**

`bm_llama_output_parser.parseModelResults` requires both `Pipeline init time` and
`Inference count` to be present and non-empty or it sets `model_output_status = "failed"`.

Excel attribute for throughput: `"2nd tokens throughput (tok/s)"` (set by `getMSmodelKeyUnit`
in `flattener.py` using the `"tok/s"` unit from `parseAverage`).

### ParseAll input folder structure

```
parseall_input/
└── WW01_PTL_HW/           ← WW label (folder[-3] = "WW01_PTL_HW")
    ├── GPU_model_run/      ← run label (folder[-2] = "GPU_model_run")
    │   ├── pacs-summary.csv
    │   └── GPU_xpu_model_qdq_proxy_w8a16_output.txt
    └── NPU_llama_run/      ← run label
        ├── pacs-summary.csv
        └── NPU_llama-3.1-8b-instruct-npu-ov_2026-01-15.txt
```

`getDatasetLabel(abs_path)` returns `[folder[-3], folder[-2]]` because `folder[-2]`
(`GPU_model_run`, `NPU_llama_run`) is NOT in `Second_folder_list`. So:
- `data_label[0]` = `"WW01_PTL_HW"` → becomes `"Data label"` attribute row value
- `data_label[1]` = `"GPU_model_run"` → becomes `"Condition"` attribute row value

`flatten_data` in `reporter_allpower.py` maps `data_label[0]` → `"Data label"` and
`data_label[1]` → `"Condition"`.

### Collection_Parser input (collection JSON)

Collection JSON is generated **dynamically** inside each test using absolute paths. This is
required because `psp.parsePowerSummaryCSV()` opens the file directly with the path from
the JSON — relative paths would fail.

Entry format:
```json
{
  "data_label": "Baseline",
  "condition": "baseline_run",
  "data_summary_type": "compact",
  "power_summary_path": "<absolute path to pacs-summary.csv>"
}
```

- `data_label` is a **string** (unlike ParseAll which uses a list).
- `condition` is the unique ID used by `pullData()` to look up the dataset.
- `data_summary_type`: `"compact"` or `"expanded"`. Compact hides extra socwatch rows
  via the `auto-hide` mechanism. Since there is no socwatch in test fixtures, this
  distinction only affects `addKeyAutoHide()` (which iterates an empty list either way).
- Optional keys: `socwatch_summary_path`, `PCIe_socwatch_summary_path`.

---

## 6. Excel Output Structure

Both parsers write a **transposed** DataFrame:

```
| Attribute         | dataset_col_1  | dataset_col_2  |
|-------------------|----------------|----------------|
| Data label        | WW01_PTL_HW    | WW01_PTL_HW    |  ← ParseAll only
| Data_label        | Baseline       | Optimized      |  ← Collection only (underscore)
| Condition         | GPU_model_run  | NPU_llama_run  |
| P_SOC             | 4.1            | 3.1            |
| P_VCCCORE         | 1.4            | 1.05           |
| ...               | ...            | ...            |
| throughput (FPS)  | 2.22           | None           |
| 2nd tokens...     | None           | 15.23          |
| auto-hide         | False          | False          |  ← Collection only
```

Key differences between the two parsers:

| Aspect | ParseAll (`_allPower_v.xlsx`) | Collection (`_collection.xlsx`) |
|---|---|---|
| Label row name | `"Data label"` (space) | `"Data_label"` (underscore) |
| Label value | list — `data_label[0]` | string — `data_label` |
| Condition row | `data_label[1]` | `condition` field |
| auto-hide row | absent | present (hides extra socwatch rows) |
| socwatch flatten | `flatten_socwatch_dic` (returns `{}`) | `flatten_socwatch_dic_per_core` (returns `[]`) |
| ETL / model data | included via `flatten_AI_model_dic` etc. | power + socwatch + PCIe only |

---

## 7. Production Bugs Fixed During Test Development

Both bugs in `parsers/reporter_allpower.py` surface when there is **no socwatch data**
(the common case when testing with power-only fixtures).

### Bug 1 — `IndexError: list index out of range` (line ~48)

**Root cause:** `flatten_socwatch_dic_per_core()` in `flattener.py` returns `[]` (empty list)
when no socwatch data exists. `flatten_data_with_autohide()` then called `flattened_socwatch_list[0]`
unconditionally.

**Fix:**
```python
# Before
flattened.update(flattened_socwatch_list[0])

# After
flattened.update(flattened_socwatch_list[0]) if flattened_socwatch_list else None
```

### Bug 2 — `TypeError: 'NoneType' object is not iterable` (line ~33)

**Root cause:** `autoHideColumn()` sets `auto_hide_row = None` and only assigns it if
`"auto-hide"` is found in column A. When no socwatch rows exist, the `"auto-hide"` attribute
is never written, so `auto_hide_row` stays `None` and `for cell in auto_hide_row` crashes.

**Fix:**
```python
# Before
for cell in auto_hide_row :

# After
for cell in auto_hide_row or [] :
```

---

## 8. Current Test Inventory

### test_parseall.py (8 tests)

| Test | What it verifies |
|---|---|
| `test_help_flag` | `-h` exits 0, prog name `"AI summary parser"` or `"usage"` in output |
| `test_power_only_run` | exit code 0, `_allPower_v.xlsx` file exists |
| `test_output_excel_has_attribute_column` | cell(1,1) == `"Attribute"` |
| `test_output_has_data_label_row` | `"Data label"` in column A values |
| `test_output_has_power_rail_attributes` | `"P_SOC"` and `"P_VCCCORE"` in column A |
| `test_multiple_datasets_produce_multiple_columns` | `max_column >= 4` (Attribute + ≥3 datasets) |
| `test_ms_model_throughput_attribute` | `"throughput (FPS)"` in column A |
| `test_llama_throughput_attribute` | `"2nd tokens throughput (tok/s)"` in column A |

All tests call `_run_parseall(tmp_path, FIXTURE_PARSEALL_INPUT)` which runs:
```
python ParseAll.py -c <test_config.json> -i <parseall_input/> -o <tmp/result>
```

### test_collection_parser.py (9 tests)

| Test | What it verifies |
|---|---|
| `test_help_flag` | `-h` exits 0, `"Collection Parser"` or `"usage"` in output |
| `test_power_only_collection_exits_zero` | exit code 0 for 2-entry power-only collection |
| `test_output_excel_created` | `_collection.xlsx` file exists |
| `test_output_has_attribute_column` | cell(1,1) == `"Attribute"` |
| `test_output_has_data_label_row` | `"Data_label"` (underscore) in column A values |
| `test_output_has_power_rail_attributes` | `"P_SOC"` and `"P_VCCCORE"` in column A |
| `test_two_entries_produce_two_data_columns` | `max_column == 3` (Attribute + 2) |
| `test_both_labels_appear_in_output` | `"Baseline"` and `"Optimized"` in Data_label row |
| `test_single_entry_collection` | 1-entry collection → exit 0, `max_column == 2` |

All Collection_Parser tests generate the collection JSON dynamically via `_build_collection_json()`
and `_two_entry_collection()`.

---

## 9. Adding New Tests

### Pattern: new ParseAll scenario

1. Create a new fixture subfolder under `test/fixtures/parseall_input/` with the correct
   folder depth (`WW_label/run_label/files`).
2. Write the test in `test_parseall.py`. Call `_run_parseall(tmp_path, FIXTURE_PARSEALL_INPUT)`
   (reuses existing fixtures) or define a new input dir constant in `conftest.py` and pass it.
3. Use `_load_attribute_column(xlsx)` to inspect attribute rows without hardcoding row indices.

Example — adding a socwatch test:
```python
# 1. Add fixture: test/fixtures/parseall_input/WW01_PTL_HW/socwatch_run/
#    Place: pacs-summary.csv  AND  a socwatch_regular_<name>.csv matching socwatch_targets lookup

# 2. Add constant in conftest.py (if using separate folder):
# FIXTURE_PARSEALL_WITH_SW = FIXTURES_DIR / "parseall_input_sw"

# 3. Test:
def test_socwatch_attribute_present(tmp_path):
    _, xlsx = _run_parseall(tmp_path, FIXTURE_PARSEALL_INPUT)
    attributes = _load_attribute_column(xlsx)
    assert "CPU native model        CPU_model" in attributes  # getSocwatchHeader format: key + "        " + label
```

Note: `getSocwatchHeader(key, label)` in `flattener.py` formats as `f"{key}        {label}"`
(8 spaces between key and label). Column names will look like `"CPU native model        CPU_model"`.

### Pattern: new Collection_Parser scenario

1. Create new fixture CSVs under `test/fixtures/collection_power/<run_name>/pacs-summary.csv`.
2. In the test, add a helper that returns the absolute path string, then build the collection
   JSON via `_build_collection_json(entries, tmp_path / "collection.json")`.
3. To add socwatch: add `"socwatch_summary_path"` to the entry dict with an absolute path
   to a valid socwatch CSV. The CSV must contain tables matching `socwatch_targets` lookups.

Example — adding a socwatch collection entry:
```python
def _entry_with_socwatch(tmp_path):
    return {
        "data_label": "WithSocwatch",
        "condition": "sw_run",
        "data_summary_type": "compact",
        "power_summary_path": str((FIXTURE_COLLECTION_PWR / "run_baseline" / "pacs-summary.csv").resolve()),
        "socwatch_summary_path": str((FIXTURE_COLLECTION_PWR / "run_baseline" / "socwatch.csv").resolve()),
    }
```

### Pattern: adding a new top-level parser (e.g., Phi_summary.py)

1. Add a fixture constant in `conftest.py`:
   ```python
   FIXTURE_PHI_INPUT = FIXTURES_DIR / "phi_input"
   ```
2. Add a `@pytest.fixture` for it (follow the existing session-scope pattern).
3. Create `test/test_phi_summary.py` using the same structure:
   - `_run_phi(tmp_path, input_dir)` helper
   - `_load_attribute_column()` — copy or import from the ParseAll test module
   - Identify the output file suffix from the parser's reporter call
   - Write help, exit-0, Excel-exists, Attribute-column, label-row, and data-attribute tests

---

## 10. Running the Suite

```batch
# From parsing-suite/ root — runs both test files
run_tests.bat

# Equivalent pytest command
python -m pytest test/test_parseall.py test/test_collection_parser.py -v --tb=short

# Run only one file
python -m pytest test/test_parseall.py -v

# Run a single test by name
python -m pytest test/test_parseall.py::test_llama_throughput_attribute -v
```

Python executable used: whatever is first on `PATH` (or the venv if activated).
The venv is at `c:\Users\siwoopar\code\.venv`.

---

## 11. Critical Implementation Details to Remember

- **ParseAll uses Windows path separator `\\`** throughout its `path_splitter` constant.
  Fixture paths must use real Windows absolute paths (which `Path.resolve()` provides).
- **`getDatasetLabel` depth depends on `Second_folder_list`**. If the immediate parent
  folder of a file matches an entry in `Second_folder_list` (e.g., `POWER`, `ETL`),
  it goes one level higher (`folder[-4]`, `folder[-2]`). The current fixtures do NOT use
  this structure, so `folder[-3]` / `folder[-2]` applies.
- **Collection_Parser does NOT call `checkAndMarkPower`** (commented out). Power type
  (`power_type` field in `power_obj`) is never set. This means `flatten_power_dic` will
  NOT write a `power_type` attribute row. Do not assert for it in Collection_Parser tests.
- **ParseAll calls `checkAndMarkPower`** before reporting. This sets `power_type` on matched
  datasets. However, `sortAndPick` requires a SOC rail in `power_data` — which the test
  config provides via `SOC_POWER_RAIL_NAME = "P_SOC"`.
- **`_allPower_v.xlsx` only** — the `_h.xlsx` (horizontal) variant is commented out in
  `create_V_H_Excel`. Do not assert for `_allPower_h.xlsx`.
- **openpyxl `read_only=True`** — use this when only reading to avoid locking issues.
  Always call `wb.close()` after reading.
- **The `auto-hide` row** is only present in `_collection.xlsx`, not in `_allPower_v.xlsx`.
  It will always be `False` when no socwatch data exists (because `addKeyAutoHide` only
  iterates the socwatch list, and the list is empty).
- **Config file extension convention:** `.config` is deprecated; new configs use `.json`.
  The test fixture is `test_config.json`. Production defaults (`PTL_default.config`,
  `LNL_default.config`) still use `.config` — do not rename them unless the parsers
  are updated to look for the new name. When adding a new parser's test, always
  create its fixture config as `<name>.json`.
