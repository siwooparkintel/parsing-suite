import csv
import time
import pandas as pd
import parsers.tools as tools
import parsers.power_trace_parser as ptp


def matches_nested_criteria(block_value, expected_value):
    """
    Recursively checks if block_value matches expected_value.
    Handles nested dictionaries at any depth.
    
    Args:
        block_value: The actual value from the block
        expected_value: The expected value from the detection criteria
    
    Returns:
        bool: True if values match, False otherwise
    """
    # If expected value is a dictionary, recursively check nested structure
    if isinstance(expected_value, dict):
        # Block value must also be a dictionary
        if not isinstance(block_value, dict):
            return False
        
        # Check all keys and values in the expected dictionary
        for key, nested_expected in expected_value.items():
            # Key must exist in block value
            if key not in block_value:
                return False
            
            # Recursively check the nested value
            if not matches_nested_criteria(block_value[key], nested_expected):
                return False
        
        return True
    
    # If expected value is a list, check if it matches (can be extended for more complex list matching)
    elif isinstance(expected_value, list):
        if not isinstance(block_value, list):
            return False
        return block_value == expected_value
    
    # For all other types (str, int, float, bool, None), do direct comparison
    else:
        return block_value == expected_value


def getTraceObject(hobl_data, picks):
    """
    Filters blocks from hobl_data based on detection criteria in picks.
    Supports multi-level nested dictionary matching.
    
    Args:
        hobl_data: List of data blocks to filter
        picks: Dictionary containing "inferencing_power_detection" criteria
    
    Returns:
        list: Filtered blocks that match all detection criteria
    """
    trace_list = list()
    
    # Get the detection criteria from picks
    detection_criteria = picks.get("inferencing_power_detection", {})
    
    for block in hobl_data:
        # Check if all keys and values in detection_criteria match the block
        match = True
        
        for key, expected_value in detection_criteria.items():
            # Check if the key exists in the block
            if key not in block:
                match = False
                break
            
            # Use recursive function to check if values match
            if not matches_nested_criteria(block[key], expected_value):
                match = False
                break
        
        # If all criteria match, add the block to the trace list
        if match:
            trace_list.append(block)
    
    return trace_list
        

def flatten_trace_data(entry):
    flattened = {'Condition': entry['data_label'][0], 'data_label': entry['data_label'][1]}
    flattened.update(tools.flatten_trace_dic(entry))
    return flattened
        

def reportInferencingOnlyPower(result_path, hobl_data, DAQ_target, picks):
    start_time = time.perf_counter()

    target_blocks = getTraceObject(hobl_data, picks)
    ptp.averageInferencingPower(target_blocks, DAQ_target, picks)
    
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





    




        


                



