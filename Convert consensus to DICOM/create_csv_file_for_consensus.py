# Creates a CSV file with all structures for each overlap nii.gz CT image

import os
import sys
import pandas as pd

def find_existing_structures(folder):

    existing_structures = set()
    for file in os.listdir(folder):
        if file.endswith("_overlap.nii.gz"):
            structure_name = file.replace("_overlap.nii.gz", "")
            existing_structures.add(structure_name)
    return existing_structures

def filter_csv_for_each_folder(base_folder, csv_file):
    
    df = pd.read_csv(csv_file)
    
    for root, dirs, _ in os.walk(base_folder):
        for folder in dirs:
            folder_path = os.path.join(root, folder)
            existing_structures = find_existing_structures(folder_path)
            print(existing_structures)
            if existing_structures:
                df_filtered = df[df['label_name'].str.lower().isin(existing_structures)]
                print(df['label_name'])
                output_csv_path = os.path.join(folder_path, "filtered_structures.csv")
                df_filtered.to_csv(output_csv_path, index=False)
                print(f"Filtered CSV saved to: {output_csv_path}")

if len(sys.argv) != 3:
    print("Usage: python script.py <base_folder> <csv_file>")
    sys.exit(1)

base_folder = sys.argv[1]
csv_file = sys.argv[2]

filter_csv_for_each_folder(base_folder, csv_file)