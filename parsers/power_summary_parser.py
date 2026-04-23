import csv
import parsers.tools as tools


fields = []
rows = []

# for LNL
target_column = ""


def parsePowerSummaryCSV(csv_path, DAQ_target) :
    
    target_column = DAQ_target["TARGET_COLUMN"] if "TARGET_COLUMN" in DAQ_target else "Average"
    power_data = dict()
    power_obj = {"power_data":power_data}
    # reading csv file
    with open(csv_path, encoding='utf-8-sig', newline='') as csvfile:
        
        # creating a csv reader object
        csvreader = csv.reader(csvfile)
        
        # extracting field names through first row
        fields = next(csvreader)
        

        avr_index = -1
        try:
            avr_index = fields.index(target_column)
        except:
            tools.errorAndExit(f"{target_column} is NOT in the CSV header")

        # print("=======", csvreader)
        for row in csvreader:
            rows.append(row)

        P_SOC_power_W = 0
        for target_rail in DAQ_target:
            #print(type(rail), rail)
            
            for power_rail_index in range(len(rows)-1, -1, -1):
                t_rail = rows[power_rail_index]

                if t_rail[0]== target_rail:
                    power_data[target_rail] = float(t_rail[avr_index])
                    if target_rail == DAQ_target["SOC_POWER_RAIL_NAME"] :
                        P_SOC_power_W = power_data[target_rail]
                    break
                    
    # this need to be updated for ARL
    if P_SOC_power_W > 0 and "Run Time" in power_data:
        power_data['Energy (J)'] = P_SOC_power_W * power_data["Run Time"]

    power_obj['power_path'] = csv_path
    return power_obj


def parseHopperRuntime(result_path, DAQ_target) :
    
    result_json = tools.jsonLoader(result_path, None)
    if "flexlogger" in result_json:
        return result_json["flexlogger"]["timing"]["duration gather window"]
    else:
        return None
