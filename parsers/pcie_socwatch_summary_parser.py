import os
import csv
import parsers.tools as tools


pcie_socwatch_header_dict = dict()


def NVMResidencyTable(table, target) :
    copied = table['table_data'].copy()
    data = dict()
    header = copied[0]
    for row_idx in range(1, len(copied), 1) :
        for device in target['devices']:
            if device in copied[row_idx][0] :
                for index, key in enumerate(header):
                    data[key+"_"+device] = copied[row_idx][index]
    table['table_data'] = data


def defaultResidencyTable(table, keyIdx, ValueIdx) :
    copied = table['table_data'].copy()
    data = dict()
    for idx in range(len(copied)):
        line = copied[idx]
        key = line[keyIdx]
        if "_Pstate" in table['label'] and idx > 0:
            key = key.split(".")[0]
        data[key] = line[ValueIdx]
    table['table_data'] = data


def PCIeTableTypeChecker(table, target) :

    label = table['label']
    if label == 'PCIe_LPM' or label == "PCIe_Active" or label == "PCIe_LTRsnoop":
        NVMResidencyTable(table, target)
    else :
        defaultResidencyTable(table, 0, 1)

def extractHeader(table) :

    if table["label"] not in pcie_socwatch_header_dict:
        pcie_socwatch_header_dict[table["label"]] = [key for key in table['table_data']]
    else :
        prev_keys = pcie_socwatch_header_dict[table["label"]]
        new_keys = [key for key in table['table_data']]
        set_keys = prev_keys.copy()
        for item in new_keys :
            if item not in prev_keys :
                set_keys.append(item)
        pcie_socwatch_header_dict[table["label"]] = set_keys


def parsePCIe(tdic, pcie_targets) :


    abs_path = None
    if "PCIe_socwatch_summary_path" in tdic :
        abs_path = tdic["PCIe_socwatch_summary_path"] 
    elif os.path.exists(tdic):
        abs_path = tdic
        # tdic = dict()
        # tdic["PCIe_socwatch_summary_path"] = abs_path
        # tdic["data_summary_type"] = "compact"
    else :
        tools.errorAndExit("PCIe socwatch summary path is not supplied")


    # abs_path = tdic["PCIe_socwatch_summary_path"]
    socwatch_obj = dict()
    socwatch_obj['pcie_socwatch_path'] = abs_path
    socwatch_obj['pcie_socwatch_tables'] = []


    with open(abs_path, encoding='utf-8-sig', newline='') as csvfile:

        csvreader = csv.reader(csvfile)

        for target in pcie_targets : 
            tTable = dict()
            for tlist in csvreader :
                if 'isCompleted' in tTable and tTable['isCompleted'] == False :
                    # if the table_data is initiated, 'isCompleted' exists, keep collecting line until empty line comes
                    if all(item == "" for item in tlist) :
                        tTable['isCompleted'] = True
                        PCIeTableTypeChecker(tTable, target)
                        # Socwatch data is being parsed, header is also being collected and expended for unified header later
                        extractHeader(tTable)
                        socwatch_obj['pcie_socwatch_tables'].append(tTable)
                        break
                    else :
                        trimmed_list = tools.trim_list(tlist)
                        if len(trimmed_list) > 0 :
                            tset = set("".join(trimmed_list))
                            if all(char in {" ", "-"} for char in tset) == False :
                                tTable['table_data'].append(trimmed_list)

                elif len(tlist) > 0 and tlist[0].rfind(target['lookup']) >=0 :
                    tTable['label'] = target['key']
                    tTable['table_data'] = list()
                    tTable['isCompleted'] = False  


        return socwatch_obj

        

