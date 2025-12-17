import os
import time
from pathlib import Path
import parsers.tools as tools
import parsers.ETLFirstEventParserByPS as ETLF


def filetime_to_epoch(filetime):
    """
    Convert Windows FILETIME to Unix Epoch timestamp
    Args:
        filetime (int): Windows FILETIME (100-nanosecond intervals since Jan 1, 1601)
    Returns:
        float: Unix timestamp (seconds since Jan 1, 1970)
    """
    # FILETIME epoch: January 1, 1601
    # Unix epoch: January 1, 1970  
    # Difference: 11644473600 seconds = 116444736000000000 * 100ns intervals
    
    FILETIME_EPOCH_DIFF = 116444736000000000
    FILETIME_TO_MILLISECONDS = 10000  # 100-nanosecond intervals per millisecond
    
    return (filetime - FILETIME_EPOCH_DIFF) / FILETIME_TO_MILLISECONDS


def isEpochMilliseconds(value):
    epoch = float(str(value).strip())
    if 1e10 <= epoch <= 4102444800000:
        return True
    else :
        return False


def parseETL(etl_path, collection) :
    
    etl_data = dict()
    etl_obj = {
        "etl_data":etl_data,
        "etl_path":etl_path
    }

    # extractor = ETLF.ETLHighPrecisionTimeExtractor()
    
    # if "socwatch_first_event_epoch_milli" in collection and isEpochMilliseconds(collection["socwatch_first_event_epoch_milli"]):
    #     etl_data["socwatch_first_event_epoch_milli"] = collection["socwatch_first_event_epoch_milli"]
    #     return etl_obj

    # try:
    #     #Get all timestamp formats
    #     print(f"[ETL Parsing...] {etl_path}")
    #     start_time = time.perf_counter()
    #     # timestamp_dict = extractor.get_first_event_times(etl_path)
    #     epoch = extractor.get_quick_first_event(etl_path)
    #     end_time = time.perf_counter()
    #     elapsed_time = end_time - start_time
    #     print(f"[Epoch: {epoch}] {etl_path} file parsed Successful! [Elapsed time:::] {elapsed_time} seconds")
        
    # except Exception as e:
    #     print(f"Error: {e}")


    # etl_data["socwatch_first_event_epoch_milli"] = epoch
    
    return etl_obj
        


