# Converts consensus NIfTI files into DICOM SEG
import os
import sys
import json
import subprocess

def find_nifti_files(base_dir):
    nifti_data = []
    for root, _, files in os.walk(base_dir):
        nii_files = [os.path.join(root, f) for f in files if f.endswith(".nii.gz")]
        if nii_files:
            nifti_data.append((root, nii_files))
    return nifti_data

def find_matching_dicom_folder(nifti_folder, dicom_base_dir):
    ct_id = os.path.basename(nifti_folder).split("_")[-1] 
    for root, _, _ in os.walk(dicom_base_dir):
        if ct_id in root:
            return root
    return None

def create_output_folder_structure(nifti_folder, base_dir, output_base):
    relative_path = os.path.relpath(nifti_folder, base_dir)
    output_folder = os.path.join(output_base, relative_path)
    os.makedirs(output_folder, exist_ok=True)
    return output_folder

def convert_nifti_to_dicom(nifti_base_dir, output_base_dir, dicom_base_dir, itkimage2segimage_path):
    nifti_data = find_nifti_files(nifti_base_dir)

    if not nifti_data:
        print("No NIfTI files found. Please check the directory structure.")
        return

    for folder, nii_files in nifti_data:
        print(f"\nProcessing NIfTI files in: {folder}")

        json_file = os.path.join(folder, "Overlap-dcmqi_seg_dict.json")
        if not os.path.exists(json_file):
            print(f"Missing JSON metadata in {folder}, skipping...")
            continue

        with open(json_file, "r") as f:
            json_data = json.load(f)

        expected_structures = [segment[0]["SegmentLabel"].lower() for segment in json_data["segmentAttributes"]]

        nifti_mapping = {os.path.basename(f).replace("_overlap.nii.gz", "").lower(): f for f in nii_files}

        missing_files = [structure for structure in expected_structures if structure not in nifti_mapping]
        if missing_files:
            print(f"Missing NIfTI files for expected structures: {missing_files}")

        sorted_nifti_files = [nifti_mapping[structure] for structure in expected_structures if structure in nifti_mapping]

        print(f"Number of matched and sorted NIfTI files: {len(sorted_nifti_files)}")

        if not sorted_nifti_files:
            print(f"No matching NIfTI files found for {folder}, skipping...")
            continue

        output_folder = create_output_folder_structure(folder, nifti_base_dir, output_base_dir)
        dicom_ct_folder = find_matching_dicom_folder(folder, dicom_base_dir)

        if not dicom_ct_folder:
            print(f"No matching DICOM folder found for {folder}, skipping...")
            continue

        output_dicom = os.path.join(output_folder, "SEG_Consensus.dcm")

        print(f"Converting NIfTI → DICOM SEG for folder: {folder}")

        command = [
            itkimage2segimage_path,
            "--inputImageList", ",".join(sorted_nifti_files),
            "--inputMetadata", json_file,
            "--inputDICOMDirectory", dicom_ct_folder,
            "--outputDICOM", output_dicom,
            "--verbose"
        ]

        try:
            subprocess.run(command, check=True)
            print(f"SEG DICOM saved at: {output_dicom}")
        except subprocess.CalledProcessError as e:
            print(f"Conversion failed for {folder}: {e}")

    print("Conversion finished successfully!")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python script.py <nifti_base_dir> <output_base_dir> <dicom_base_dir> <itkimage2segimage_path>")
        sys.exit(1)

    nifti_base_dir = sys.argv[1]
    output_base_dir = sys.argv[2]
    dicom_base_dir = sys.argv[3]
    itkimage2segimage_path = sys.argv[4]

    convert_nifti_to_dicom(nifti_base_dir, output_base_dir, dicom_base_dir, itkimage2segimage_path)