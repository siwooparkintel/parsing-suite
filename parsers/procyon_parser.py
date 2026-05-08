import zipfile
import xml.etree.ElementTree as ET
import parsers.tools as tools


def readXMLfile(abs_path) :

    tree = ET.parse(abs_path)
    root = tree.getroot()
    procyon_score_list = list()
    # Prefer per-pass score when available; otherwise use the aggregate score.
    preferred_tags = [
        "OfficeProductivityOneHourBatteryConsumptionPerformanceScoreForPass",
        "OfficeProductivityOneHourBatteryConsumptionPerformanceScore",
    ]

    score = None
    for tag in preferred_tags:
        elems = root.findall(".//" + tag)
        if elems:
            value = elems[-1].text
            if value is not None and value.strip() != "":
                score = value.strip()
                break

    # Fallback for future Procyon variants that keep the same score suffix.
    if score is None:
        for elem in root.iter():
            if elem.tag.endswith("PerformanceScoreForPass") or elem.tag.endswith("PerformanceScore"):
                if elem.text is not None and elem.text.strip() != "":
                    score = elem.text.strip()

    if score is not None:
        return tools.tryIntifNumber(score)
    else :
        print(f"[procyon_parser] No valid score found in: {abs_path}")
        return None


def readArielleResult(abs_path) :
    # abs_path points to a .procyon-result file, which is a ZIP archive.

    arielle_data = dict()

    with zipfile.ZipFile(abs_path) as zf:
        arielle_names = [name for name in zf.namelist() if name.lower().endswith('arielle.xml')]
        if not arielle_names:
            print(f"[procyon_parser] 'Arielle.xml' not found inside: {abs_path}")
            return
        with zf.open(arielle_names[0]) as xml_file:
            xml_bytes = xml_file.read()

    root = ET.fromstring(xml_bytes)

    for elem in root.iter('secondary_result'):
        result_type = elem.get('result_type', '').strip()
        quantity = elem.get('quantity', '').strip()
        # Use quantity as key when available, fall back to result_type
        key = quantity if quantity else result_type
        if not key:
            continue
        unit = elem.get('unit', '').strip()
        value_text = elem.text.strip() if elem.text and elem.text.strip() != '' else ''
        try:
            f = float(value_text)
            value_out = int(f) if f == int(f) else round(f, 3)
        except (ValueError, TypeError):
            value_out = value_text
        arielle_data[key] = f"{value_out} {unit}".strip() if unit else value_out

    return arielle_data

def parseProcyonResultScore(dataset, abs_path) :
    if "procyon_score_obj" not in dataset :
        dataset["procyon_score_obj"] = dict()

    dataset["procyon_score_obj"]["procyon_overall_score"] = readXMLfile(abs_path)
    dataset["procyon_score_obj"]['procyon_score_path'] = abs_path

def parseProcyonResultArielle(dataset, abs_path) :
    if "procyon_arielle_obj" not in dataset :
        dataset["procyon_arielle_obj"] = dict()

    dataset["procyon_arielle_obj"]["procyon_arielle_data"] = readArielleResult(abs_path)
    dataset["procyon_arielle_obj"]["procyon_arielle_path"] = abs_path
    
