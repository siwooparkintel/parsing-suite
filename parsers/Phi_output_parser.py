import parsers.tools as tools

def readTextfile(abs_path, AI_parsing_items) :

    with open(abs_path, 'r') as file:
        parsed = dict()
        for line in file:

            for item in AI_parsing_items:
                #print(type(item), item)
                target_text = item["lookup"]
                found = line.rfind(target_text)
                if found >= 0 :
                    target_string = line[len(target_text):]
                    parsed_data = ""
                    if item['key'] == 'device':
                        parsed_data = tools.parseDevice(target_string)
                    else :
                        # change it to cut 5th decimal place
                        parsed_data = round(float(tools.parseNumeric(target_string)), 5)
                    parsed[item["key"]] = [parsed_data, item['unit']]
                    break
                elif item["key"] not in parsed:
                    parsed[item["key"]] = [None, ""]

        return parsed


def parseModelResults(abs_path, AI_parsing_items) :
    temp = dict()

    # need to modify it, HoBL => AI_Phi_tester.bat => GPU_run.bat => python model runner => python model runner output => hobl.log parsing


    temp['model_output_path'] = abs_path
    temp['model_output_data'] = readTextfile(abs_path, AI_parsing_items)

    token_gen_number = int(temp['model_output_data']['total_token_gen'][0])

    device = ""
    if "GPU" in tools.splitLastItem(abs_path, "\\", 1)[1] :
        device = "GPU"
    elif "NPU" in tools.splitLastItem(abs_path, "\\", 1)[1] :
        device = "NPU"

    temp['model_output_data']['device'] = [device, ""]
    temp['model_output_data']['throughput'] = temp['model_output_data']['Tokens_per_second'].copy()
    temp['model_output_data']['dur_checksum'] = [round(token_gen_number * (1 / float(temp['model_output_data']['throughput'][0])), 2), "ms"]

    if temp['model_output_data']['throughput'][1] == "" :
        err = [abs_path, "=[ERROR]= : ", " it may not a result file or you may want to recollect"]
        temp['model_output_status'] = "failed"
    else :
        temp['model_output_status'] = "successful"

    return temp





