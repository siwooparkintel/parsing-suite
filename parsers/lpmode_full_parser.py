import json
import parsers.tools as tools


def parseLpmodeJson(abs_path) :

    lpmode_data = dict()
    avg_row = list()
    with open(abs_path, 'r') as f:
        lpmode_full_json = json.load(f)
        if "table" in lpmode_full_json and "rows" in lpmode_full_json["table"] and "Average Residency" == lpmode_full_json["table"]["rows"][1]["metric"] :
            avg_row = lpmode_full_json["table"]["rows"][1]["values"]
        if "table" in lpmode_full_json and "headers" in lpmode_full_json["table"] and len(avg_row) == len(lpmode_full_json["table"]["headers"]) : 
            for index, header in enumerate(lpmode_full_json["table"]["headers"]) :
                lpmode_data[header] = avg_row[index]

        return lpmode_data


def parseLPmodeFull(abs_path) :
    temp = dict()

    temp['lpmode_full_path'] = abs_path
    temp['lpmode_full_data'] = parseLpmodeJson(abs_path)

    return temp





