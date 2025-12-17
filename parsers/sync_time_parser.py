import os
import json
from datetime import datetime
import parsers.tools as tools


sync_verifier = 5


def isExistFile(file_path):
    return True if os.path.exists(file_path) else False

def string_to_epoch(time_string):

    format_string = "%Y-%m-%d %H:%M:%S.%f"

    try:
        datetime_object = datetime.strptime(time_string, format_string)
        epoch_timestamp = datetime_object.timestamp()
        return epoch_timestamp
    except ValueError as e:
        return e

def parseStringTimeBeforeMark(line, target_text) :
    mark_idx = line.find(target_text)
    return line[:mark_idx].strip().replace(",", ".")
    # mark_idx = line.find(target_dic["DAQ_timestamp_mark"])
    # timestamp = string_to_epoch(line[:mark_idx].strip().replace(",", "."))
    # daq_dic["daq_start_timestamp"] = timestamp

def parseDaq(log_path, target_dic):
    daq_dic = dict()
    with open(log_path, encoding='utf-8-sig', newline='') as file:
        lines = file.readlines()
        for line in lines:
            if line.find(target_dic["DAQ_start_target"]) >= 0:
                daq_dic["daq_start_timestamp"] = string_to_epoch(parseStringTimeBeforeMark(line, target_dic["DAQ_timestamp_mark"]))
            if line.find(target_dic["DAQ_stop_target"]) >= 0:
                daq_dic["daq_stop_timestamp"] = string_to_epoch(parseStringTimeBeforeMark(line, target_dic["DAQ_timestamp_mark"]))
                daq_dic["daq_duration"] =  round(daq_dic["daq_stop_timestamp"] - daq_dic["daq_start_timestamp"], 3)
                break
        return daq_dic

def readLog(log_path, target_text):
    # # reading csv file
    with open(log_path, encoding='utf-8-sig', newline='') as file:
        target_lines = []
        lines = file.readlines()
        for line in lines:
            target_index = line.find(target_text)
            if  target_index >= 0:
                timestamp = string_to_epoch(line[:target_index].strip().replace(",", "."))
                msg = json.loads(line[target_index+len(target_text):])
                if "method" in msg and msg['method'] == "StartJobWithNotification":
                    target_lines.append({'timestamp':timestamp, "msg_obj":msg})
        return target_lines

def find_dict_by_scenario_name(data, scenario_name):
    for idx in range(len(data) - 1, -1, -1):
        if data[idx].get('scenario_name') == scenario_name:
            return data[idx]
    return None

def read_ICOB_output(output_path, sync_target, daq_dic, trace_obj):

    start_string = sync_target["scenario_start_target"]
    end_string = sync_target["scenario_end_target"]
                                           
    time_scale = trace_obj["time_scale"]
     # # reading csv file
    scenario_list = list()
    with open(output_path, 'r', encoding='utf-16') as file:
        lines = file.readlines()
        for line in lines:
            found_scenario_idx = line.find(start_string)
            if found_scenario_idx >= 0:
                parsed_start_timestamp_int = int(line[:found_scenario_idx].split(" ")[2][:-1])
                scenario_list.append({
                    "index":len(scenario_list),
                    "scenario_name":line[found_scenario_idx+len(start_string):].strip().split(" ")[0],
                    "start_timestamp":parsed_start_timestamp_int,
                    "scenario_start_trace_row" : int(round((parsed_start_timestamp_int - daq_dic["daq_offset_adjusted_start_ms"]) / time_scale, 0))
                })
            end_scenario_idx = line.find(end_string)
            if end_scenario_idx >= 0:
                scenario_name = line[end_scenario_idx+len(end_string):].strip().split(" ")[0]
                end_timestamp = line[:end_scenario_idx].split(" ")[2][:-1]
                pulled_scenario = find_dict_by_scenario_name(scenario_list, scenario_name)
                pulled_scenario["end_timestamp"] = int(end_timestamp)
                pulled_scenario["scenario_stop_trace_row"] = int(round((pulled_scenario["end_timestamp"] - daq_dic["daq_offset_adjusted_start_ms"]) / time_scale, 0))
                pulled_scenario["duration"] = pulled_scenario["end_timestamp"] - pulled_scenario["start_timestamp"]
                pulled_scenario["duration_in_row_number"] = (pulled_scenario["scenario_stop_trace_row"] - pulled_scenario["scenario_start_trace_row"])

            # target_index = line.find(target_text)
            # if  target_index > 0:
            #     timestamp = string_to_epoch(line[:target_index].strip().replace(",", "."))
            #     msg = json.loads(line[target_index+len(target_text):])
            #     if "method" in msg and msg['method'] == "StartJobWithNotification":
            #         target_lines.append({'timestamp':timestamp, "msg_obj":msg})
                    
    return scenario_list   

def get_offsets(dut_list, host_list):
    offsets = list()
    for dut_msg in dut_list:
        for host_msg in host_list:
            if "msg_obj" in host_msg and "msg_obj" in dut_msg and host_msg["msg_obj"]['params'][1] == dut_msg["msg_obj"]['params'][1]:
                offsets.append(host_msg["timestamp"] - dut_msg["timestamp"])
    offsets.sort()
    return offsets

def find_first_value_within_verifier_percent_change(numbers):
    for i in range(len(numbers) - 1):
        current_value = numbers[i]
        next_value = numbers[i + 1]
        
        # Calculate the percentage change
        if current_value != 0:  # Avoid division by zero
            percent_change = abs(next_value - current_value) / current_value * 100
        else:
            percent_change = float('inf')  # Handle zero current_value
        
        # Check if the percentage change is within 5%
        if percent_change < sync_verifier:
            return current_value
    
    return None

def parseLogs(tdic, sync_target, trace_obj) :

    sync_obj = dict()

    host_log_path = tdic["host_log"]
    dut_log_path = tdic["dut_log"]
    CataV3_output_path = tdic["catapult_output"]

    if isExistFile(host_log_path) == False or isExistFile(dut_log_path) == False or isExistFile(CataV3_output_path) == False :
        tools.errorAndExit(f"file(s) not existing [host_log] {host_log_path} or [dut_log] {dut_log_path} or [catapult_output] {CataV3_output_path}")

    host_log_list = readLog(host_log_path, sync_target["host_log_target"])
    daq_dic = parseDaq(host_log_path, sync_target)
    dut_log_list = readLog(dut_log_path, sync_target["dut_log_target"])

    time_offset_list = get_offsets(dut_log_list, host_log_list)
    valid_offset = find_first_value_within_verifier_percent_change(time_offset_list)
    print("[time sync] clock offset: ", valid_offset, " from : ", time_offset_list, " offset positive means HOST clock is ahead, DUT clock is slower than HOST")

    sync_obj["sync_offset"] = round(valid_offset, 3)

    daq_dic["daq_offset_adjusted_start_ms"] = int(round((daq_dic["daq_start_timestamp"] - sync_obj["sync_offset"]) * 1000, 0))
    daq_dic["daq_offset_adjusted_stop_ms"] = int(round((daq_dic["daq_stop_timestamp"] - sync_obj["sync_offset"]) * 1000, 0))

    sync_obj["daq_data"] = daq_dic

    dut_timestamp_list = read_ICOB_output(CataV3_output_path, sync_target, daq_dic, trace_obj)
    
    sync_obj["CataV3_data"] = dut_timestamp_list
    # sync_obj["sum_of_duration"] = sum([item['duration'] for item in dut_timestamp_list])
    sync_obj["workload_duration"] = dut_timestamp_list[len(dut_timestamp_list)-1]["end_timestamp"] - dut_timestamp_list[0]["start_timestamp"]

    sync_obj["host_log_path"] = host_log_path
    sync_obj["dut_log_path"] = dut_log_path
    sync_obj["catapult_output_path"] = CataV3_output_path

    return sync_obj





