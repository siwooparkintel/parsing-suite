import re
import sys
import os
import json
import numpy as np


header_collection = dict()


def tk_dialogs(
    dialog_type="open_file",
    title="Select a file",
    initial_dir=None,
    filetypes=None,
):
    """Small tkinter dialog helper for file/folder interactions.

    Supported dialog_type values:
    - open_file
    - open_folder
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    root = tk.Tk()
    root.withdraw()

    selected = None
    try:
        if dialog_type == "open_folder":
            selected = filedialog.askdirectory(
                title=title,
                initialdir=initial_dir,
            )
        else:
            selected = filedialog.askopenfilename(
                title=title,
                initialdir=initial_dir,
                filetypes=filetypes or [("All files", "*.*")],
            )
    finally:
        root.destroy()

    return selected if selected else None

def parseNumeric(text) :
    return ''.join(re.findall(r'[0-9.]', text))
def parseDevice(text) :
    return ''.join(re.findall(r'[A-Z.0-9]', text))


def tryRoundifNumber(value) :
    try :
        return round(float(value), 2)
    except ValueError as e:
        return value

def tryIntifNumber(value) :
    try :
        return int(value)
    except ValueError as e:
        return value
    
# add def saveLastOpenedFolder(folder_path):
def saveLastOpenedFolder(folder_path):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        last_folder_file = os.path.join(parent_dir, "config", "last_opened_folder.txt")
        with open(last_folder_file, "w") as f:
            f.write(folder_path)
    except Exception as e:
        print(f"Failed to save last opened folder: {e}")
    
def splitLastItem(abs_path, joint, cutNum) :
    item_list = abs_path.split(joint)
    return [joint.join(item_list[:-cutNum]), item_list[len(item_list)-1]]

def trim_list(data_list):
    """
    Removes empty items from the back of a list.
    An item is considered 'empty' if it evaluates to False (e.g., '', 0, None, [], {}).
    """
    while data_list and data_list[-1].strip() == "":  # Check if list is not empty and last element is falsy
        data_list.pop()
    return [item.strip() for item in data_list]


def get_median(values) :
    return np.median(values)
        
def errorAndExit(msgs) :
    print("=============================================================================")
    sys.exit("[Error] :: " + msgs)
    print("=============================================================================")

    
def jsonLoader(filename, picks) :

    try :
        with open(os.path.join(filename), 'r') as json_file:
            data = json.load(json_file)
            parsePowerRailNames(data["DAQ_target"], picks) if "DAQ_target" in data else None
            return data
    except Exception as e:
        errorAndExit(f"Failed to load JSON file: {e}")

def parsePowerRailNames(DAQ_target, picks):
    picks["SOC_POWER_RAIL_NAME"] = DAQ_target.get("SOC_POWER_RAIL_NAME")
    picks["PCORE_POWER_RAIL_NAME"] = DAQ_target.get("PCORE_POWER_RAIL_NAME")
    picks["SA_POWER_RAIL_NAME"] = DAQ_target.get("SA_POWER_RAIL_NAME")
    picks["GT_POWER_RAIL_NAME"] = DAQ_target.get("GT_POWER_RAIL_NAME")
    print("============================= ", picks)