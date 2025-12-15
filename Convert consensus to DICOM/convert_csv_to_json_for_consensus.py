#Generate json out of csv
import os
import json
import pandas as pd
import re
import sys

def process_csv_to_json(csv_path, algorithm, overview_csv):
    
    df = pd.read_csv(csv_path, delimiter=",")   
    df_overview = pd.read_csv(overview_csv, delimiter=",") 
    print(df_overview.columns)
    print(f"Processing CSV: {csv_path}")
    print(df.columns)

    dcmqi_seg_dict = {
        "ContentCreatorName": "IDC",
        "ClinicalTrialSeriesID": "Session1",
        "ClinicalTrialTimePointID": "1",
        "ClinicalTrialCoordinatingCenterName": "IDC",
        "SeriesDescription": "Multi-organ AI segmentation consensus",
        "SeriesNumber": "300",
        "InstanceNumber": "1",
        "segmentAttributes": []
    }

    for index, row in df.iterrows():
        try:
            rgb = [int(num) for num in re.findall(r'\d+', str(row['recommendedDisplayRGBValue']))]
        except (TypeError, ValueError):
            print(f"Warning: Failed to parse RGB value in row {index}: {row}")

        segment_attributes = {
            "labelID": 1,
            "SegmentDescription": f"{row['label_name']} : consensus of {df_overview.loc[df_overview['final_label'] == row['label_name'], 'models'].iloc[0] if not df_overview.loc[df_overview['final_label'] == row['label_name'], 'models'].empty else 'no matching models'} ",
            "SegmentLabel": row['label_name'],
            "SegmentAlgorithmType": "AUTOMATIC",
            "SegmentAlgorithmName": "Consensus segmentation by overlap",
            "SegmentedPropertyCategoryCodeSequence": {
                "CodeValue": str(int(row['Category.CodeValue'])),
                "CodingSchemeDesignator": row['Category.CodingSchemeDesignator'],
                "CodeMeaning": row['Category.CodeMeaning']
            },
            "SegmentedPropertyTypeCodeSequence": {
                "CodeValue": str(int(row['Type.CodeValue'])),
                "CodingSchemeDesignator": row['Type.CodingSchemeDesignator'],
                "CodeMeaning": row['Type.CodeMeaning']
            },
            "recommendedDisplayRGBValue": rgb
        }

        if not pd.isna(row.get('TypeModifier.CodeValue', None)):
            segment_attributes["SegmentedPropertyTypeModifierCodeSequence"] = {
                "CodeValue": str(int(row['TypeModifier.CodeValue'])),
                "CodingSchemeDesignator": row['TypeModifier.CodingSchemeDesignator'],
                "CodeMeaning": row['TypeModifier.CodeMeaning']
            }

        dcmqi_seg_dict["segmentAttributes"].append([segment_attributes])

    output_folder = os.path.dirname(csv_path)
    json_filename = f"{algorithm}-dcmqi_seg_dict.json"
    output_path = os.path.join(output_folder, json_filename)

    with open(output_path, 'w', encoding='utf-8') as outfile:
        json.dump(dcmqi_seg_dict, outfile, indent=2)

    print(f"JSON saved to: {output_path}")

def process_all_csv_in_folders(base_folder, algorithm, overview_csv):
    for root, _, files in os.walk(base_folder):
        for file in files:
            if file.endswith(".csv"):
                csv_path = os.path.join(root, file)
                process_csv_to_json(csv_path, algorithm, overview_csv)

algorithm = "Consensus"

if len(sys.argv) != 3:
    print("Usage: python script.py <base_folder> <overview_csv>")
    sys.exit(1)

base_folder = sys.argv[1]
overview_csv = sys.argv[2]

process_all_csv_in_folders(base_folder, algorithm, overview_csv)