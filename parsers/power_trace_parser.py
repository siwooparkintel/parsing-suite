import csv
import numbers
import parsers.tools as tools


fields = []
rows = []

AVERAGE = "Average"
P_SOC = "P_SOC"
P_CORE = "P_VCCCORE"
P_GPU = "P_VCCGT"
P_NPU = "P_VCCSA"

# time buffer to include the whole inferencing duration. 
# inferencing happening at the end of power collection, 
# so it is easier to check it from the power data backwards
# power data collection ends after 2.2 seconds in most of the time, + 2.8 seconds more buffer, total 5000 ms.
TIME_BUFFER = 5000


def getSamplingRate(file_path) :
    # file_name = file_path.split("\\")[-1]
    samplingRate = file_path.split("-")[-1]
    # print(float(tools.parseNumeric(samplingRate)))
    return float(tools.parseNumeric(samplingRate))


def getTargetedRailIndexObject(header, DAQ_target) :
    copied = DAQ_target.copy()
    for target_rail_name in copied :
        for trace_idx in range(len(header)-1, -1, -1):
            if target_rail_name == header[trace_idx] :
                copied[target_rail_name] = trace_idx
                break
    return copied

def getReversedPower(csv_list, total_row_num, infer_duration, time_scale, power_rail_name) :
    # capture power data in reverse since the inferencing happens at the end of the power collection
    target_power_reversed = list()
    stop_row_num = total_row_num - (int((infer_duration+TIME_BUFFER) / time_scale))
    for idx in range(total_row_num-1, stop_row_num, -1):
        line = csv_list[idx]
        target_power_reversed.append(line[power_rail_name])
    # print(target_power_reversed, len(target_power_reversed))    
    return target_power_reversed

def getInferencingStartReversed(target_power_reversed, target_rail, file_path) :

    # now have to find the power surge by checking power changes (slope and derivative)
    step_avr = list()
    steps = 10
    length = len(target_power_reversed)-1
    isInferencingFound = False

    for idx in range(0, length, steps) :
        upto = idx + steps
        if upto > length :
            upto = length
            
        # data_set will be 5 item list : [index start, idx end, step average, slope, derivative]
        data_set = [idx, upto]

        total = sum([float(item) for item in target_power_reversed[idx:upto]])

        # ==========================================================================================================
        # data correction. physical power measurement can give the impossible negative power in very miniscule scale
        # adjust is needed to avoid Zero related issues
        # ==========================================================================================================
        total = 0.001 if total < 0.001 else total    # if you set smaller than 0.001 it became 0 divided by Zero later
        data_set.append(round(total/len(target_power_reversed[idx:upto]), 4))
        step_avr_idx = len(step_avr)-1
        if step_avr_idx == -1:
            data_set.append(1)
            data_set.append(0)
            step_avr.append(data_set)
        else :
            # print(step_avr[step_avr_idx],  step_avr[step_avr_idx-1], step_avr[step_avr_idx] - step_avr[step_avr_idx-1])
            # slope = step_avr[key][step_avr_idx] / step_avr[step_avr_idx-1] if step_avr[step_avr_idx-1] else 0
            # derivative = step_avr[step_avr_idx] - step_avr[step_avr_idx-1]
            pre_data_set = step_avr[-1]
            # print ("===================== : ", pre_data_set)
            slope = round(data_set[2] / pre_data_set[2], 2)
            derivative = round((data_set[2] - pre_data_set[2]), 2)
            data_set.append(slope)
            data_set.append(derivative)
            step_avr.append(data_set)
            if slope > target_rail[1] and derivative > target_rail[2]:
                isInferencingFound = True
                # print("== found inferencing start", file_path, target_rail, data_set, step_avr)
                return data_set[0]

    if isInferencingFound == False :
        print("======= not found: ", file_path, target_rail, data_set, step_avr)   
        return None                 
    

def getAveragePowerByRails(csv_list, time_scale, target_obj, total_token_gen, P_SOC) :
    trace_data = dict()
    for rail in target_obj:
        # print("==== rail name: ", len(csv_list), rail, target_obj[rail])
        rail_idx = target_obj[rail]
        if rail == "Run Time" : 
            trace_data["Run Time"] = round((len(csv_list) * time_scale / 1000), 1) # in seconds 1st floating digit 
        elif isinstance(rail_idx, numbers.Number) :
            rail_list = [float(line[rail_idx]) for line in csv_list]
            # if rail == "P_SOC+MEMORY" :
            #     print(rail, rail_list)
            trace_data[rail] = round(sum(rail_list) / len(csv_list), 3)
            # print("==== ", rail, trace_obj[rail])
            # if rail == "P_SOC+MEMORY" :
        else :
            #print("skipping rail: ", rail, rail_idx)
            pass

    # print(trace_obj)
    trace_data["Energy (J)"] = round(trace_data["Run Time"] * trace_data[P_SOC], 3)
    trace_data["Eng(J)/Token"] = round(trace_data["Energy (J)"] / total_token_gen, 3)
    return trace_data


def averageInferencingPower(filtered_data, DAQ_target, picks) :
    # reading csv file
    P_SOC = picks.get('SOC_POWER_RAIL_NAME')
    P_CORE = picks.get('PCORE_POWER_RAIL_NAME')
    P_GPU = picks.get('GT_POWER_RAIL_NAME')
    P_NPU = picks.get('SA_POWER_RAIL_NAME')
    
    for block in filtered_data:

        if "power_obj" in block and "model_output_obj" in block and block["model_output_obj"]["model_output_status"] == "successful":
            
            block["trace_obj"]
            trace_sampling_rate = getSamplingRate(block["trace_obj"]["file_path"])
            # in milliseconds. So 100 sampling rate, 1 row advance means 10 ms passed.
            time_scale = 1000 / trace_sampling_rate


            with open(block["trace_obj"]["file_path"], encoding='utf-8-sig', newline='') as tracefile:
                
                csvreader = csv.reader(tracefile)
                header = next(csvreader)
                target_obj = getTargetedRailIndexObject(header, DAQ_target)

                if block["model_output_obj"]["model_output_data"]["duration"][1].lower() in ['s', 'sec', 'secs', 'second', 'seconds'] :
                    infer_duration = block["model_output_obj"]["model_output_data"]["duration"][0] * 1000  # in ms
                    block["model_output_obj"]["model_output_data"]["duration"][1] = "ms"
                else :
                    infer_duration = block["model_output_obj"]["model_output_data"]["duration"][0] # already in ms
                
                
                device = block["model_output_obj"]["model_output_data"]["device"][0]
                csv_list = list(csvreader)
                total_row_num = len(csv_list)
                # CPU uses P-core for inferencing, so default. 
                # [Power_rail_name, slope minimum, power delta minimum]
                target_rail = [P_CORE, 2.3, 3]
                # if "GPU" in device:
                #     target_rail = [P_GPU, 2.24, 3]  # after checking 50 files 
                # elif "NPU" in device:
                #     target_rail = [P_NPU, 1.7, 1] # slope is the main detector for power surge
                
                infer_start_idx = -1
                infer_end_idx = -1

                target_power_reversed = getReversedPower(csv_list, total_row_num, infer_duration, time_scale, target_obj[target_rail[0]])
                infer_start_reversed = getInferencingStartReversed(target_power_reversed, target_rail, block["trace_obj"]["file_path"])
                if infer_start_reversed is None :
                    block["trace_obj"]["total_row"] = None
                    block["trace_obj"]["duration_in_scale"] = None
                    block["trace_obj"]["inf_start"] = None
                    block["trace_obj"]["inf_end"] = None
                    block["trace_obj"]["trace_data"] = None
                else :
                    infer_duration_in_scale = round((infer_duration / time_scale))
                    infer_start_idx = total_row_num - infer_duration_in_scale - infer_start_reversed
                    infer_end_idx = infer_start_idx + infer_duration_in_scale
                    # print(f"=== total_row_num: {total_row_num}, infer_duration_in_scale: {infer_duration_in_scale}, infer_start_idx: {infer_start_idx}, infer_end_idx: {infer_end_idx}, path: {block["trace_obj"]["file_path"]}")
                    block["trace_obj"]["total_row"] = total_row_num
                    block["trace_obj"]["duration_in_scale"] = infer_duration_in_scale
                    block["trace_obj"]["inf_start"] = infer_start_idx
                    block["trace_obj"]["inf_end"] = infer_end_idx
                    block["trace_obj"]["Device"] = device
                    block["trace_obj"]["trace_data"] = getAveragePowerByRails(csv_list[infer_start_idx:infer_end_idx], time_scale, target_obj, block["model_output_obj"]["model_output_data"]["total_token_gen"][0], P_SOC)
                    print("========", block["trace_obj"]["trace_data"])
        else :
            # print("[Missing essential data]", )
            pass
    # sub_slopes = list()
    # sub_deriv = list()
    # for infer_set in NPU_list :
    #     sub_slopes.append(infer_set[3])
    #     sub_deriv.append(infer_set[4])
    # sorted_slopes = sorted(sub_slopes)
    # sorted_deriv = sorted(sub_deriv)
    # print("slopes: ", sorted_slopes, "    derivatives: ", sorted_deriv)

def parsePowerTraceCSV(csv_path) :
    
    trace_data = None
    trace_obj = {"trace_data":trace_data}
    trace_obj["file_path"] = csv_path
    
    return trace_obj


