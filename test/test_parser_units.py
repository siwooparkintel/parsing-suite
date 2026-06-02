"""
test_parser_units.py
====================
Unit tests for the shared parser components in parsers/.

Each test exercises a specific function in isolation using either synthetic
data or the fixture files under test/fixtures/.  These tests run fast and
do not invoke any top-level workload parser script.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Put the project root on sys.path so "parsers.*" imports resolve.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import parsers.tools as tools
import parsers.model_output_parser as mop
import parsers.bm_llama_output_parser as lop
import parsers.Phi_output_parser as pop
import parsers.power_summary_parser as psp
import parsers.flattener as flattener

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ===========================================================================
# parsers/tools.py
# ===========================================================================

class TestParseNumeric:
    def test_integer_string(self):
        assert tools.parseNumeric("1234 ms") == "1234"

    def test_float_string(self):
        assert tools.parseNumeric("3.14 seconds") == "3.14"

    def test_no_digits(self):
        assert tools.parseNumeric("no digits here") == ""

    def test_mixed_text(self):
        assert tools.parseNumeric("[ INFO ] Duration: 45000.00 ms") == "4500000"

    def test_only_number(self):
        assert tools.parseNumeric("42") == "42"


class TestTryRoundIfNumber:
    def test_valid_float_string(self):
        assert tools.tryRoundifNumber("3.14159") == 3.14

    def test_valid_integer_string(self):
        assert tools.tryRoundifNumber("100") == 100.0

    def test_non_numeric_string(self):
        result = tools.tryRoundifNumber("N/A")
        assert result == "N/A"

    def test_empty_string(self):
        result = tools.tryRoundifNumber("")
        assert result == ""


class TestSplitLastItem:
    def test_windows_path(self):
        path = "C:\\folder\\subfolder\\file.txt"
        result = tools.splitLastItem(path, "\\", 1)
        assert result[0] == "C:\\folder\\subfolder"
        assert result[1] == "file.txt"

    def test_two_levels(self):
        path = "a\\b\\c\\d"
        result = tools.splitLastItem(path, "\\", 1)
        assert result[0] == "a\\b\\c"
        assert result[1] == "d"


class TestTrimList:
    def test_removes_trailing_empty(self):
        assert tools.trim_list(["a", "b", "", ""]) == ["a", "b"]

    def test_no_trailing_empty(self):
        assert tools.trim_list(["x", "y"]) == ["x", "y"]

    def test_all_empty(self):
        assert tools.trim_list(["", ""]) == []


# ===========================================================================
# parsers/model_output_parser.py  (MS AI model format)
# ===========================================================================

MS_MODEL_AI_PARSING_ITEMS = [
    {"key": "read_model",      "lookup": "[ INFO ] Read model took",                              "unit": "ms"},
    {"key": "compile_model",   "lookup": "[ INFO ] Compile model took",                           "unit": "ms"},
    {"key": "start_mem_usage", "lookup": "[ INFO ] Start of compilation memory usage: Peak",      "unit": "KB"},
    {"key": "end_mem_usage",   "lookup": "[ INFO ] End of compilation memory usage: Peak",        "unit": "KB"},
    {"key": "ram_used",        "lookup": "[ INFO ] Compile model ram used",                       "unit": "KB"},
    {"key": "first_inference", "lookup": "[ INFO ] First inference took",                         "unit": "ms"},
    {"key": "device",          "lookup": "[ INFO ] Execution Devices:",                           "unit": ""},
    {"key": "iterations",      "lookup": "[ INFO ] Count:",                                       "unit": ""},
    {"key": "duration",        "lookup": "[ INFO ] Duration:",                                    "unit": "ms"},
    {"key": "latency_median",  "lookup": "[ INFO ]    Median:",                                   "unit": "ms"},
    {"key": "latency_average", "lookup": "[ INFO ]    Average:",                                  "unit": "ms"},
    {"key": "throughput",      "lookup": "[ INFO ] Throughput:",                                  "unit": "FPS"},
]

MS_MODEL_FIXTURE = (
    FIXTURES_DIR
    / "ms_model"
    / "WW01_PTL_NPU_HW"
    / "NPU_run001"
    / "NPU_xpu_model_qdq_proxy_w8a16_output.txt"
)


class TestMSModelOutputParser:
    def test_readTextfile_returns_dict(self):
        result = mop.readTextfile(str(MS_MODEL_FIXTURE), MS_MODEL_AI_PARSING_ITEMS)
        assert isinstance(result, dict)

    def test_throughput_parsed(self):
        result = mop.readTextfile(str(MS_MODEL_FIXTURE), MS_MODEL_AI_PARSING_ITEMS)
        assert "throughput" in result
        assert result["throughput"][0] == pytest.approx(2.22, rel=1e-2)
        assert result["throughput"][1] == "FPS"

    def test_latency_median_parsed(self):
        result = mop.readTextfile(str(MS_MODEL_FIXTURE), MS_MODEL_AI_PARSING_ITEMS)
        assert result["latency_median"][0] == pytest.approx(450.0, rel=1e-3)

    def test_parse_model_results_status(self):
        result = mop.parseModelResults(str(MS_MODEL_FIXTURE), MS_MODEL_AI_PARSING_ITEMS)
        assert result["model_output_status"] == "successful"
        assert "model_output_data" in result

    def test_device_parsed_as_string(self):
        result = mop.readTextfile(str(MS_MODEL_FIXTURE), MS_MODEL_AI_PARSING_ITEMS)
        assert result["device"][0] == "NPU"


# ===========================================================================
# parsers/bm_llama_output_parser.py  (BM Llama format)
# ===========================================================================

BM_PARSING_ITEMS = [
    {"key": "Pipeline init time", "lookup": "[ INFO ] Pipeline initialization time: ", "unit": "s"},
    {"key": "Inference count",    "lookup": "inference count: ",                        "unit": ""},
    {"key": "Average",            "lookup": "[ INFO ] [Average] P[",                   "unit": "string"},
]

LLAMA_FIXTURE = (
    FIXTURES_DIR
    / "llama"
    / "WW01_PTL_NPU_HW"
    / "NPU_run001"
    / "NPU_llama-3.1-8b-instruct-npu-ov_2026-01-15_18-17-57.txt"
)


class TestBMLlamaOutputParser:
    def test_readTextfile_returns_dict(self):
        result = lop.readTextfile(str(LLAMA_FIXTURE), BM_PARSING_ITEMS)
        assert isinstance(result, dict)

    def test_pipeline_init_time_parsed(self):
        result = lop.readTextfile(str(LLAMA_FIXTURE), BM_PARSING_ITEMS)
        assert "Pipeline init time" in result
        assert result["Pipeline init time"][0] == pytest.approx(12.5, rel=1e-3)

    def test_throughput_from_average_line(self):
        result = lop.readTextfile(str(LLAMA_FIXTURE), BM_PARSING_ITEMS)
        # bm_llama_output_parser maps "2nd tokens throughput" -> "throughput"
        assert "throughput" in result
        assert result["throughput"][0] == pytest.approx(15.23, rel=1e-2)


# ===========================================================================
# parsers/Phi_output_parser.py  (Phi model format)
# ===========================================================================

PHI_AI_PARSING_ITEMS = [
    {"key": "prompt_length",    "lookup": "prompt length: ",                         "unit": ""},
    {"key": "prefill_time",     "lookup": "Prefill stage total time = ",             "unit": "s"},
    {"key": "total_token_gen",  "lookup": "total_num_generated_tokens : ",           "unit": ""},
    {"key": "duration",         "lookup": "total_time_new_tokens : ",                "unit": "s"},
    {"key": "Tokens_per_second","lookup": "Tokens per second : :",                   "unit": "s"},
    {"key": "TPS_models_only",  "lookup": "Tokens per second (Models Only): :",      "unit": "s"},
]

PHI_FIXTURE = (
    FIXTURES_DIR
    / "phi"
    / "WW01_PTL_NPU_HW"
    / "NPU_run001"
    / "NPU_phi_qdq_proxy_output.txt"
)


class TestPhiOutputParser:
    def test_readTextfile_returns_dict(self):
        result = pop.readTextfile(str(PHI_FIXTURE), PHI_AI_PARSING_ITEMS)
        assert isinstance(result, dict)

    def test_tokens_per_second_parsed(self):
        result = pop.readTextfile(str(PHI_FIXTURE), PHI_AI_PARSING_ITEMS)
        assert "Tokens_per_second" in result
        assert result["Tokens_per_second"][0] == pytest.approx(15.15, rel=1e-3)

    def test_total_token_gen_parsed(self):
        result = pop.readTextfile(str(PHI_FIXTURE), PHI_AI_PARSING_ITEMS)
        assert result["total_token_gen"][0] == pytest.approx(128.0)

    def test_parse_model_results_successful(self):
        result = pop.parseModelResults(str(PHI_FIXTURE), PHI_AI_PARSING_ITEMS)
        assert result["model_output_status"] == "successful"


# ===========================================================================
# parsers/power_summary_parser.py
# ===========================================================================

POWER_FIXTURE = (
    FIXTURES_DIR / "ms_model" / "WW01_PTL_NPU_HW" / "NPU_run001" / "pacs-summary.csv"
)

TEST_DAQ_TARGET = {
    "P_SOC": -1,
    "P_VCCCORE": -1,
    "P_VCCSA": -1,
    "P_VCCGT": -1,
    "Run Time": -1,
    "SOC_POWER_RAIL_NAME": "P_SOC",
    "PCORE_POWER_RAIL_NAME": "P_VCCCORE",
    "SA_POWER_RAIL_NAME": "P_VCCSA",
    "GT_POWER_RAIL_NAME": "P_VCCGT",
    "TARGET_COLUMN": "Average",
}


class TestPowerSummaryParser:
    def test_returns_power_obj_with_data(self):
        result = psp.parsePowerSummaryCSV(str(POWER_FIXTURE), TEST_DAQ_TARGET)
        assert "power_data" in result
        assert "power_path" in result

    def test_soc_power_parsed(self):
        result = psp.parsePowerSummaryCSV(str(POWER_FIXTURE), TEST_DAQ_TARGET)
        assert "P_SOC" in result["power_data"]
        assert result["power_data"]["P_SOC"] == pytest.approx(3.456, rel=1e-3)

    def test_run_time_parsed(self):
        result = psp.parsePowerSummaryCSV(str(POWER_FIXTURE), TEST_DAQ_TARGET)
        assert "Run Time" in result["power_data"]
        assert result["power_data"]["Run Time"] == pytest.approx(120.0)

    def test_energy_calculated_from_power_and_runtime(self):
        result = psp.parsePowerSummaryCSV(str(POWER_FIXTURE), TEST_DAQ_TARGET)
        # Energy (J) = P_SOC * Run Time
        assert "Energy (J)" in result["power_data"]
        expected = 3.456 * 120.0
        assert result["power_data"]["Energy (J)"] == pytest.approx(expected, rel=1e-3)


# ===========================================================================
# parsers/flattener.py  (flatten helpers)
# ===========================================================================

class TestFlattener:
    """Light tests to confirm the flatten helpers don't crash on typical inputs."""

    def _make_entry_with_power(self):
        picks = {
            "SOC_POWER_RAIL_NAME": "P_SOC",
            "PCORE_POWER_RAIL_NAME": "P_VCCCORE",
            "SA_POWER_RAIL_NAME": "P_VCCSA",
            "GT_POWER_RAIL_NAME": "P_VCCGT",
            "power_pick": "MED_picked",
        }
        entry = {
            "data_label": ["WW01", "NPU_run001"],
            "data_type": ["POWER"],
            "power_obj": {
                "power_data": {
                    "P_SOC": 3.456,
                    "P_VCCCORE": 1.2,
                    "P_VCCSA": 0.4,
                    "P_VCCGT": 0.6,
                    "Energy (J)": 414.72,
                    "MED_picked": True,
                },
                "power_type": "POWER",
                "power_path": "test/path",
            },
        }
        return entry, picks

    def test_flatten_power_dic_returns_dict(self):
        entry, picks = self._make_entry_with_power()
        result = flattener.flatten_power_dic(entry, picks)
        assert isinstance(result, dict)

    def test_flatten_ETL_dic_empty_when_no_etl(self):
        entry, _ = self._make_entry_with_power()
        result = flattener.flatten_ETL_dic(entry)
        assert result == {}

    def test_flatten_AI_model_dic_empty_when_no_model(self):
        entry, _ = self._make_entry_with_power()
        result = flattener.flatten_AI_model_dic(entry)
        assert result == {}
