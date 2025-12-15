import os
import subprocess
import json
import numpy as np
import pandas as pd
import SimpleITK as sitk
from functools import reduce
import sys

def extract_all_segments(dicom_files, temp_output_folder):
    os.makedirs(temp_output_folder, exist_ok=True)

    for dicom_file in dicom_files:
        dicom_filename = os.path.basename(dicom_file).replace(".dcm", "")
        dicom_output_folder = os.path.join(temp_output_folder, dicom_filename)
        os.makedirs(dicom_output_folder, exist_ok=True)

        if os.listdir(dicom_output_folder):
            print(f"Segments already extracted for {dicom_file}")
            continue

        command = [
            "/Users/lenagiebeler/Downloads/dcmqi-1.3.4-mac/bin/segimage2itkimage",
            "--inputDICOM", dicom_file,
            "--outputDirectory", dicom_output_folder
        ]
        try:
            subprocess.run(command, check=True)
            print(f"All segments extracted to: {dicom_output_folder}")
        except subprocess.CalledProcessError as e:
            print(f"Error extracting segments from {dicom_file}: {e}")
            return None

    return temp_output_folder

def load_meta_json(json_path):
    with open(json_path, "r") as f:
        meta_data = json.load(f)
    
    label_map = {}
    for segment in meta_data["segmentAttributes"]:
        segment_info = segment[0]
        segment_label = segment_info["SegmentDescription"].split(":")[-1].strip().lower().replace(" ", "_")
        label_id = str(segment_info["labelID"])
        label_map[label_id] = segment_label
    
    return label_map

def load_nrrd_segmentation(nrrd_file):
    if nrrd_file and os.path.exists(nrrd_file):
        return sitk.ReadImage(nrrd_file)
    return None

def resample_image(image, reference_image):
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference_image)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    #resampler.SetOutputPixelType(sitk.sitkUInt8)
    resampled_image = resampler.Execute(image)
    binary_image = sitk.BinaryThreshold(resampled_image, lowerThreshold=1, upperThreshold=255, insideValue=1, outsideValue=0)
    return binary_image

def extract_model_name(file_name):
    models = {"TotalSegmentator_v15": "TotalSegmentator_1.5", "TS_2.6": "TotalSegmentator_2.6", "OMAS": "OMAS", "MOOSE": "Moose", "Auto3DSeg": "Auto3Dseg", "MultiTalent": "MultiTalent"}
    for key, value in models.items():
        if key in file_name:
            return value
    return "Unknown"

def process_ct_folders(base_folder, csv_file):
    df_structures = pd.read_csv(csv_file, delimiter=",")
    structures_list = df_structures[df_structures["count"] == 6]["final_label"].str.lower().tolist()
    
    results = []

    for root, dirs, _ in os.walk(base_folder):
        for ct_folder in dirs:
            if ct_folder.startswith("CT_"):
                print(f"Processing CT folder: {ct_folder}")    
                series_uid = ct_folder.split("_")[-1]
                ct_path = os.path.join(root, ct_folder)

                if not os.path.exists(ct_path):
                    continue

                segmentation_files = [os.path.join(ct_path, f) for f in os.listdir(ct_path) if f.endswith(".dcm")]

                if not segmentation_files:
                    continue

                temp_output_folder = os.path.join(ct_path, "temp_nifti")
                
                print(f"Converting all DICOM segmentations to NIfTI for {ct_folder}")
                temp_output_folder = extract_all_segments(segmentation_files, temp_output_folder)
                if not temp_output_folder:
                    continue

                nifti_files = {}
                for file in segmentation_files:
                    model_name = extract_model_name(file)
                    dicom_filename = os.path.basename(file).replace(".dcm", "")
                    subdir_path = os.path.join(temp_output_folder, dicom_filename)
                    
                    if os.path.isdir(subdir_path):
                        meta_json_path = os.path.join(subdir_path, "meta.json")
                        if os.path.exists(meta_json_path):
                            label_map = load_meta_json(meta_json_path)
                            nifti_data = {os.path.basename(f).split(".")[0]: os.path.join(subdir_path, f)
                                          for f in os.listdir(subdir_path) if f.endswith(".nrrd")}
                            
                            for label_id, structure_name in label_map.items():
                                if structure_name in structures_list and label_id in nifti_data:
                                    nifti_path = nifti_data[label_id]
                                    nifti_files.setdefault(structure_name, []).append((model_name, nifti_path))
                
                for structure_name, paths in nifti_files.items():
                    print(f"Processing structure: {structure_name}")
                    if len(paths) < 6:
                        print(f"Skipping {structure_name}, not all models available.")
                        print(len(paths))
                        print(paths)
                        continue
                    
                    model_masks = {}
                    auto3dseg_path = next((path for model, path in paths if model == "Auto3Dseg"), None)
                    reference_image = load_nrrd_segmentation(auto3dseg_path)
                    for model_name, file in paths:
                        image = load_nrrd_segmentation(file)
                        model_masks[model_name] = resample_image(image, reference_image)
                    
                    overlap = reduce(sitk.And, [mask for mask in model_masks.values()])

                    overlap_filter = sitk.LabelOverlapMeasuresImageFilter()
                    for model, mask in model_masks.items():
                        overlap_filter.Execute(mask, overlap)
                        dice = overlap_filter.GetDiceCoefficient()
                        results.append({
                            "CT_SeriesInstanceUID": series_uid,
                            "Structure": structure_name,
                            "Model": model,
                            "Dice_Score": dice
                        })
    
    df_results = pd.DataFrame(results)
    df_pivot = df_results.pivot_table(values="Dice_Score", index=["Structure"], columns=["CT_SeriesInstanceUID", "Model"], aggfunc="first")
    output_path = os.path.join(base_folder, "segmentation_dice_scores_pivot.csv")
    df_pivot.to_csv(output_path)
    print(f"Results saved to: {output_path}")
    return output_path


if len(sys.argv) != 3:
    print("Usage: python script.py <base_folder> <csv_file>")
    sys.exit(1)

base_folder = sys.argv[1]
csv_file = sys.argv[2]

process_ct_folders(base_folder, csv_file)
