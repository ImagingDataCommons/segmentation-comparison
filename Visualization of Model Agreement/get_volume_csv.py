import os
import json
import pandas as pd
import sys

def parse_method(folder_name):
    s = folder_name[len("SEG_"):]
    if s.startswith("TS_"):
        parts = s.split('_', 2)
        if len(parts) >= 2:
            return parts[0] + '_' + parts[1]
        else:
            return s  
    else:
        parts = s.split('_', 1)
        return parts[0]  

def parse_case_id(folder_name):
    if folder_name.startswith("CT_"):
        return folder_name[len("CT_"):]
    return folder_name

def collect_volumes(base_dir):
    data_rows = []
    for root, dirs, files in os.walk(base_dir):
        for file_name in files:
            if file_name.endswith("_features.json"):
                json_path = os.path.join(root, file_name)
                path_parts = root.split(os.sep)
                method_name = None
                case_id = None

                for part in path_parts:
                    if part.startswith("SEG_"):
                        method_name = parse_method(part)
                    if part.startswith("CT_"):
                        case_id = parse_case_id(part)

                with open(json_path, "r") as f:
                    features_dict = json.load(f)

                for segment_name, metrics in features_dict.items():
                    volume = metrics.get("shape_VoxelVolume", None)
                    row = {
                        "segment": segment_name.split(" :")[0],
                        "method": method_name,
                        "volume": volume,
                        "caseID": case_id
                    }
                    data_rows.append(row)
    df = pd.DataFrame(data_rows, columns=["segment", "method", "volume", "caseID"])
    return df

def main():
    if len(sys.argv) != 3:
        print("Usage: python collect_volumes.py <features_reports_base_dir> <output_csv>")
        sys.exit(1)

    features_reports_base_dir = sys.argv[1]
    output_csv = sys.argv[2]

    df = collect_volumes(features_reports_base_dir)
    df.to_csv(output_csv, index=False)

    print(f"Volume CSV written to: {output_csv}")

if __name__ == "__main__":
    main()
