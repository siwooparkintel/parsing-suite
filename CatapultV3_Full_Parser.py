import os
import json
import time
from os import listdir
from os.path import isfile, join
import parsers.tools as tools

import parsers.pcie_socwatch_summary_parser as psoc
import parsers.socwatch_summary_parser as soc
import parsers.power_summary_parser as psp
import parsers.power_trace_parser as ptp
import parsers.sync_time_parser as stp
import parsers.ETL_power_slicer as eps
import parsers.power_checker as pck
import parsers.ETL_parser as etl
import parsers.reporter as rpt




import argparse

parser = argparse.ArgumentParser(prog='Catapult V3 Full Parser V1.0')
parser.add_argument('-i', '--input', help='input path. Catapult V3 Full Parser needs multiple log files to sync Host and DUT, also ICOB.exe output files to web sites break downs, all path will be fed as JSON format')
parser.add_argument('-o', '--output', help='output path. location of file and file name')
parser.add_argument('-d', '--daq', help='DAQ power rail name dictionary')
parser.add_argument('-st', '--swtarget', help='a list of dictionary objects that you want to parse from the socwatch summary')
parser.add_argument('-hb', '--hobl', action='store_true', help='if the data is collected via HOBL, looking for .PASS or .FAIL file in the folder to set file path as data set ID')

# parser.print_help()
args = parser.parse_args()
print("args: ", args)


socwatch_targets = [
    {"key": "CPU_model", "lookup": "CPU native model"},
    {"key": "PCH_SLP50", "lookup": "PCH SLP-S0 State Summary: Residency (Percentage and Time)"},
    {"key": "S0ix_Substate", "lookup": "S0ix Substate Summary: Residency (Percentage and Time)"},
    {"key": "PKG_Cstate", "lookup": "Platform Monitoring Technology CPU Package C-States Residency Summary: Residency (Percentage and Time)"},
    {"key": "Core_Cstate", "lookup": "Core C-State Summary: Residency (Percentage and Time)"},
    {"key": "Core_Concurrency", "lookup": "CPU Core Concurrency (OS)"},
    {"key": "ACPI_Cstate", "lookup": "Core C-State (OS) Summary: Residency (Percentage and Time)"},
    {"key": "OS_wakeups", "lookup": "Processes by Platform Busy Duration"},
    {"key": "CPU-iGPU", "lookup": "CPU-iGPU Concurrency Summary: Residency (Percentage and Time)"},
    {"key": "CPU_Pavr", "lookup": "CPU P-State Average Frequency (excluding CPU idle time)"},
    {"key": "CPU_Pstate", "lookup": "CPU P-State/Frequency Summary: Residency (Percentage and Time)"},
    {"key": "RC_Cstate", "lookup": "Integrated Graphics C-State  Summary: Residency (Percentage and Time)"},
    {"key": "DDR_BW", "lookup": "DDR Bandwidth Requests by Component Summary: Average Rate and Total"},
    {"key": "IO_BW", "lookup": "IO Bandwidth Summary: Average Rate and Total"},
    {"key": "VC1_BW", "lookup": "Display VC1 Bandwidth Summary: Average Rate and Total"},
    {"key": "NPU_BW", "lookup": "Neural Processing Unit (NPU) to Memory Bandwidth Summary: Average Rate and Total"},
    {"key": "Media_BW", "lookup": "Media to Network on Chip (NoC) Bandwidth Summary: Average Rate and Total"},
    {"key": "IPU_BW", "lookup": "Image Processing Unit (IPU) to Network on Chip (NoC) Bandwidth Summary: Average Rate and Total"},
    {"key": "CCE_BW", "lookup": "CCE to Network on Chip (NoC) Bandwidth Summary: Average Rate and Total"},
    {"key": "GT_BW", "lookup": "Chip GT Bandwidth Summary: Average Rate and Total"},
    {"key": "D2D_BW", "lookup": "Chip Die to Die Bandwidth Summary: Average Rate and Total"},
    {"key": "CPU_temp", "lookup": "Temperature Metrics Summary - Sampled: Min/Max/Avg"},
    {"key": "SoC_temp", "lookup": "SoC Domain Temperatures Summary - Sampled: Min/Max/Avg"},
    {"key": "NPU_Dstate", "lookup": "Neural Processing Unit (NPU) D-State Residency Summary: Residency (Percentage and Time)"},
    {"key": "PMC+SLP_S0", "lookup": "PCH Active State (as percentage of PMC Active plus SLP_S0 Time) Summary: Residency (Percentage)"},
    {"key": "DC_count", "lookup": "Dynamic Display State Enabling"},
    {"key": "Media_Cstate", "lookup": "Media C-State Residency Summary: Residency (Percentage and Time)"},
    {"key": "NPU_Pstate", "lookup": "Neural Processing Unit (NPU) P-State Summary - Sampled: Approximated Residency (Percentage)", "buckets":["0", "1900", "1901-2900", "2901-3899", "3900"]},
    {"key": "MEMSS_Pstate", "lookup": "Memory Subsystem (MEMSS) P-State Summary - Sampled: Approximated Residency (Percentage)"},
    {"key": "NoC_Pstate", "lookup": "Network on Chip (NoC) P-State Summary - Sampled: Approximated Residency (Percentage)", "buckets":["400", "401-1049", "1050"]},
    {"key": "iGFX_Pstate", "lookup": "Integrated Graphics P-State/Frequency Summary - Sampled: Approximated Residency (Percentage)", "buckets":["0-399","400-650", "651-1299", "1300-1849", "1850-2050"]}
]

PCIe_targets = [
    {"key": "PCIe_LPM", "devices":["NVM"], "lookup": "PCIe LPM Summary - Sampled: Approximated Residency (Percentage)"},
    {"key": "PCIe_Active", "devices":["NVM"], "lookup": "PCIe Link Active Summary - Sampled: Approximated Residency (Percentage)"},
    {"key": "PCIe_LTRsnoop", "devices":["NVM"], "lookup": "PCIe LTR Snoop Summary - Sampled: Histogram"}
]

SYNC_targets = {
    "host_log_target": "DEBUG call_rpc:45  sending RPC:",
    "dut_log_target": "DEBUG Received json:",
    "scenario_start_target":"Executing - Scenario:",
    "scenario_end_target":"Completed - Scenario:",
    "DAQ_start_target": "Record phase time: DAQ start time",
    "DAQ_stop_target": "Record phase time: DAQ stop time",
    "DAQ_timestamp_mark": "INFO"
}

DAQ_target = {
"P_SSD":-1,
"V_VAL_VCC_PCORE":-1,
"I_VAL_VCC_PCORE":-1,
"V_VAL_VCC_ECORE":-1,
"I_VAL_VCC_ECORE":-1,
"V_VAL_VCCSA":-1,
"I_VAL_VCCSA":-1,
"V_VAL_VCCGT":-1,
"I_VAL_VCCGT":-1,
"P_VCC_PCORE":-1,
"P_VCC_ECORE":-1,
"P_VCCSA":-1,
"P_VCCGT":-1,
"P_VCCL2":-1,
"P_VCC1P8":-1,
"P_VCCIO":-1,
"P_VCCDDRIO":-1,
"P_VNNAON":-1,
"P_VNNAONLV":-1,
"P_VDDQ":-1,
"P_VDD2H":-1,
"P_VDD2L":-1,
"P_V1P8U_MEM":-1,
"P_SOC+MEMORY":-1,
"Run Time":-1
}

CL_UNCLASSIFIED = "unclassified"
CL_ETL = ".etl"
CL_SOCWATCH = 'Session.etl'
CL_DAQ_SUMMARY = 'pacs-summary.csv'
CL_DAQ_TRACES = 'pacs-traces'
CL_HOBL = "hobl.log"
CL_SIMPLE_REMOTE = "simple_remote_"
CL_CATA_OUTPUT = 'CataV3_output.txt'
CL_PASS = ".PASS"
CL_FAIL = ".FAIL"

ETL = "ETL"
POWER = "POWER"
SOCWATCH = "SOCWATCH"
PCIE = "PCIE"
MIN = "MIN"
MAX = "MAX"
MED = "MED"

second_folder_list = [ETL, POWER, SOCWATCH, PCIE]

collection = args.input
result_path = args.output


if args.input is None:
    print("============== No input")
else :
    with open(args.input, 'r') as f:
        collection = json.load(f)
        print(collection)

if args.daq is None:
    print("============== No external DAQ.json provided")
else :
    with open(args.daq, 'r') as f:
        DAQ_target = json.load(f)
        print(DAQ_target)

if args.swtarget is None:
    print("============== No external Socwatch_target.json provided")
else :
    with open(args.swtarget, 'r') as f:
        socwatch_targets = json.load(f)
        print(socwatch_targets)
        
if result_path == None : 
    result_path = f"{tools.splitLastItem(collection, "\\", -1)[0]}\\CataV3_full_summary"


picks = {'power_pick':MED, 'inferencingOnlyPower':False, 'sortSimilarData':False}



hobl_sets = list()

file_num = 0





def getDatasetLabel(abs_path) :
    folder_list = abs_path.split("\\")
    folder_structure_detector = abs_path.split("\\")[:-1]
    last_folder = folder_structure_detector[-1]
    sl_upper = last_folder.upper()
    if sl_upper in second_folder_list:
        return [folder_list[-3], folder_list[-2]]
    else :
        return [folder_list[-2], folder_list[-1]]

def createDataset(abs_path) :
    # print("[abs_path] ", abs_path)
    hobl_sets.append({
        "ID_path":abs_path,
        "data_label":getDatasetLabel(abs_path),
        "data_type":[]
    })

def pullData(abs_path) :
    for item in hobl_sets:
        if (abs_path.find(item["ID_path"]) == 0) : 
            return item
    return None

def add_etl(abs_path):
    path_set = tools.splitLastItem(abs_path, "\\", 1)
    dataset = pullData(path_set[0])
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + abs_path)
    if ETL not in dataset["data_type"] :
        dataset["data_type"].insert(0, ETL)
    dataset["etl_obj"] = etl.parseETL(abs_path, collection)
    # if "host_dut_sync_obj" in dataset and "CataV3_data" in dataset["host_dut_sync_obj"] :
    #     sliced_list = eps.slice_power_ETL(dataset, collection)
    global file_num
    file_num += 1

def add_power(abs_path):
    path_set = tools.splitLastItem(abs_path, "\\", 1)
    dataset = pullData(path_set[0])
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + abs_path)
    if POWER not in dataset["data_type"] :
        dataset["data_type"].append(POWER)
    dataset["power_obj"] = psp.parsePowerSummaryCSV(abs_path, DAQ_target)
    # calFromPowerModel(dataset)
    global file_num
    file_num += 1

def add_trace(abs_path):
    path_set = tools.splitLastItem(abs_path, "\\", 1)
    dataset = pullData(path_set[0])
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + abs_path)
    dataset["trace_obj"] = ptp.parsePowerTraceCSV(abs_path)

    if "host_dut_sync_obj" in dataset:    
        dataset["host_dut_sync_obj"] = stp.parseLogs(dataset["host_dut_sync_obj"], SYNC_targets, dataset['trace_obj'])
    
    global file_num
    file_num += 1

def add_socwatch(abs_path, osSession_etl_path):
    path_set = tools.splitLastItem(abs_path, "\\", 1)
    dataset = pullData(path_set[0])
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + abs_path)
    if SOCWATCH not in dataset["data_type"] :
        dataset["data_type"].insert(0, SOCWATCH)
    dataset["socwatch_obj"] = soc.parseSocwatch(abs_path, socwatch_targets)
    dataset["socwatch_obj"][""]
    global file_num
    file_num += 1

def add_pcie_only(abs_path):
    path_set = tools.splitLastItem(abs_path, "\\", 1)
    dataset = pullData(path_set[0])
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + abs_path)
    if PCIE not in dataset["data_type"] :
        dataset["data_type"].insert(0, PCIE)
    dataset["pcie_socwatch_obj"] = psoc.parsePCIe(abs_path, PCIe_targets)
    global file_num
    file_num += 1

def sync_times(tdic):
    path_set = tools.splitLastItem(tdic["dut_log"], "\\", 1)
    dataset = pullData(path_set[0])
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + tdic)
    
    if "trace_obj" in dataset:
        dataset["host_dut_sync_obj"] = stp.parseLogs(tdic, SYNC_targets, dataset['trace_obj'])
    else :
        dataset["host_dut_sync_obj"] = tdic.copy()
    if "etl_obj" in dataset and "etl_data" in dataset["etl_obj"] :  
        sliced_list = eps.slice_power_ETL(dataset, collection)
    global file_num
    file_num += 3




def fileClassifier(abs_path, f):

    file_type = CL_UNCLASSIFIED
    
    if args.hobl == True and (f == CL_PASS or f == CL_FAIL):
        createDataset(tools.splitLastItem(abs_path, "\\", 1)[0])
    elif f.find(CL_SIMPLE_REMOTE) >= 0 :
        upto_path = tools.splitLastItem(abs_path, "\\", 1)[0]
        hobl_log_fullPath = os.path.join(upto_path, "hobl.log")
        CataV3_output_fullPath = os.path.join(upto_path, "CataV3_output.txt")
        if os.path.exists(hobl_log_fullPath) and os.path.exists(CataV3_output_fullPath):
            sync_times({"host_log":hobl_log_fullPath, "dut_log":abs_path, "catapult_output":CataV3_output_fullPath})
        else :
            print("==== Missing log files to sync HOST and DUT")
    elif f.find(CL_ETL) >= 0 and f.find(CL_SOCWATCH) == -1 : 
        # print("ETL detected ", abs_path, f)
        add_etl(abs_path)
        file_type = CL_ETL
    elif f.find(CL_DAQ_SUMMARY) >= 0:
        add_power(abs_path)
        file_type = CL_DAQ_SUMMARY
    elif f.find(CL_DAQ_TRACES) >= 0 and f.find('sr.csv') >= 0:
        add_trace(abs_path)
        file_type = CL_DAQ_TRACES
    elif f.find(CL_SOCWATCH) >= 0:
        workload_name = tools.splitLastItem(f, "_", 1)[0]
        upto_path = tools.splitLastItem(abs_path, "\\", 1)[0]
        soc_summary = workload_name + ".csv"
        summary_fullPath = os.path.join(upto_path, soc_summary)
        osSession_fullPath = os.path.join(upto_path, workload_name+"_osSession.etl")
        if os.path.exists(summary_fullPath) and os.path.exists(osSession_fullPath):
            add_socwatch(summary_fullPath, osSession_fullPath)
            file_type = CL_SOCWATCH
        elif os.path.exists(summary_fullPath) and not os.path.exists(osSession_fullPath):
            add_pcie_only(summary_fullPath)
            file_type = CL_SOCWATCH
        else :
            print("===== No Socwatch summary, Socwatch post-process may have interrupted or socwatch summary file name has altered", abs_path)
    return file_type


def detectAndParseFile(path) :

    # listdir gives back all file system list, including file and folder
    for f in os.listdir(path):
        abs_path = os.path.join(path, f)
        # if f == "Model_A3_v1_2_3_qdq_proxy_stripped":
        #     break
        if os.path.isfile(abs_path):
            fType = fileClassifier(abs_path, f)
            if fType == CL_SOCWATCH :
                # after detecting first Socwatch ETL, and it's summary, no need to go further
                break
        else :
            # only creates data set if not collected through HOBL. 
            if args.hobl == None or args.hobl == False:
                path_sliced = tools.splitLastItem(abs_path, "\\", 1)
                last_folder = path_sliced[1].upper()
                if last_folder not in second_folder_list and (pullData(abs_path) == None) :
                    createDataset(abs_path)
            #recursive on a folder detection
            detectAndParseFile(abs_path)



def main():
    detectAndParseFile(collection["selected_etl_folder"])
    detectAndParseFile(collection["selected_power_folder"])
    detectAndParseFile(collection["selected_socwatch_folder"])
    detectAndParseFile(collection["selected_PCIe_folder"])

    print("====[hobl_sets]", hobl_sets)
    # rpt.writeParsedSelectionInExcel(result_path, hobl_sets, picks, socwatch_targets, PCIe_targets)


start_time = time.perf_counter()
main()
end_time = time.perf_counter()
elapsed_time = end_time - start_time
print(f"Parsing {file_num} files Successful! [Elapsed time:::] {elapsed_time} seconds")




