#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from idc_index import index
import glob
import json
import logging
import matplotlib.pyplot as plt
import multiprocessing
import nibabel as nib
import numpy as np
#import nvidia_smi
import os
from pathlib import Path
import pandas as pd
import psutil
import pydicom
from pydicom.filereader import dcmread
from pydicom.sr.codedict import codes
from pydicom.uid import generate_uid
import radiomics
from radiomics import featureextractor, generalinfo
import random
import re
import shutil
import SimpleITK as sitk
import subprocess
import sys
import time
from time import sleep, asctime, localtime
from tqdm import tqdm
from tqdm.contrib.concurrent import process_map

# -------------------------------------------------------------------------
# 1) Convert SEG and CT Files to nifti files
# -------------------------------------------------------------------------
import os
import re
import subprocess

def mirror_and_convert_dicom(base_input_dir: str, base_output_dir: str, dcm2niix_path: str, segimage2itkimage_path: str):

    for root, dirs, files in os.walk(base_input_dir):
        rel_path = os.path.relpath(root, base_input_dir)
        out_dir = os.path.join(base_output_dir, rel_path)
        os.makedirs(out_dir, exist_ok=True)

        series_uid = None
        folder_name = os.path.basename(root) 
        match = re.match(r"CT_(.+)", folder_name)
        if match:
            series_uid = match.group(1)

        seg_files = [
            f for f in files
            if f.lower().endswith('.dcm') and f.startswith('SEG_')
        ]
        
        non_seg_dcms = [
            f for f in files
            if f.lower().endswith('.dcm') and not f.startswith('SEG_')
        ]

        
        if non_seg_dcms:
            if series_uid:
                nii_name_no_ext = f"CT_{series_uid}"  
            else:
                nii_name_no_ext = "CT"

            print(f"[INFO] Creating {nii_name_no_ext}.nii.gz in {out_dir} from DICOMs in {root}")
            cmd = [
                dcm2niix_path,
                "-z", "y",          
                "-m", "y",          
                "-f", nii_name_no_ext,
                "-o", out_dir,
                root
            ]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] dcm2niix failed in {root}: {e}")

        
        for seg_file in seg_files:
            seg_path = os.path.join(root, seg_file)
            seg_basename = os.path.splitext(seg_file)[0]
            seg_output_folder = os.path.join(out_dir, seg_basename)
            os.makedirs(seg_output_folder, exist_ok=True)

            print(f"[INFO] Creating NIfTI segmentation in {seg_output_folder} from {seg_path}")
            cmd2 = [
                segimage2itkimage_path,
                "--inputDICOM", seg_path,
                "--outputDirectory", seg_output_folder,
                "--outputType", "nii",
                "--mergeSegments"
            ]
            try:
                subprocess.run(cmd2, check=True)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] segimage2itkimage failed for {seg_path}: {e}")



# -------------------------------------------------------------------------
# 2) Load Code-Mappings (TotalSegmentator SNOMED, Radiomics Feature-Classes)
# -------------------------------------------------------------------------

'''totalsegmentator_segments_code_mapping_df = pd.read_csv(
    "https://raw.githubusercontent.com/wasserth/TotalSegmentator/1691bb8cd27a9ab78c2da3acef4dddf677c7dd24/resources/totalsegmentator_snomed_mapping.csv",
    dtype={"SegmentedPropertyTypeModifierCodeSequence.CodeValue": str},
)'''

totalsegmentator_radiomics_features_code_mapping_df = pd.read_csv(
    "https://raw.githubusercontent.com/ImagingDataCommons/CloudSegmentator/main/workflows/TotalSegmentator/resources/radiomicsFeaturesMaps.csv",
    index_col=[0]
)

logger = radiomics.logger
logger.setLevel(logging.WARNING)

idc_client=index.IDCClient()



# -------------------------------------------------------------------------
# 2) Radiomics-Extraction for all Labels of one Seg-File
# -------------------------------------------------------------------------
def log_failed_to_save_raw_radiomics_features(series_id: str) -> None:
    """
    Log an error message when the raw radiomics features for a given series fail to save.

    Args:
        series_id: The ID of the series.

    Returns:
        None. The error message is written to a log file.
    """
    # Define the path to the log file
    log_file_path = 'radiomics_error_file.txt'

    # Define the error message
    error_message = f"Error: Failed to save raw radiomics features for series {series_id}\n"

    # Append the error message to the log file
    with open(log_file_path, 'a') as f:
        f.write(error_message)

def is_series_greater_than_800_slices(series_id: str) -> bool:
    """
    Gets the SOPInstance count of the corresponding seriesInstanceUID from idc-index
    Refer to this query for additional columns available in idc-index!
    The reason why we are checking for 800 slices is whether to extract radiomics features
    using multiprocessor or sequentially. We validated that series with slices upto 800 slices
    work with out any issues with multiprocessor. However, above 800 we did find erratic
    behavior. While it is inefficient to do extract radiomics features sequentially, we
    expect it to work.

    https://github.com/ImagingDataCommons/idc-index/blob/main/queries/idc_index.sql

    Args:
    series_id: The DICOM Tag SeriesInstanceUID of the DICOM series to be processed.
    """

    query = f"""
    SELECT
    instanceCount
    FROM index
    WHERE SeriesInstanceUID = '{series_id}'
    """
    print(series_id)
    sopInstanceCount_df = idc_client.sql_query(query)
    if int(sopInstanceCount_df["instanceCount"][0]) > 800:
        return True
    else:
        return False
    
def ndarray_to_list(obj):

    """Convert a numpy array to a list.
       Helps for saving raw radiomics in a json file

    Args:
      obj: A numpy array.

    Returns:
      A list representation of the numpy array.
    """

    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

def resample_segmentation_to_ct(seg_file: Path, ct_file: Path):
    
    seg_image = sitk.ReadImage(str(seg_file))
    ct_image = sitk.ReadImage(str(ct_file))
    
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(ct_image)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    resampler.SetOutputPixelType(seg_image.GetPixelID())
    
    resampled_seg = resampler.Execute(seg_image)
    sitk.WriteImage(resampled_seg, str(seg_file))
    print(f"[INFO] Resampled segmentation saved to {seg_file}")

def get_label_id_body_part_df(meta_json_path: Path):

    with open(meta_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segmentAttributes", [])
    rows = []

    for seg_entry in segments:
        if isinstance(seg_entry, list):
            for seg in seg_entry:
                label_id = seg.get("labelID")
                body_part = seg.get("SegmentDescription")
                if label_id is not None and body_part is not None:
                    rows.append((label_id, body_part))

    df = pd.DataFrame(rows, columns=["label_id", "body_part"])
    return df


def extract_features_for_all_labels(series_id: str, ct_file: Path, seg_file: Path, json_file: Path, output_file: Path):
    
    resample_segmentation_to_ct(seg_file, ct_file)
    
    label_id_body_part_df = get_label_id_body_part_df(json_file)
    print(label_id_body_part_df)
    
    stats = {}
    raw_stats = {}
    
    labels = [
        int(x) for x in np.unique(nib.load(seg_file).get_fdata()).tolist() if x != 0
    ]
    
    func = partial(
        extract_radiomics_features_from_one_label,
        str(seg_file), 
        str(ct_file),       
        label_id_body_part_df,
    )

    if not is_series_greater_than_800_slices(series_id):
        # Use a multiprocessing pool to apply the function to all labels
        with multiprocessing.Pool() as pool:
            results = list(tqdm(pool.imap(func, labels), total=len(labels)))
    else:
        # Apply the function to all labels sequentially
        results = [func(label) for label in tqdm(labels)]

    # Process the results
    for body_part, mask_stats, raw_features in results:
        if any(v != 0 for v in mask_stats.values()):
            stats[body_part] = mask_stats
            raw_stats[body_part] = raw_features

    # Save the results to the output file
    with open(output_file, "w") as f:
        json.dump(stats, f, indent=4)
    try:
        # Save the raw features to a separate output file
        with open(output_file.rsplit(".", 1)[0] + "_raw.json", "w") as f:
            json.dump(raw_stats, f, indent=4, default=ndarray_to_list)
    except:
        log_failed_to_save_raw_radiomics_features(series_id)

def extract_radiomics_features_from_one_label(
    segmentation_file, image_file, label_id_body_part_df, label=None
):
    """
    Extract radiomics features from a given ct nifti image and segmentation file.

    Args:
        segmentation_file: The path to the segmentation file.
        image_file: The path to the ct nifti image file.
        label: The label of the region of interest in the segmentation file.

    Returns:
        A dictionary containing the extracted radiomics features.
    """
    body_part = label_id_body_part_df.loc[label_id_body_part_df["label_id"] == label][
        "body_part"
    ].values[0]
    try:
        # Define the settings for the feature extractor

        """the tolerance value is taken from the totalsegmentator repo
        # https://github.com/wasserth/TotalSegmentator/blob/master/totalsegmentator/statistics.py#L31
        """
        settings = {"geometryTolerance": 1e-3}

        # Create the feature extractor
        extractor = featureextractor.RadiomicsFeatureExtractor(**settings)

        # Get the list of shape and firstorder features
        shape_features = totalsegmentator_radiomics_features_code_mapping_df[
            totalsegmentator_radiomics_features_code_mapping_df[
                "pyradiomics_feature_class"
            ]
            == "shape"
        ]["feature"].tolist()
        firstorder_features = totalsegmentator_radiomics_features_code_mapping_df[
            totalsegmentator_radiomics_features_code_mapping_df[
                "pyradiomics_feature_class"
            ]
            == "firstorder"
        ]["feature"].tolist()

        # Enable the shape and firstorder features
        extractor.disableAllFeatures()
        extractor.enableFeaturesByName(
            shape=shape_features, firstorder=firstorder_features
        )
        # Extract the features
        raw_features = extractor.execute(
            str(image_file), str(segmentation_file), label=label
        )

        # Clean the feature names and round the values
        cleaned_features = {
            name.replace("original_", ""): round(float(value), 4)
            for name, value in raw_features.items()
            if name.startswith("original_")
        }
        mask_stats = {
            k: v.tolist() if isinstance(v, np.ndarray) else v
            for k, v in cleaned_features.items()
        }
    except Exception as e:
        print(
            f"WARNING: radiomics raised an exception (setting all features to 0): {e}"
        )
        cleaned_features = {feature: 0 for feature in shape_features}
        raw_features= {feature: 0 for feature in shape_features}
        mask_stats = {
            k: v.tolist() if isinstance(v, np.ndarray) else v
            for k, v in cleaned_features.items()
        }
    return body_part, mask_stats, raw_features


def process_ct_and_segments(base_output_dir_ct: str, base_output_dir_seg: str, base_output_dir_results: str):
    
    base_output_dir_ct = Path(base_output_dir_ct)
    base_output_dir_seg = Path(base_output_dir_seg)
    base_output_dir_results = Path(base_output_dir_results)

    for root, dirs, files in os.walk(base_output_dir_seg):
        root_path = Path(root)

        if "meta.json" not in files:
            continue

        seg_nifti_files = [f for f in files if f.endswith(".nii.gz") or f.endswith(".nii")]

        if not seg_nifti_files:
            continue

        if root_path.name.startswith("SEG_"):
            try:
                ct_rel_path = root_path.parent.relative_to(base_output_dir_seg)
            except ValueError:
                
                ct_rel_path = root_path.parent
        else:
            ct_rel_path = root_path.relative_to(base_output_dir_seg)

        ct_folder = base_output_dir_ct.joinpath(ct_rel_path)
        if not ct_folder.exists():
            print(f"[WARN] CT-Ordner {ct_folder} existiert nicht. Überspringe {root_path}.")
            continue

        ct_candidates = list(ct_folder.glob("CT*.nii*"))
        if not ct_candidates:
            print(f"[WARN] Keine CT-NIfTI in {ct_folder} gefunden. Überspringe {root_path}.")
            continue

        ct_nifti_file = ct_candidates[0]

        series_id = ct_folder.name.replace("CT_", "")

        meta_json_path = root_path / "meta.json"

        results_folder = base_output_dir_results.joinpath(root_path.relative_to(base_output_dir_seg))
        results_folder.mkdir(parents=True, exist_ok=True)

        for seg_file_name in seg_nifti_files:
            seg_file_path = root_path / seg_file_name
            seg_stem = seg_file_path.stem  
            output_file = results_folder / f"{seg_stem}_features.json" 

            extract_features_for_all_labels(
                series_id=str(series_id),
                ct_file=ct_nifti_file,
                seg_file=seg_file_path,
                json_file=meta_json_path,
                output_file=output_file
            )

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  Convert DICOM to NIfTI:\n"
            "    python radiomics_pipeline.py convert "
            "<dicom_input_dir> <dicom_output_dir> <dcm2niix_path> <segimage2itkimage_path>\n\n"
            "  Extract radiomics:\n"
            "    python radiomics_pipeline.py radiomics "
            "<ct_nifti_base_dir> <seg_nifti_base_dir> <results_dir>"
        )
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "convert":
        if len(sys.argv) != 6:
            print(
                "Usage:\n"
                "  python radiomics_pipeline.py convert "
                "<dicom_input_dir> <dicom_output_dir> "
                "<dcm2niix_path> <segimage2itkimage_path>"
            )
            sys.exit(1)

        dicom_input_dir = sys.argv[2]
        dicom_output_dir = sys.argv[3]
        dcm2niix_path = sys.argv[4]
        segimage2itkimage_path = sys.argv[5]

        mirror_and_convert_dicom(
            base_input_dir=dicom_input_dir,
            base_output_dir=dicom_output_dir,
            dcm2niix_path=dcm2niix_path,
            segimage2itkimage_path=segimage2itkimage_path,
        )

    elif mode == "radiomics":
        if len(sys.argv) != 5:
            print(
                "Usage:\n"
                "  python radiomics_pipeline.py radiomics "
                "<ct_nifti_base_dir> <seg_nifti_base_dir> <results_dir>"
            )
            sys.exit(1)

        ct_nifti_base_dir = sys.argv[2]
        seg_nifti_base_dir = sys.argv[3]
        results_dir = sys.argv[4]

        process_ct_and_segments(
            base_output_dir_ct=ct_nifti_base_dir,
            base_output_dir_seg=seg_nifti_base_dir,
            base_output_dir_results=results_dir,
        )

    else:
        print(f"Unknown mode '{mode}'. Use 'convert' or 'radiomics'.")
        sys.exit(1)
