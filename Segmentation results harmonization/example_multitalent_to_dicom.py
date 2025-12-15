import os
import json
import subprocess
import pydicom
import sys

if len(sys.argv) != 6:
    print(
        "Usage: python convert_to_dicom_seg.py "
        "<dicom_base_dir> <nifti_base_dir> <json_base_dir> "
        "<output_base_dir> <itkimage2segimage_path>"
    )
    sys.exit(1)

dicom_base_dir = sys.argv[1]
nifti_base_dir = sys.argv[2]
json_base_dir = sys.argv[3]
output_base_dir = sys.argv[4]
itkimage2segimage_path = sys.argv[5]

os.makedirs(output_base_dir, exist_ok=True)

def extract_dicom_metadata(dicom_folder):
    for dicom_file in os.listdir(dicom_folder):
        dicom_path = os.path.join(dicom_folder, dicom_file)
        try:
            ds = pydicom.dcmread(dicom_path)
            series_description = getattr(ds, "SeriesDescription", "Unknown")
            series_number = getattr(ds, "SeriesNumber", "300")
            return series_description, str(series_number)
        except:
            continue
    return "Unknown", "300"

for study_id in os.listdir(nifti_base_dir):
    study_path = os.path.join(nifti_base_dir, study_id)

    if not os.path.isdir(study_path) or study_id.startswith("."):
        continue

    json_filename = "MultiTalent-dcmqi_seg_dict.json"
    json_path = os.path.join(json_base_dir, json_filename)

    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}. Skipping...")
        continue

    with open(json_path, "r") as f:
        metadata = json.load(f)

    expected_segments = [
        segment[0]["SegmentDescription"] for segment in metadata["segmentAttributes"]
    ]

    nifti_files = [
        os.path.join(study_path, f) for f in os.listdir(study_path) if f.endswith(".nii.gz")
    ]
    
    nifti_mapping = {os.path.basename(f).replace(".nii.gz", ""): f for f in nifti_files}

    sorted_nifti_files = [nifti_mapping[seg] for seg in expected_segments if seg in nifti_mapping]

    if not sorted_nifti_files:
        print(f"No matching NIfTI files found for study {study_id}. Skipping...")
        continue

    output_dir = os.path.join(output_base_dir, study_id)
    os.makedirs(output_dir, exist_ok=True)

    dicom_ct_folder = None  

    for patient_folder in os.listdir(dicom_base_dir):
        if patient_folder.startswith("."):
            continue

        patient_path = os.path.join(dicom_base_dir, patient_folder)
        if not os.path.isdir(patient_path):
            continue

        for study_folder in os.listdir(patient_path):
            if study_folder.startswith("."):
                continue

            study_folder_path = os.path.join(patient_path, study_folder)
            if not os.path.isdir(study_folder_path):
                continue

            for series_folder in os.listdir(study_folder_path):
                if series_folder.startswith("."):
                    continue

                series_path = os.path.join(study_folder_path, series_folder)
                if not os.path.isdir(series_path):
                    continue

                if series_folder.startswith("CT_"):
                    ct_id = series_folder.split("_")[1] 
                    if ct_id == study_id:
                        dicom_ct_folder = series_path
                        print(f"Found DICOM CT folder: {dicom_ct_folder} for CT {study_id}")
                        break

            if dicom_ct_folder:
                break
        if dicom_ct_folder:
            break

    if dicom_ct_folder:
        output_seg_file = os.path.join(output_dir, f"SEG_MultiTalent_CT_{study_id}.dcm")
        series_description, series_number = extract_dicom_metadata(dicom_ct_folder)
                
        with open(json_path, 'r') as json_file:
            json_data = json.load(json_file)
        
        json_data["SeriesNumber"] = str(int(series_number) * 100)
        json_data["SeriesDescription"] = f"Multitalent - {series_description}"

        with open(json_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=2)

        print(f"Converting -> {output_seg_file} using DICOM input {dicom_ct_folder}")

        command = [
            itkimage2segimage_path,
            "--inputImageList", ",".join(sorted_nifti_files),
            "--inputMetadata", json_path,
            "--inputDICOMDirectory", dicom_ct_folder,
            "--outputDICOM", output_seg_file,
            "--verbose"
        ]

        try:
            subprocess.run(command, check=True)
            print(f"DICOM segmentation saved: {output_seg_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error during conversion for study {study_id}: {e}")
    else:
        print(f"No matching DICOM CT folder found for CT {study_id}. Skipping...")

print("Conversion completed successfully!")
