import re
import sys
import os
import json
import numpy as np
import parsers.tools as tools


header_collection = dict()



def getPickedType(picks) :
    return picks['power_pick']+"_picked"

def getMSmodelKeyUnit(key, value_list) :
    return key+f" ({value_list[1]})" if value_list[1] != "" else key

def getSocwatchHeader(key, label) :
    return f"{key}        {label}"

def find_dict_by_key_value(data, key, value):
    for item in data:
        if item.get(key) == value:
            return item
    return None

def get_rest_cpu_pstate(rest_dic_list, key, rest_cpu_p_residency_list):
    if len(rest_dic_list) == 0:
        for item in rest_cpu_p_residency_list :
            tdic = dict()
            tdic[key] = tools.tryRoundifNumber(item) # round(float(item), 2)
            rest_dic_list.append(tdic)
    else :
        for idx in range(len(rest_dic_list)) :
            tdic = rest_dic_list[idx]
            if key is not tdic:
                tdic[key] = tools.tryRoundifNumber(rest_cpu_p_residency_list[idx]) # round(float(rest_cpu_p_residency_list[idx]), 2)


def flatten_ETL_dic(entry) :
    
    if "etl_path" in entry :

        new_output = dict()
        new_output["etl_path"] = entry["etl_path"]
        ETL_header_updater(entry)
        return new_output
    else :
        return {}   
    

def flatten_AI_model_dic(entry) :
    
    if "model_output_obj" in entry and "model_output_data" in entry["model_output_obj"] :
        copied = entry["model_output_obj"]['model_output_data'].copy()
        new_output = dict()
        for index, key in enumerate(copied):
            value_list = copied[key]
            updated_key = getMSmodelKeyUnit(key, value_list)
            new_output[updated_key] = value_list[0]
        new_output['model_output_path'] = entry["model_output_obj"]["model_output_path"]
        AI_model_header_updater(entry["model_output_obj"])
        return new_output
    else :
        return {}
    
def flatten_fps_dic(entry) :
    
    if "fps_img_obj" in entry and "fps_data" in entry["fps_img_obj"] :
        copied = entry["fps_img_obj"]['fps_data'].copy()
        new_output = dict()
        for index, key in enumerate(copied):
            value_list = copied[key]
            # updated_key = key+f" ({value_list[1]})" if value_list[1] != "" else key
            new_output[key] = value_list
        new_output['Eng(J)/Frame'] = entry["power_obj"]["power_data"]["Energy (J)"] / copied["frames_rendered"] if "Energy (J)" in entry["power_obj"]["power_data"] and "frames_rendered" in copied and copied["frames_rendered"] != '' and copied["frames_rendered"] != 0 else ''
        new_output['fps_img_path'] = entry["fps_img_obj"]["fps_img_path"]
        return new_output
    else :
        return {}

def flatten_mlc_output_dic(entry) :
    
    if "mlc_output_obj" in entry and "mlc_output_data" in entry["mlc_output_obj"] :
        copied = entry["mlc_output_obj"]['mlc_output_data'].copy()
        new_output = dict()
        for index, key in enumerate(copied):
            value_list = copied[key]
            updated_key = key+f" ({value_list[1]})" if value_list[1] != "" else key
            new_output[updated_key] = value_list[0]
        new_output['mlc_output_path'] = entry["mlc_output_obj"]["mlc_output_path"]
        return new_output
    else :
        return {}
    
def flatten_teams_vpt_camera_dic(entry):
    if "vpt_output_obj" in entry and "vpt_output_data" in entry["vpt_output_obj"] :
        copied = entry["vpt_output_obj"].copy()
        new_output = dict()
        new_output['min_cam_fps'] = copied["min_cam_fps"]
        new_output['median_cam_fps'] = copied["median_cam_fps"]
        new_output['vpt_output_path'] = copied["vpt_output_path"]
        teams_vpt_header_updater(entry["vpt_output_obj"])
        return new_output
    else :
        return {}
    

def flatten_procyon_arielle_dic(entry):
    new_output = dict()

    if "procyon_arielle_obj" in entry and "procyon_arielle_data" in entry["procyon_arielle_obj"] :
        copied = entry["procyon_arielle_obj"]["procyon_arielle_data"].copy()

        for key in copied:
            new_output[key] = copied[key]

        new_output['procyon_arielle_path'] = entry["procyon_arielle_obj"]["procyon_arielle_path"]
        procyon_arielle_header_updater(entry["procyon_arielle_obj"])

    return new_output
            
def flatten_trace_dic(entry):
    if "trace_obj" in entry and "trace_data" in entry["trace_obj"] and entry["trace_obj"]["trace_data"] != None:
        copied = entry["trace_obj"]['trace_data'].copy()
        copied["total_row"] = entry['trace_obj']['total_row']
        copied["duration_in_scale"] = entry['trace_obj']['duration_in_scale']
        copied["inf_start"] = entry['trace_obj']['inf_start']
        copied["inf_end"] = entry['trace_obj']['inf_end']
        copied["Device"] = entry["trace_obj"]["Device"]
        copied["Token/s"] = entry["model_output_obj"]["model_output_data"]["throughput"][0] if "model_output_obj" in entry and "model_output_data" in entry["model_output_obj"] and "throughput" in entry["model_output_obj"]["model_output_data"] else None
        copied["file_path"] = entry['trace_obj']['file_path']
        return copied
    else :
        return {}
    
def flatten_pcie_socwatch_dic(entry, pcie_socwatch_targets):
    if "pcie_socwatch_obj" in entry and "pcie_socwatch_tables" in entry["pcie_socwatch_obj"] :
        flat_socwatch = {}
        for table in entry["pcie_socwatch_obj"]["pcie_socwatch_tables"]:
            # flat_socwatch.update(table["table_data"]) if "table_data" in table else {}

            data = table["table_data"]
            if "bucketized_data" in table:
                data = table["bucketized_data"]
            for item in data :
                # print(item, item+"_"+table["label"])
                flat_socwatch[getSocwatchHeader(item, table["label"])] = tools.tryRoundifNumber(data[item])
            # flat_socwatch[table]
        flat_socwatch['pcie_socwatch_path'] = entry['pcie_socwatch_obj']['pcie_socwatch_path']
        pcie_socwatch_header_updater(entry["pcie_socwatch_obj"])
        return flat_socwatch
    else :
        return {}
         
def flatten_socwatch_dic_per_core(entry, socwatch_targets):
    if "socwatch_obj" in entry and "socwatch_tables" in entry["socwatch_obj"] :
        flatten_list = []
        rest_cpu_pstate_list = []
        flat_socwatch = {}
        for table in entry["socwatch_obj"]["socwatch_tables"]:
            # flat_socwatch.update(table["table_data"]) if "table_data" in table else {}

            data = table["table_data"]
            if "bucketized_data" in table:
                data = table["bucketized_data"]
            for item in data :
                # print(item, item+"_"+table["label"])
                new_key = getSocwatchHeader(item, table["label"])
                if table["label"] == "CPU_Pstate":
                    flat_socwatch[new_key] = tools.tryRoundifNumber(data[item][0])
                    get_rest_cpu_pstate(rest_cpu_pstate_list, new_key, data[item][1:]) if isinstance(data[item], list) else None
                else :
                    flat_socwatch[new_key] = data[item]
            # flat_socwatch[table]
        flat_socwatch['socwatch_path'] = entry['socwatch_obj']['socwatch_path']
        flatten_list.append(flat_socwatch)
        flatten_list.extend(rest_cpu_pstate_list)
        
        return flatten_list
    else :
        return []

def flatten_socwatch_dic(entry, socwatch_targets):
    if "socwatch_obj" in entry and "socwatch_tables" in entry["socwatch_obj"] :
        flat_socwatch = {}
        for table in entry["socwatch_obj"]["socwatch_tables"]:
            # flat_socwatch.update(table["table_data"]) if "table_data" in table else {}

            data = table["table_data"]
            if "bucketized_data" in table:
                data = table["bucketized_data"]
            for item in data :
                # print(item, item+"_"+table["label"])
                flat_socwatch[getSocwatchHeader(item, table["label"])] = data[item]
            # flat_socwatch[table]
        flat_socwatch['socwatch_path'] = entry['socwatch_obj']['socwatch_path']
        socwatch_header_updater(entry["socwatch_obj"])
        return flat_socwatch
    else :
        return {}
    
def flatten_power_dic(entry, picks):
    if "power_obj" in entry and "power_data" in entry["power_obj"] :
        copied = entry["power_obj"]['power_data'].copy()
        copied["power_type"] = entry['power_obj']['power_type']
        copied[getPickedType(picks)] = entry['power_obj']['picked']
        copied["power_path"] = entry['power_obj']['power_path']
        power_header_updater(entry["power_obj"], picks)
        return copied
    else :
        return {}

def flatten_LPmode_sr_dic(entry):
    if "sr_output_obj" in entry and "sr_output_data" in entry["sr_output_obj"] and "NOP" in entry["sr_output_obj"]['sr_output_data'] and "Affinity" in entry["sr_output_obj"]['sr_output_data'] :
        copied = entry["sr_output_obj"]['sr_output_data'].copy()
        copied["NOP"] = entry["sr_output_obj"]['sr_output_data']["NOP"]
        copied["Affinity"] = entry["sr_output_obj"]['sr_output_data']["Affinity"]
        return copied
    else :
        return {}
        
def flatten_lpmode_full_dic(entry):
    if "lpmode_full_obj" in entry and "lpmode_full_data" in entry["lpmode_full_obj"] :
        copied = entry["lpmode_full_obj"]['lpmode_full_data'].copy()
        copied["lpmode_full_path"] = entry['lpmode_full_obj']['lpmode_full_path']
        lpmode_full_header_updater(entry["lpmode_full_obj"])
        return copied
    else :
        return {}

    
def power_header_updater(parsed_obj, picks):
    if "power" not in header_collection :
        header_collection["power"] = dict()
    for item in parsed_obj :

        if item == "power_data":
            if "power_data_key" not in header_collection["power"] :
                header_collection["power"]["power_data_key"] = list(parsed_obj[item].keys())
            else :
                existing_keys = header_collection["power"]["power_data_key"]
                new_keys = parsed_obj[item].keys()
                combined = list(dict.fromkeys(list(new_keys) + list(existing_keys)))  # Combine and remove duplicates while preserving order
                header_collection["power"]["power_data_key"] = combined
    
    if "power_type" not in header_collection["power"] and "power_type" in parsed_obj :
        header_collection["power"]["power_type"] = ""
    if "picked" not in header_collection["power"]  and "picked" in parsed_obj : 
        header_collection["power"][getPickedType(picks)] = ""
    if "power_path" not in header_collection["power"] and "power_path" in parsed_obj :
        header_collection["power"]["power_path"] = ""

def ETL_header_updater(parsed_obj):
    if "ETL" not in header_collection :
        header_collection["ETL"] = dict()

    if "etl_path" not in header_collection["ETL"] and "etl_path" in parsed_obj :
        header_collection["ETL"]["etl_path"] = ""   

def socwatch_header_updater(parsed_obj):
    if "socwatch" not in header_collection :
        header_collection["socwatch"] = dict()
    for table in parsed_obj["socwatch_tables"] :
        if "bucketized_data" in table :
            new_keys = [getSocwatchHeader(key, table["label"]) for key in table["bucketized_data"].keys()]
        else :
            new_keys = [getSocwatchHeader(key, table["label"]) for key in table["table_data"].keys()]

        if table["label"] not in header_collection["socwatch"] :
            header_collection["socwatch"][table["label"]] = new_keys
        else :
            existing_keys = header_collection["socwatch"][table["label"]]
            combined = list(dict.fromkeys(new_keys + existing_keys))  # Combine and remove duplicates while preserving order
            header_collection["socwatch"][table["label"]] = combined
    if "socwatch_path" in parsed_obj and "socwatch_path" not in header_collection["socwatch"] :
        header_collection["socwatch"]["socwatch_path"] = ""

def pcie_socwatch_header_updater(parsed_obj):
    if "PCIe_socwatch" not in header_collection :
        header_collection["PCIe_socwatch"] = dict()
    for table in parsed_obj["pcie_socwatch_tables"] :

        new_keys = [getSocwatchHeader(key, table["label"]) for key in table["table_data"].keys()]

        if table["label"] not in header_collection["PCIe_socwatch"] :
            header_collection["PCIe_socwatch"][table["label"]] = new_keys
        else :
            existing_keys = header_collection["PCIe_socwatch"][table["label"]]
            combined = list(dict.fromkeys(new_keys + existing_keys))  # Combine and remove duplicates while preserving order
            header_collection["PCIe_socwatch"][table["label"]] = combined
    if "pcie_socwatch_path" in parsed_obj and "pcie_socwatch_path" not in header_collection["PCIe_socwatch"] :
        header_collection["PCIe_socwatch"]["pcie_socwatch_path"] = ""

def procyon_arielle_header_updater(parsed_obj):
    if "procyon_arielle" not in header_collection :
        header_collection["procyon_arielle"] = dict()
    for key in parsed_obj["procyon_arielle_data"].keys() :
        if key not in header_collection["procyon_arielle"] :
            header_collection["procyon_arielle"][key] = ""
    if "procyon_arielle_path" in parsed_obj and "procyon_arielle_path" not in header_collection["procyon_arielle"] :
        header_collection["procyon_arielle"]["procyon_arielle_path"] = ""

def teams_vpt_header_updater(parsed_obj):
    if "teams_vpt" not in header_collection :
        header_collection["teams_vpt"] = dict()
    if "vpt_output_data" in parsed_obj and "min_cam_fps" in parsed_obj and "min_cam_fps" not in header_collection["teams_vpt"] :
        header_collection["teams_vpt"]["min_cam_fps"] = ""
    if "vpt_output_data" in parsed_obj and "median_cam_fps" in parsed_obj and "median_cam_fps" not in header_collection["teams_vpt"] :
        header_collection["teams_vpt"]["median_cam_fps"] = ""
    if "vpt_output_path" in parsed_obj and "vpt_output_path" not in header_collection["teams_vpt"] :
        header_collection["teams_vpt"]["vpt_output_path"] = ""

def AI_model_header_updater(parsed_obj):
    if "AI_model" not in header_collection :
        header_collection["AI_model"] = dict()
    if "model_output_data" in parsed_obj :
        if "model_data_key" not in header_collection["AI_model"] :
            header_collection["AI_model"]["model_data_key"] = [getMSmodelKeyUnit(key, parsed_obj["model_output_data"][key]) for key in parsed_obj["model_output_data"].keys()]
        else :
            existing_keys = header_collection["AI_model"]["model_data_key"]
            # new_keys = parsed_obj["model_output_data"].keys()
            new_keys = [getMSmodelKeyUnit(key, parsed_obj["model_output_data"][key]) for key in parsed_obj["model_output_data"].keys()]
            combined = list(dict.fromkeys(list(new_keys) + list(existing_keys)))  # Combine and remove duplicates while preserving order
            header_collection["AI_model"]["model_data_key"] = combined
    if "model_output_path" in parsed_obj and "model_output_path" not in header_collection["AI_model"] :
        header_collection["AI_model"]["model_output_path"] = ""
    
def lpmode_full_header_updater(parsed_obj):
    if "lpmode_full" not in header_collection :
        header_collection["lpmode_full"] = dict()
    if "lpmode_full_data" in parsed_obj :
        for key in parsed_obj["lpmode_full_data"].keys() :
            if key not in header_collection["lpmode_full"] :
                header_collection["lpmode_full"][key] = ""
    if "lpmode_full_path" in parsed_obj and "lpmode_full_path" not in header_collection["lpmode_full"] :
        header_collection["lpmode_full"]["lpmode_full_path"] = ""

def get_AI_model_list(AI_model_header_dict) :
    model_header  = list()
    for model_key in AI_model_header_dict["model_data_key"] :
        if model_key == "model_data_key":
            model_header.extend(AI_model_header_dict[model_key])
        else :
            model_header.append(model_key)
    model_header.append("model_output_path") if "model_output_path" in AI_model_header_dict else None
    return model_header

def get_power_header_list(power_header_dict) :
    power_header  = list()
    for power_key in power_header_dict:
        if power_key == "power_data_key" :
            power_header.extend(power_header_dict[power_key])
        else :
            power_header.append(power_key)
    
    return power_header

def get_ETL_header_list(ETL_header_dict) :
    ETL_header  = list()
    for ETL_key in ETL_header_dict:
        ETL_header.append(ETL_key)
    return ETL_header

def get_socwatch_header_list(socwatch_header_dict) :
    socwatch_header  = list()
    for table_label in socwatch_header_dict:
        if table_label != "socwatch_path" :
            socwatch_header.extend(socwatch_header_dict[table_label])
    socwatch_header.append("socwatch_path") if "socwatch_path" in socwatch_header_dict else None
    return socwatch_header

def get_pcie_socwatch_header_list(PCIe_socwatch_header_dict) :
    PCIe_socwatch_header  = list()
    for table_label in PCIe_socwatch_header_dict:
        if table_label != "pcie_socwatch_path" :
            PCIe_socwatch_header.extend(PCIe_socwatch_header_dict[table_label])
    PCIe_socwatch_header.append("pcie_socwatch_path") if "pcie_socwatch_path" in PCIe_socwatch_header_dict else None
    return PCIe_socwatch_header

def get_procyon_score_header_list() :
    return ["procyon_overall_score", "procyon_score_path"]

def get_procyon_arielle_header_list(procyon_header_dict) :
    procyon_arielle_header  = list()
    for procyon_item in procyon_header_dict:
        if  procyon_item != "procyon_arielle_path" :
            procyon_arielle_header.append(procyon_item)
    procyon_arielle_header.append("procyon_arielle_path") if "procyon_arielle_path" in procyon_header_dict else None
    return procyon_arielle_header

def get_teams_vpt_camera_list(teams_vpt_camera_header_dict) :
    teams_vpt_header  = list()
    for teams_vpt_item in teams_vpt_camera_header_dict:
        teams_vpt_header.append(teams_vpt_item)
    return teams_vpt_header

def get_lpmode_full_header_list(lpmode_header_dict) :
    lpmode_full_header  = list()
    for lpmode_item in lpmode_header_dict:
        lpmode_full_header.append(lpmode_item)
    return lpmode_full_header

def getHeaderCollection():
    # this dictates the column order in the final excel, so the order of appending matters
    flatten_header = ["Data label", "Condition"]
    flatten_header.extend(get_power_header_list(header_collection["power"])) if "power" in header_collection else None
    flatten_header.append("Data Detected")
    flatten_header.extend(get_ETL_header_list(header_collection["ETL"])) if "ETL" in header_collection else None
    flatten_header.extend(get_AI_model_list(header_collection["AI_model"])) if "AI_model" in header_collection else None
    flatten_header.extend(get_lpmode_full_header_list(header_collection["lpmode_full"])) if "lpmode_full" in header_collection else None
    flatten_header.extend(get_teams_vpt_camera_list(header_collection["teams_vpt"])) if "teams_vpt" in header_collection else None
    flatten_header.extend(get_procyon_score_header_list())
    flatten_header.extend(get_socwatch_header_list(header_collection["socwatch"])) if "socwatch" in header_collection else None
    flatten_header.extend(get_pcie_socwatch_header_list(header_collection["PCIe_socwatch"])) if "PCIe_socwatch" in header_collection else None
    flatten_header.extend(get_procyon_arielle_header_list(header_collection["procyon_arielle"])) if "procyon_arielle" in header_collection else None
    return flatten_header




