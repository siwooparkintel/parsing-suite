import parsers.tools as tools

def readTextfile(abs_path, AI_parsing_items) :

    parsed = dict()
    for item in AI_parsing_items:
        with open(abs_path, 'r') as file:
            for line in file:
                #print(type(item), item)
                target_text = item["lookup"]
                found = line.rfind(target_text)
                if found >= 0 :
                    target_string = line[found+len(target_text):]
                    parsed_data = ""
                    if item['key'] == 'full_params':
                        parsed_data = target_string.strip()
                    elif item['key'] == 'read_buffer' or item['key'] == 'write_buffer':
                        # change it to cut 5th decimal place
                        parsed_data = round(float(tools.parseNumeric(target_string.split(" ")[0])), 5)
                    else :
                        parsed_data = round(float(tools.parseNumeric(target_string)), 5)
                    parsed[item["key"]] = [parsed_data, item["unit"]]
                    break
                # elif item["key"] not in parsed:
                    # parsed[item["key"]] = [None, ""]
                # find a line that only has "=" characters to get the next line 

    with open(abs_path, 'r') as file:
        for line in file:
            if line.strip().startswith("===") :
                next_line = next(file)
                value_list = next_line.split("\t")
                parsed['inject_delay'] = [int(value_list[0].strip()), "cycles"]
                parsed['Latency'] = [round(float(tools.parseNumeric(value_list[1])), 2), "ns"]
                parsed['Bandwith'] = [round(float(tools.parseNumeric(value_list[2])), 2), "MB/sec"]
                break
    return parsed


def parseMlcResults(abs_path, AI_parsing_items) :
    temp = dict()

    # need to modify it, HoBL => AI_Phi_tester.bat => GPU_run.bat => python model runner => python model runner output => hobl.log parsing


    temp['mlc_output_path'] = abs_path
    temp['mlc_output_data'] = readTextfile(abs_path, AI_parsing_items)

    # token_gen_number = int(temp['mlc_output_data']['total_token_gen'][0])

    # device = ""
    # if "GPU" in tools.splitLastItem(abs_path, "\\", 1)[1] :
    #     device = "GPU"
    # elif "NPU" in tools.splitLastItem(abs_path, "\\", 1)[1] :
    #     device = "NPU"

    # temp['mlc_output_data']['device'] = [device, ""]
    # temp['mlc_output_data']['throughput'] = temp['mlc_output_data']['Tokens_per_second'].copy()
    # temp['mlc_output_data']['dur_checksum'] = [round(token_gen_number * (1 / float(temp['mlc_output_data']['throughput'][0])), 2), "ms"]

    # if temp['mlc_output_data']['throughput'][1] == "" :
    #     err = [abs_path, "=[ERROR]= : ", " it may not a result file or you may want to recollect"]
    #     temp['mlc_output_status'] = "failed"
    # else :
    #     temp['mlc_output_status'] = "successful"

    return temp





