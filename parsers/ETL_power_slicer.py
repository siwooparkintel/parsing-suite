import os
import time
from pathlib import Path
import parsers.tools as tools
import parsers.ETLFirstEventParserByPS as ETLF




def slice_power_ETL(entry, collection) :
    
    if "socwatch" in collection or os.path.exists(collection["socwatch"]):
        print(entry)
    else :
        tools.errorAndExit("[Error] Socwatch.exe path is mssing")

        


