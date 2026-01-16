import parsers.tools as tools

def parseAverage(target_string) :
    tdic = dict()
    item_list = target_string.split(",")
    for item in item_list :
        couple_list = item.split(":")
        trimmed_key = couple_list[0].strip()
        tdic[trimmed_key] = couple_list[1].strip().split(" ")
        tdic[trimmed_key][0] = round(float(tdic[trimmed_key][0]), 2)
        if trimmed_key == "2nd tokens throughput":
            tdic["throughput"] = tdic[trimmed_key]
        if len(tdic[trimmed_key]) == 1:
            tdic[trimmed_key].append("")
    return tdic


def readTextfile(abs_path, AI_parsing_items) :

    # print(abs_path)
    with open(abs_path, 'r') as file:
        parsed = dict()
        folder_list = tools.splitLastItem(abs_path, "\\", 1)
        parsed["device"] = [folder_list[1].split("_")[0], ""]
        for line in file:

            for item in AI_parsing_items:
                #print(type(item), item)
                target_text = item["lookup"]
                found = line.rfind(target_text)
                if found >= 0 :
                    target_string = line[found+len(target_text):]
                    parsed_data = dict()
                    if item['key'] == 'Average':
                        parsed.update(parseAverage(target_string.split("]")[1]))
                    else :
                        parsed_data = float(tools.parseNumeric(target_string))
                        parsed[item["key"]] = [parsed_data, item['unit']]
                    break
                # elif item["key"] not in parsed:
                #    parsed[item["key"]] = [None, ""]

        if "2nd token latency" in parsed and "Inference count" in parsed:
            parsed["duration"] = [parsed["2nd token latency"][0] * parsed["Inference count"][0], "ms"]
        if "Inference count" in parsed:
            parsed["total_token_gen"] = [int(parsed["Inference count"][0]), ""]          
        return parsed


def parseModelResults(abs_path, AI_parsing_items) :
    temp = dict()

    temp['model_output_path'] = abs_path
    temp['model_output_data'] = readTextfile(abs_path, AI_parsing_items)

    if temp['model_output_data']['Pipeline init time'][0] == "" or temp['model_output_data']['Inference count'][0] == "":
        err = [abs_path, "=[ERROR]= : ", " it may not a result file or you may want to recollect"]
        temp['model_output_status'] = "failed"
    else :
        temp['model_output_status'] = "successful"

    return temp





