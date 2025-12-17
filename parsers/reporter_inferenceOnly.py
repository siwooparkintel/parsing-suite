import csv
import time
import pandas as pd
import parsers.tools as tools
import parsers.power_trace_parser as ptp




def getTraceObject(hobl_data, DAQ_target) :
    trace_list = list()
    for block in hobl_data :
        if "power_obj" in block and block["power_obj"]["picked"] == "picked" and block['power_obj']['power_type'] == "POWER" and "model_output_obj" in block and block["model_output_obj"]["model_output_status"] == "successful" :
            trace_list.append(block)
    return trace_list
        

def flatten_trace_data(entry):
    flattened = {'Condition': entry['data_label'][0], 'data_label': entry['data_label'][1]}
    flattened.update(tools.flatten_trace_dic(entry))
    return flattened
        

def reportInferencingOnlyPower(result_path, hobl_data, DAQ_target):
    start_time = time.perf_counter()

    target_blocks = getTraceObject(hobl_data, DAQ_target)
    ptp.averageInferencingPower(target_blocks, DAQ_target)
    
    infOnlyAdded_dict_list = []
    for entry in target_blocks:
            
        # need to insert after similar data. not just at the end
        trace_flatten_dict = flatten_trace_data(entry)
        similar_model_index = None
        for index in range(len(infOnlyAdded_dict_list)-1, -1, -1):
            if infOnlyAdded_dict_list[index]['data_label'].find(trace_flatten_dict['data_label']) >= 0:
                similar_model_index = index
                break
        if similar_model_index is not None :
            infOnlyAdded_dict_list.insert(similar_model_index+1, trace_flatten_dict)
        else :
            infOnlyAdded_dict_list.append(trace_flatten_dict)

    df = pd.DataFrame(infOnlyAdded_dict_list)
    df.to_excel(result_path+"_infOnly_h.xlsx", index=False)

    df_v = df.transpose()
    df_v = df_v.reset_index()
    df_v.rename(columns={'index': 'Attribute'}, inplace=True)
    df_v.to_excel(result_path+"_infOnly_v.xlsx", index=False)


    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"{len(target_blocks)} of Detecting and Calculate inferencing only Power from trace raw data [Elapsed time:::] {elapsed_time} seconds")





    




        


                



