import re
import sys
import os
import json
import numpy as np


header_collection = dict()


def tk_dialogs(
    dialog_type="open_file",
    title="Select a file",
    initial_dir=None,
    filetypes=None,
):
    """Small tkinter dialog helper for file/folder interactions.

    Supported dialog_type values:
    - open_file
    - open_folder
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    root = tk.Tk()
    root.withdraw()

    selected = None
    try:
        if dialog_type == "open_folder":
            selected = filedialog.askdirectory(
                title=title,
                initialdir=initial_dir,
            )
        else:
            selected = filedialog.askopenfilename(
                title=title,
                initialdir=initial_dir,
                filetypes=filetypes or [("All files", "*.*")],
            )
    finally:
        root.destroy()

    return selected if selected else None

def parseNumeric(text) :
    return ''.join(re.findall(r'[0-9.]', text))
def parseDevice(text) :
    return ''.join(re.findall(r'[A-Z.0-9]', text))

def getPickedType(picks) :
    return picks['power_pick']+"_picked"

def getMSmodelKeyUnit(key, value_list) :
    return key+f" ({value_list[1]})" if value_list[1] != "" else key

def getSocwatchHeader(key, label) :
    return f"{key}        {label}"

def tryRoundifNumber(value) :
    try :
        return round(float(value), 2)
    except ValueError as e:
        return value

def tryIntifNumber(value) :
    try :
        return int(value)
    except ValueError as e:
        return value
    
# add def saveLastOpenedFolder(folder_path):
def saveLastOpenedFolder(folder_path):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        last_folder_file = os.path.join(parent_dir, "config", "last_opened_folder.txt")
        with open(last_folder_file, "w") as f:
            f.write(folder_path)
    except Exception as e:
        print(f"Failed to save last opened folder: {e}")
    
def splitLastItem(abs_path, joint, cutNum) :
    item_list = abs_path.split(joint)
    return [joint.join(item_list[:-cutNum]), item_list[len(item_list)-1]]

def trim_list(data_list):
    """
    Removes empty items from the back of a list.
    An item is considered 'empty' if it evaluates to False (e.g., '', 0, None, [], {}).
    """
    while data_list and data_list[-1].strip() == "":  # Check if list is not empty and last element is falsy
        data_list.pop()
    return [item.strip() for item in data_list]

def find_dict_by_key_value(data, key, value):
    for item in data:
        if item.get(key) == value:
            return item
    return None

def get_rest_cpu_pstate(rest_dic_list, key, rest_cpu_p_residency_list):
    if len(rest_dic_list) == 0:
        for item in rest_cpu_p_residency_list :
            tdic = dict()
            tdic[key] = tryRoundifNumber(item) # round(float(item), 2)
            rest_dic_list.append(tdic)
    else :
        for idx in range(len(rest_dic_list)) :
            tdic = rest_dic_list[idx]
            if key is not tdic:
                tdic[key] = tryRoundifNumber(rest_cpu_p_residency_list[idx]) # round(float(rest_cpu_p_residency_list[idx]), 2)

def getSocPowerRailName(DAQ_target, picks):
    soc_power_rail_name = ""
    soc_list = ["P_SOC", "P_MCP", "P_SOC+MEMORY"]
    # for loop from the backward order of DAQ_target keys
    # check the possible soc power rail names if it contains "P_SOC", "P_MCP" or "P_SOC+MEMORY"
    # make this a list for future expansion
    # then assign the first found name to soc_power_rail_name   
    for key in reversed(list(DAQ_target.keys())):
        if key in soc_list:
            soc_power_rail_name = key
            break
    picks['SOC_POWER_RAIL_NAME'] = soc_power_rail_name


def flatten_MS_model_dic(entry) :
    
    if "model_output_obj" in entry and "model_output_data" in entry["model_output_obj"] :
        copied = entry["model_output_obj"]['model_output_data'].copy()
        new_output = dict()
        for index, key in enumerate(copied):
            value_list = copied[key]
            updated_key = getMSmodelKeyUnit(key, value_list)
            new_output[updated_key] = value_list[0]
        new_output['model_output_path'] = entry["model_output_obj"]["model_output_path"]
        MS_model_header_updater(entry["model_output_obj"])
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

def flatten_LPmode_sr_dic(entry):
    if "sr_output_obj" in entry and "sr_output_data" in entry["sr_output_obj"] and "NOP" in entry["sr_output_obj"]['sr_output_data'] and "Affinity" in entry["sr_output_obj"]['sr_output_data'] :
        copied = entry["sr_output_obj"]['sr_output_data'].copy()
        copied["NOP"] = entry["sr_output_obj"]['sr_output_data']["NOP"]
        copied["Affinity"] = entry["sr_output_obj"]['sr_output_data']["Affinity"]
        return copied
    else :
        return {}
    
def flatten_teams_vpt_camera_dic(entry):
    if "vpt_output_obj" in entry and "vpt_output_data" in entry["vpt_output_obj"] :
        copied = entry["vpt_output_obj"].copy()
        new_output = dict()
        new_output['min_cam_fps'] = copied["min_cam_fps"]
        new_output['median_cam_fps'] = copied["median_cam_fps"]
        new_output['vpt_output_path'] = copied["vpt_output_path"]
        return new_output
    else :
        return {}
    
def flatten_procyon_xml_dic(entry):
    if "procyon_result_obj" in entry and "procyon_data" in entry["procyon_result_obj"] :
        copied = entry["procyon_result_obj"]["procyon_data"].copy()
        new_output = dict()
        new_output['procyon_overall_score'] = copied["procyon_overall_score"]
        new_output['procyon_xml_path'] = entry["procyon_result_obj"]["procyon_xml_path"]
        procyon_header_updater(entry["procyon_result_obj"])
        return new_output
    else :
        return {}
    
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
                flat_socwatch[getSocwatchHeader(item, table["label"])] = tryRoundifNumber(data[item])
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
                    flat_socwatch[new_key] = tryRoundifNumber(data[item][0])
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
    

def get_median(values) :
    return np.median(values)
        
def errorAndExit(msgs) :
    print("=============================================================================")
    sys.exit("[Error] :: " + msgs)
    print("=============================================================================")

    
def jsonLoader(filename, picks) :

    try :
        with open(os.path.join(filename), 'r') as json_file:
            data = json.load(json_file)
            parsePowerRailNames(data["DAQ_target"], picks) if "DAQ_target" in data else None
            return data
    except Exception as e:
        errorAndExit(f"Failed to load JSON file: {e}")

def parsePowerRailNames(DAQ_target, picks):
    picks["SOC_POWER_RAIL_NAME"] = DAQ_target.get("SOC_POWER_RAIL_NAME")
    picks["PCORE_POWER_RAIL_NAME"] = DAQ_target.get("PCORE_POWER_RAIL_NAME")
    picks["SA_POWER_RAIL_NAME"] = DAQ_target.get("SA_POWER_RAIL_NAME")
    picks["GT_POWER_RAIL_NAME"] = DAQ_target.get("GT_POWER_RAIL_NAME")
    print("============================= ", picks)

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

def procyon_header_updater(parsed_obj):
    if "procyon" not in header_collection :
        header_collection["procyon"] = dict()
    if "procyon_data" in parsed_obj and "procyon_overall_score" in parsed_obj["procyon_data"] and "procyon_overall_score" not in header_collection["procyon"] :
        header_collection["procyon"]["procyon_overall_score"] = ""
    if "procyon_xml_path" in parsed_obj and "procyon_xml_path" not in header_collection["procyon"] :
        header_collection["procyon"]["procyon_xml_path"] = ""

def MS_model_header_updater(parsed_obj):
    if "MS_model" not in header_collection :
        header_collection["MS_model"] = dict()
    if "model_output_data" in parsed_obj :
        if "model_data_key" not in header_collection["MS_model"] :
            header_collection["MS_model"]["model_data_key"] = [getMSmodelKeyUnit(key, parsed_obj["model_output_data"][key]) for key in parsed_obj["model_output_data"].keys()]
        else :
            existing_keys = header_collection["MS_model"]["model_data_key"]
            # new_keys = parsed_obj["model_output_data"].keys()
            new_keys = [getMSmodelKeyUnit(key, parsed_obj["model_output_data"][key]) for key in parsed_obj["model_output_data"].keys()]
            combined = list(dict.fromkeys(list(new_keys) + list(existing_keys)))  # Combine and remove duplicates while preserving order
            header_collection["MS_model"]["model_data_key"] = combined
    if "model_output_path" in parsed_obj and "model_output_path" not in header_collection["MS_model"] :
        header_collection["MS_model"]["model_output_path"] = ""
    
def get_MS_model_list(MS_model_header_dict) :
    model_header  = list()
    for model_key in MS_model_header_dict["model_data_key"] :
        if model_key == "model_data_key":
            model_header.extend(MS_model_header_dict[model_key])
        else :
            model_header.append(model_key)
    model_header.append("model_output_path") if "model_output_path" in MS_model_header_dict else None
    return model_header

def get_power_header_list(power_header_dict) :
    power_header  = list()
    for power_key in power_header_dict:
        if power_key == "power_data_key" :
            power_header.extend(power_header_dict[power_key])
        else :
            power_header.append(power_key)
    
    return power_header

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

def get_procyon_score_header_list(procyon_header_dict) :
    procyon_header  = list()
    for procyon_item in procyon_header_dict:
        procyon_header.append(procyon_item)
    return procyon_header


def getHeaderCollection():
    # this dictates the column order in the final excel, so the order of appending matters
    flatten_header = ["Data label", "Condition"]
    flatten_header.extend(get_power_header_list(header_collection["power"])) if "power" in header_collection else None
    flatten_header.extend(get_MS_model_list(header_collection["MS_model"])) if "MS_model" in header_collection else None
    # flatten_header.extend(get_SC_FPS_list(header_collection["SC_FPS"])) if "SC_FPS" in header_collection else None
    # flatten_header.extend(get_teams_vpt_camera_list(header_collection["vpt_camera"])) if "vpt_camera" in header_collection else None
    flatten_header.extend(get_procyon_score_header_list(header_collection["procyon"])) if "procyon" in header_collection else None
    flatten_header.extend(get_socwatch_header_list(header_collection["socwatch"])) if "socwatch" in header_collection else None
    flatten_header.extend(get_pcie_socwatch_header_list(header_collection["PCIe_socwatch"])) if "PCIe_socwatch" in header_collection else None
    return flatten_header


"""
    flattened.update(tools.flatten_power_dic(entry, picks))
    flattened.update(tools.flatten_model_dic(entry))
    flattened.update(tools.flatten_fps_dic(entry))
    flattened.update(tools.flatten_LPmode_sr_dic(entry))
    flattened.update(tools.flatten_procyon_xml_dic(entry))
    flattened.update(tools.flatten_teams_vpt_camera_dic(entry))
    flattened.update(tools.flatten_socwatch_dic(entry, socwatch_targets))
    flattened.update(tools.flatten_pcie_socwatch_dic(entry, PCIe_targets))
"""

