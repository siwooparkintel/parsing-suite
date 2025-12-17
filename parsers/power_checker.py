import math



def markPicked(list, PICKED):
    if len(list) > 0 :
        if len(list) == 1 or PICKED == "MIN":
            list[0]['power_obj']['picked'] = 'picked'
        elif PICKED == "MAX":
            list[len(list)-1]['power_obj']['picked'] = 'picked'
        elif PICKED == "MED" and len(list)%2 == 0:
            # this picks middle lower side. ex) 4 => (4/2)-1 = 1. [0, 1, 2, 3] pick 1 
            list[int(len(list)/2) - 1]['power_obj']['picked'] = 'picked'
            # this picks middle higher side. ex) 4 => (4/2) = . [0, 1, 2, 3] pick 2 
            # list[int(len(list)/2)]['power_obj']['picked'] = 'picked'
        elif PICKED == "MED" and len(list)%2 == 1:
            list[math.floor(len(list)/2)]['power_obj']['picked'] = 'picked'
        
        for item in list :
            if 'picked' not in item['power_obj'] :
                item['power_obj']['picked'] = None  



def sortAndPick(objs, picks) :
    etls = list()
    powers = list()
    socwatches = list()

    for obj in objs :
        dtype = obj["data_type"]
        if "ETL" in dtype and "POWER" in dtype:
            # if len(etls) > 0 and etls[leg(etls)]
            etls.append(obj)
        elif "SOCWATCH" in dtype and "POWER" in dtype:
            socwatches.append(obj)
        elif "POWER" in dtype:
            powers.append(obj)

    sorted_etls = sorted(etls, key=lambda x: x["power_obj"]["power_data"]['P_SOC+MEMORY'])
    sorted_powers = sorted(powers, key=lambda x: x["power_obj"]["power_data"]['P_SOC+MEMORY'])
    sorted_socwatches = sorted(socwatches, key=lambda x: x["power_obj"]["power_data"]['P_SOC+MEMORY'])

    markPicked(sorted_etls, picks['power_pick'])
    markPicked(sorted_powers, picks['power_pick'])
    markPicked(sorted_socwatches, picks['power_pick'])


    # sort working. commented out reverse also working
    # sorted_etls = sorted(etls, key=lambda x: x["power_data"]['P_SOC+MEMORY'], reverse=True)
    # sorted_powers = sorted(powers, key=lambda x: x["power_data"]['P_SOC+MEMORY'], reverse=True)
    # sorted_socwatches = sorted(socwatches, key=lambda x: x["power_data"]['P_SOC+MEMORY'], reverse=True)
    # print("+++++++++++++++++++++++++++", sorted_etls, sorted_powers, sorted_socwatches)


def pullSameLabel(whole_sets, full_data_label) :

    power_list = list()

    for block in whole_sets:
        
        if full_data_label == " ".join(block["data_label"]) and 'power_obj' in block and "power_data" in block['power_obj'] : # and not ("ETL" in block["data_type"] or "SOCWATCH" in block["data_type"])
            temp = block["data_type"].copy()
            # temp.sort()
            block["power_obj"]["power_type"] = "_".join(temp)
            power_list.append(block)

    return power_list



def checkAndMarkPower(whole_sets, picks) :

    done_model = set()

    for obj in whole_sets:
        full_data_label = " ".join(obj["data_label"])
        if full_data_label not in done_model:
            done_model.add(full_data_label)
            objs = pullSameLabel(whole_sets, full_data_label)
            # if picks['only_picks'] is True:
            sortAndPick(objs, picks)
            
    
        