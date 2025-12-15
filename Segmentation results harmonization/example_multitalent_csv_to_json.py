import json
import pandas as pd
import re
import sys
import os

df = pd.read_csv(sys.argv[1], delimiter=";")   

print(df.columns)

algorithm = sys.argv[2]
output_dir = sys.argv[3]

dcmqi_seg_dict = {
    "ContentCreatorName": algorithm,
    "ClinicalTrialSeriesID": "Session1",
    "ClinicalTrialTimePointID": "1",
    "ClinicalTrialCoordinatingCenterName": algorithm,
    "SeriesDescription": f"{algorithm} segmentation",
    "SeriesNumber": "300",
    "InstanceNumber": "1",
    "segmentAttributes": []
}

for index, row in df.iterrows():
    try:
        rgb = [int(num) for num in re.findall(r'\d+', row['recommendedDisplayRGBValue'])]
    except (TypeError, ValueError):
        print(f"Error parsing RGB value for row {index}: {row}")

    segment_attributes = {
        "labelID": int(row['label_id']),
        "SegmentDescription": row['multitalent_label_name'],
        "SegmentAlgorithmType": "AUTOMATIC",
        "SegmentAlgorithmName": algorithm,
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

output_path = os.path.join(output_dir, f"{algorithm}-dcmqi_seg_dict.json")
with open(output_path, 'w', encoding='utf-8') as outfile:
    json.dump(dcmqi_seg_dict, outfile, indent=2)