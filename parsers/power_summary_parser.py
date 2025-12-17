import csv
import parsers.tools as tools


fields = []
rows = []

# for LNL
AVERAGE = "Average"


def parsePowerSummaryCSV(csv_path, DAQ_target) :
    
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
            avr_index = fields.index(AVERAGE)
        except:
            tools.errorAndExit(f"{AVERAGE} is NOT in the CSV header")

        # print("=======", csvreader)
        for row in csvreader:
            rows.append(row)

        P_SOC = 0
        for target_rail in DAQ_target:
            #print(type(rail), rail)
            
            for power_rail_index in range(len(rows)-1, -1, -1):
                t_rail = rows[power_rail_index]
                # print(power_rail_index, type(rows[power_rail_index]), rows[power_rail_index], target_rail)
                if t_rail[0]== target_rail:
                    power_data[target_rail] = float(t_rail[avr_index])
                    if target_rail.find("P_SOC") >= 0 or target_rail.find("P_MCP") >= 0 :
                        P_SOC = power_data[target_rail]
                    break
                    
        # this need to be updated for ARL
        if P_SOC > 0 and "Run Time" in power_data:
            power_data['Energy (J)'] = P_SOC * power_data["Run Time"]
        # power_data['Eng(J)/Frame'] = None

        power_obj['file_path'] = csv_path
        # power_collection['data_type'] 
        return power_obj


