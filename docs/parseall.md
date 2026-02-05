

# ParseAll.py : 
This is developed to parse and summarize all ETL/Power/Socwatch/PCIe_Only data into one Excel file to help with the data selection process. Power comes first; if the power data is collected with Socwatch or PCIe-only Socwatch, they will be parsed and presented in one column. Currently, ETL is not being post-processed.

### Acceptable Folder Structures
-----------------------------------------------------------------------------------------------------------------------------------------
##### [Folder Structure 1 (flat layer)]

It requires to provide upto "Baseline" (or different name) folder as a input  and children folders are a flat level. each folder can be, ETL, Power, PCIe, or Socwatch
<pre>
WW2534.1_somedata ├── Baseline ├── CataV3_000 (ETL + Power)
                               ├── CataV3_001 (Power)
                               ├── CataV3_002 (Power)
                               ├── CataV3_003 (Power)
                               ├── CataV3_004 (Socwatch + Power)
                               ├── CataV3_005 (Socwatch + Power)
                               ├── CataV3_006 (Socwatch + Power)
                               ├── CataV3_007 (PCIe Only Socwatch + Power)
                               └── CataV3_008 (PCIe Only Socwatch + Power)
</pre>
##### [Folder Structure 2 (2 layers)]

It requires to provide upto "Baseline" (or different name) folder as a input and children folders can be grouped as ETL, Power, Socwatch or PCIe (exact folder names are needed here)
<pre>
WW2534.1_somedata ├── Baseline  ├── ETL          └── CataV3_000 (ETL + Power)
                                ├── Power        ├── CataV3_001 (Power)
                                │                ├── CataV3_002 (Power)
                                │                └── CataV3_003 (Power)
                                ├── Socwatch     ├── CataV3_004 (Socwatch + Power)
                                │                ├── CataV3_005 (Socwatch + Power)
                                │                └── CataV3_006 (Socwatch + Power)
                                └── PCIe         ├── CataV3_007 (PCIe Only Socwatch + Power)
                                                 └── CataV3_008 (PCIe Only Socwatch + Power)
</pre>

### Arguments
##### -i, --input [required] : full path to the folder
##### -o, --output [recommended]: full path to the output excel file location and filename prefix. "_allPower_v.xlsx" will be added in the file name.
##### -d, --daq [recommended]: full path and json file name. it externalizes the DAQ_target dictionary object as a json since each DAQ can have different power measure rail names.
##### -st, --swtarget [optional]: full path and json file name that contains a list of dictionary object that contains "look up" text in the socwatch summary file to parse. if the dictionary has "buckets" list it will bucketize the p-states into defined range group.
##### -hb, --hobl [optional]: If data is collected through HOBL, it should have .PASS or .FAIL empty file, and using them to set a data group is much more accurate, so recommended to use it if it is collected via HOBL. 
##### [Powershell example]
```powershell

PS C:\Users\siwoopar\code\ParseCSV> py ParseAll.py -i \\255.255.255.255\Pnpext\Siwoo\data\WW2526.5_CataV3_IT_CCA_LC\Baseline -o .\test\2nd_folders -d .\config\DAQ_target_LNL09-04DUT.json -st .\config\Socwatch_targets.json

```

### DAQ Rail Name Adjustment (-d, --daq)

Each DAQ power rail name can be different. To summarize the targeted rails, modify the "DAQ_target" object in ParseAll.py or provide the -d flag with the full path and JSON file name. Lastly if you add "Rum Time" in the DAQ_target, it will provide the total energy (J) used during the workload.

```python

DAQ_target = {
"P_SSD":-1,
"V_VAL_VCC_PCORE":-1,
"I_VAL_VCC_PCORE":-1,
"V_VAL_VCC_ECORE":-1,
"I_VAL_VCC_ECORE":-1,
"V_VAL_VCCSA":-1,
"I_VAL_VCCSA":-1,
"V_VAL_VCCGT":-1,
"I_VAL_VCCGT":-1,
"P_VCC_PCORE":-1,
"P_VCC_ECORE":-1,
"P_VCCSA":-1,
"P_VCCGT":-1,
"P_VCCL2":-1,
"P_VCC1P8":-1,
"P_VCCIO":-1,
"P_VCCDDRIO":-1,
"P_VNNAON":-1,
"P_VNNAONLV":-1,
"P_VDDQ":-1,
"P_VDD2H":-1,
"P_VDD2L":-1,
"P_V1P8U_MEM":-1,
"P_SOC+MEMORY":-1,
"Run Time":-1
}

```

### Socwatch Target Table List Adjustment (-st, --swtarget)

If it is not provided, it uses an internally implemented target object, which works well. However, detection wording changes are possible by Socwatch developers. A user can add or remove the targeted socwatch summary table data here; bucketizing a large range of p-states is also possible. One important thing to get the best performance out of the parser is to match the order of the socwatch summary. If it is matched, it only loops once and parses every table together in that one loop. However, if not matched, it wastes the loop and loops again to check its existence.

```python

socwatch_targets = [
    {"key": "CPU_model", "lookup": "CPU native model"},
    {"key": "PCH_SLP50", "lookup": "PCH SLP-S0 State Summary: Residency (Percentage and Time)"},
    {"key": "S0ix_Substate", "lookup": "S0ix Substate Summary: Residency (Percentage and Time)"},
    {"key": "PKG_Cstate", "lookup": "Platform Monitoring Technology CPU Package C-States Residency Summary: Residency (Percentage and Time)"},
    {"key": "Core_Cstate", "lookup": "Core C-State Summary: Residency (Percentage and Time)"},
    {"key": "Core_Concurrency", "lookup": "CPU Core Concurrency (OS)"},
    {"key": "ACPI_Cstate", "lookup": "Core C-State (OS) Summary: Residency (Percentage and Time)"},
    {"key": "OS_wakeups", "lookup": "Processes by Platform Busy Duration"},
    {"key": "CPU-iGPU", "lookup": "CPU-iGPU Concurrency Summary: Residency (Percentage and Time)"},
    {"key": "CPU_Pavr", "lookup": "CPU P-State Average Frequency (excluding CPU idle time)"},
    {"key": "CPU_Pstate", "lookup": "CPU P-State/Frequency Summary: Residency (Percentage and Time)"},
    {"key": "RC_Cstate", "lookup": "Integrated Graphics C-State  Summary: Residency (Percentage and Time)"},
    {"key": "DDR_BW", "lookup": "DDR Bandwidth Requests by Component Summary: Average Rate and Total"},
    {"key": "IO_BW", "lookup": "IO Bandwidth Summary: Average Rate and Total"},
    {"key": "VC1_BW", "lookup": "Display VC1 Bandwidth Summary: Average Rate and Total"},
    {"key": "NPU_BW", "lookup": "Neural Processing Unit (NPU) to Memory Bandwidth Summary: Average Rate and Total"},
    {"key": "Media_BW", "lookup": "Media to Network on Chip (NoC) Bandwidth Summary: Average Rate and Total"},
    {"key": "IPU_BW", "lookup": "Image Processing Unit (IPU) to Network on Chip (NoC) Bandwidth Summary: Average Rate and Total"},
    {"key": "CCE_BW", "lookup": "CCE to Network on Chip (NoC) Bandwidth Summary: Average Rate and Total"},
    {"key": "GT_BW", "lookup": "Chip GT Bandwidth Summary: Average Rate and Total"},
    {"key": "D2D_BW", "lookup": "Chip Die to Die Bandwidth Summary: Average Rate and Total"},
    {"key": "CPU_temp", "lookup": "Temperature Metrics Summary - Sampled: Min/Max/Avg"},
    {"key": "SoC_temp", "lookup": "SoC Domain Temperatures Summary - Sampled: Min/Max/Avg"},
    {"key": "NPU_Dstate", "lookup": "Neural Processing Unit (NPU) D-State Residency Summary: Residency (Percentage and Time)"},
    {"key": "PMC+SLP_S0", "lookup": "PCH Active State (as percentage of PMC Active plus SLP_S0 Time) Summary: Residency (Percentage)"},
    {"key": "DC_count", "lookup": "Dynamic Display State Enabling"},
    {"key": "Media_Cstate", "lookup": "Media C-State Residency Summary: Residency (Percentage and Time)"},
    {"key": "NPU_Pstate", "lookup": "Neural Processing Unit (NPU) P-State Summary - Sampled: Approximated Residency (Percentage)", "buckets":["0", "1900", "1901-2900", "2901-3899", "3900"]},
    {"key": "MEMSS_Pstate", "lookup": "Memory Subsystem (MEMSS) P-State Summary - Sampled: Approximated Residency (Percentage)"},
    {"key": "NoC_Pstate", "lookup": "Network on Chip (NoC) P-State Summary - Sampled: Approximated Residency (Percentage)", "buckets":["400", "401-1049", "1050"]},
    {"key": "iGFX_Pstate", "lookup": "Integrated Graphics P-State/Frequency Summary - Sampled: Approximated Residency (Percentage)", "buckets":["0", "400", "401-1799", "1800-2049", "2050"]}
]

```

### HOBL or Non-HOBL data (-hb, --hobl)
If the data is collected via HOBL, using this option to improve the data detection. It is empty flag, add it if it is hobl data or omit it if not.










[BACK](../)