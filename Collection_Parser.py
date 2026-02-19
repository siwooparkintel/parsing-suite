import time
import json
import os
from os import listdir
from os.path import isfile, join
from pathlib import Path
import parsers.tools as tools
import parsers.pcie_socwatch_summary_parser as psoc
import parsers.socwatch_summary_parser as soc
import parsers.power_summary_parser as psp
import parsers.power_trace_parser as ptp
import parsers.power_checker as pck
import parsers.reporter as rpt


import argparse

parser = argparse.ArgumentParser(prog='Collection Parser V1.0')
parser.add_argument('-c', '--config', help='configuration path. json format, need to have all of -d -st and others')
parser.add_argument('-i', '--input', help='input path. this will be the bese of the summray, will detect all files and folders from that path tree')
parser.add_argument('-o', '--output', help='output path. location of file and file name')
parser.add_argument('-d', '--daq', help='DAQ power rail name dictionary')
parser.add_argument('-st', '--swtarget', help='a list of dictionary objects that you want to parse from the socwatch summary')
# parser.add_argument('-hb', '--hobl', action='store_true', help='if the data is collected via HOBL, looking for .PASS or .FAIL file in the folder to set file path as data set ID')

args = parser.parse_args()
print("args: ", args)

CL_UNCLASSIFIED = "unclassified"
CL_ETL = ".etl"
CL_OUTPUT = '_output.txt'
CL_SOCWATCH = 'Session.etl'
CL_AI_MODEL = '_qdq_proxy_'
CL_DAQ_SUMMARY = 'pacs-summary.csv'
CL_DAQ_TRACES = 'pacs-traces'
CL_PASS = ".PASS"

ETL = "ETL"
POWER = "POWER"
SOCWATCH = "SOCWATCH"
MODEL_OUTPUT = "MODEL_OUTPUT"
MIN = "MIN"
MAX = "MAX"
MED = "MED"

BASE = args.input
result_path = args.output
# Get script directory for relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


hobl_sets = list()
picks = {
        "SOC_POWER_RAIL_NAME":'', "PCORE_POWER_RAIL_NAME":'', "SA_POWER_RAIL_NAME":'', "GT_POWER_RAIL_NAME":'', 
        'power_pick':MED,
        'inferencingOnlyPower':True, 
        'sortSimilarData':True,
        'inferencing_power_detection':{
            'power_obj':{'power_type':'SOCWATCH_ETL_POWER'},
            'model_output_obj':{'model_output_status':'successful'}
            }
        }

config_json = dict()

if args.config is None:
    print("============== No external default config JSON provided")
    config_json = tools.jsonLoader(f"{SCRIPT_DIR}\\config\\LNL_default.config", picks)
else :
    config_json = tools.jsonLoader(args.config, picks)
    print(config_json)

socwatch_targets = config_json["socwatch_targets"]
PCIe_targets = config_json["PCIe_targets"]
DAQ_target = config_json["DAQ_target"]
second_folder_list = config_json["Second_folder_list"]
loaded_file_num = 0


# path_splitter = "\\"

# def replaceSplitter(Abs_path) :
#     Abs_path = Abs_path.replace("/", "\\")
#     return Abs_path

# if BASE is None:
#     from tools.tk_dialogs import select_folder_dialog

#     folder_path = select_folder_dialog(
#         title="Select a folder",
#         storage_name="last_opened_folder",
#         base_dir=Path(SCRIPT_DIR),
#     )
#     if folder_path:
#         BASE = replaceSplitter(folder_path)
#         print(f"Selected folder: {BASE}")
#     else:
#         tools.errorAndExit("No folder selected")

collection = [
    {
        "data_label":"Llama 8B GPU 512 token gen",
        "condition":"Baseline DDR8533",
        "data_summary_type": "compact",
        "power_summary_path":r"\\amr.corp.intel.com\EC\proj\pst\jf\SPA-Lab\Siwoo\CatapultV3\WW20.2_LNL32_CataV3_PC10.2\PC10.2_UHX\web_cataV3_si_001_ppick\web_cataV3_si_001\web_cataV3_si_001_pacs-summary.csv",
        "socwatch_summary_path":r"\\amr.corp.intel.com\EC\proj\pst\jf\SPA-Lab\Siwoo\CatapultV3\WW20.2_LNL32_CataV3_PC10.2\PC10.2_UHX\web_cataV3_si_008_spick\socwatch\PC10.2_UHX_web_cataV3_si.csv",
        "PCIe_socwatch_summary_path":r"\\amr.corp.intel.com\EC\proj\pst\jf\SPA-Lab\Siwoo\CatapultV3\WW20.2_LNL32_CataV3_PC10.2\PCIe_only_Socwatch\UHX_baseline\web_cataV3_si_002_pick\socwatch\web_cataV3_si_CataV3_UHX.csv"
    },    
    {
        "data_label":"Llama 8B GPU 512 token gen",
        "condition":"TME DDR8533",
        "data_summary_type": "compact",
        "power_summary_path":r"\\amr.corp.intel.com\EC\proj\pst\jf\SPA-Lab\Siwoo\CatapultV3\WW20.2_LNL32_CataV3_PC10.2\PC10.2_UHX_LCLT\web_cataV3_si_006_ppick\web_cataV3_si_006\web_cataV3_si_006_pacs-summary.csv",
        "socwatch_summary_path":r"\\amr.corp.intel.com\EC\proj\pst\jf\SPA-Lab\Siwoo\CatapultV3\WW20.2_LNL32_CataV3_PC10.2\PC10.2_UHX_LCLT\web_cataV3_si_000_spick\socwatch\PC10.2_UHX_LCLT_web_cataV3_si.csv",
        "PCIe_socwatch_summary_path":r"\\amr.corp.intel.com\EC\proj\pst\jf\SPA-Lab\Siwoo\CatapultV3\WW20.2_LNL32_CataV3_PC10.2\PCIe_only_Socwatch\UHX_LCLT\web_cataV3_si_000_pick\socwatch\web_cataV3_si_CataV3_UXH_LCLT.csv"
    },
]


#=============================================================================
# place this same order of the socwatch summary for ultimate performance
# in that case, it only looping thru one time of socwatch summary file.
# if you are not matching the data table order, it will do the loop from the beginning
#=============================================================================






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
    result_path = f"{BASE}\\collection_summary"





    
#=========================================================================
# this returns parent or parent*2 folder name string as a data_set name
# if ETL, Power, Socwatch folder separation structure,
# it returns grand parent folder name
#=========================================================================
def getDatasetLabel(abs_path) :
    folder_list = abs_path.split("\\")[:-1]
    last = folder_list[-1]
    last_lower = last.lower()
    if last_lower == 'etl' or last_lower == 'power' or last_lower == 'socwatch':
        return [folder_list[-3], folder_list[-2]]
    else :
        return [folder_list[-2], folder_list[-1]]

def createDataset(tdic) :
    hobl_sets.append({
        "data_label":tdic["data_label"],
        "condition":tdic["condition"],
        "data_summary_type": tdic['data_summary_type'],
        "data_type":[]
    })

def pullData(ID) :
    for item in hobl_sets:
        if (item["condition"] == ID) : 
            return item
    return None

def add_etl(tdic):
    ID = tdic['condition']
    dataset = pullData(ID)
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + ID)
    if ETL not in dataset["data_type"] :
        dataset["data_type"].insert(0, ETL)
    dataset["etl_path"] = tdic['power_summary_path']

def add_power(tdic):
    ID = tdic['condition']
    dataset = pullData(ID)
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + ID)
    if POWER not in dataset["data_type"] :
        dataset["data_type"].append(POWER)
    dataset["power_obj"] = psp.parsePowerSummaryCSV(tdic['power_summary_path'], DAQ_target)

    global loaded_file_num
    loaded_file_num += 1

def add_trace(tdic):
    ID = tdic['condition']
    dataset = pullData(ID)
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + ID)
    dataset["trace_obj"] = ptp.parsePowerTraceCSV(tdic['trace_path'])
    global loaded_file_num
    loaded_file_num += 1

def add_socwatch(tdic):
    ID = tdic['condition']
    dataset = pullData(ID)
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + ID)
    if SOCWATCH not in dataset["data_type"] :
        dataset["data_type"].insert(0, SOCWATCH)
    dataset["socwatch_obj"] = soc.parseSocwatch(tdic, socwatch_targets)
    global loaded_file_num
    loaded_file_num += 1

def add_pcie_only(tdic):
    ID = tdic['condition']
    dataset = pullData(ID)
    if dataset == None:
        tools.errorAndExit("pulling data failed by using the Path as ID: " + ID)
    dataset["pcie_socwatch_obj"] = psoc.parsePCIe(tdic, PCIe_targets)
    global loaded_file_num
    loaded_file_num += 1


def fileClassifier(abs_path, f):

    file_type = CL_UNCLASSIFIED
    
    if f == CL_PASS :
        createDataset(tools.splitLastItem(abs_path, "\\", 1)[0])
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
        if os.path.exists(summary_fullPath) :
            add_socwatch(summary_fullPath)
        else :
            print("===== No Socwatch summary, Socwatch post-process may have interrupted", abs_path)
        file_type = CL_SOCWATCH
    return file_type


def detectAndParseFile(file_list) :

    for tdic in file_list:
        if "condition" in tdic:
            # print(tdic["data_label"])
            createDataset(tdic)
        if "power_summary_path" in tdic:
            # print(tdic["power_summary_path"])
            add_power(tdic)
        if "socwatch_summary_path" in tdic:
            # print(tdic["socwatch_summary_path"])
            add_socwatch(tdic)
        if "PCIe_socwatch_summary_path" in tdic:
            # print("PCIe parser")
            add_pcie_only(tdic)

def main():

    detectAndParseFile(collection)
    # pck.checkAndMarkPower(hobl_sets, picks)
    # if (picks["inferencing_power"] is True) : 
    # ptp.averageInferencingPower(hobl_sets, DAQ_target)
    # ===========================================================================
    # print processed(fully parsed) data to check the dictionary (Object) structure
    # since it is keep improving, changing
    # ===========================================================================
    print("====[hobl_sets]", hobl_sets)
    rpt.writeParsedSelectionInExcel(result_path, hobl_sets, picks, socwatch_targets, PCIe_targets)


start_time = time.perf_counter()
main()
end_time = time.perf_counter()
elapsed_time = end_time - start_time
print(f"Parsing {loaded_file_num} files Successful! [Elapsed time:::] {elapsed_time} seconds")




