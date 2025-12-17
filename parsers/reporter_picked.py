import pandas as pd
import parsers.tools as tools
import parsers.socwatch_summary_parser as soc



def flatten_picked_data(entry, socwatch_targets, picks, pulled_soc_entry):
    flattened = {'Condition': entry['data_label'][0], 'data_label': entry['data_label'][1]}
    flattened.update(tools.flatten_power_dic(entry, picks))
    flattened.update(tools.flatten_model_dic(entry))
    flattened.update(tools.flatten_socwatch_dic(pulled_soc_entry, socwatch_targets))
    return flattened


def pulled_soc_entry(data_label_list, hobl_data):
    for entry in hobl_data :
        if data_label_list == entry["data_label"] and entry["power_obj"]["power_type"] == "SOCWATCH_POWER" and entry["power_obj"]["picked"] == "picked":
            return entry
    return {}


def reportPickedData2(result_path, hobl_data, socwatch_targets, picks) :

    picked_list = []
    for entry in hobl_data:
        if entry["power_obj"]["power_type"] == "POWER" and entry["power_obj"]["picked"] == "picked":
            
            # need to insert after similar data. not just at the end
            picked_flatten_dict = flatten_picked_data(entry, socwatch_targets, picks, pulled_soc_entry(entry["data_label"], hobl_data))
            similar_model_index = None
            for index in range(len(picked_list)-1, -1, -1):
                if picked_list[index]['data_label'].find(picked_flatten_dict['data_label']) >= 0:
                    similar_model_index = index
                    break
            if similar_model_index is not None :
                picked_list.insert(similar_model_index+1, picked_flatten_dict)
            else :
                picked_list.append(picked_flatten_dict)

    df = pd.DataFrame(picked_list)
    df.to_excel(result_path+"_picked_h.xlsx", index=False)

    df_v = df.transpose()
    df_v = df_v.reset_index()
    df_v.rename(columns={'index': 'Attribute'}, inplace=True)
    df_v.to_excel(result_path+"_picked_v.xlsx", index=False)



    




        


                



