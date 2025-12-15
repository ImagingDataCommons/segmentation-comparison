# Scripts to Convert Consensus NIfTI Files into DICOM SEG Files

This folder contains three Python scripts used to convert the consensus NIfTI segmentations into DICOM SEG objects using **dcmqi**.  
The workflow consists of three stages:

1. **create_csv_file_for_consensus.py**  
   Creates a CSV containing only the structures available in the consensus NIfTI files, along with their corresponding metadata (SNOMED-CT codes) required for DICOM conversion.

2. **convert_csv_to_json_for_consensus.py**  
   Converts each  CSV into a dcmqi-compatible metadata JSON file.

3. **convert_consensus_to_dicom.py**  
   Combines consensus NIfTI masks + JSON metadata + original CT DICOM series into final DICOM SEG objects.

All scripts require **Python 3**, and the last step depends on **dcmqi (itkimage2segimage)**.

---

## Folder Structure

The scripts assume a consistent directory layout. If a different folder structure is used, **the scripts must be adapted accordingly**.

### 1. DICOM Base Directory
The original CT DICOM data is organized in a hierarchical structure that reflects the DICOM standard and is typically preserved when downloading data from IDC:
```
dicom_base/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│       └── CT_<SeriesInstanceUID>/
│           └── *.dcm
```

#### Explanation of each level

- **PatientID**  
  A subject identifier assigned by the dataset (e.g., NLST). Each patient folder may contain one or more imaging studies.
- **StudyInstanceUID**  
  A unique identifier for a specific imaging study. A study may include multiple imaging series.
- **CT_<SeriesInstanceUID>**  
  The folder containing a CT series. Its name begins with `CT_` followed by the `SeriesInstanceUID`.  
  This is the *leaf folder* that contains the individual `.dcm` files.
- **DICOM slice files (.dcm)**  
  These files represent the axial slices of the CT acquisition.

The consensus-to-DICOM conversion script uses the **SeriesInstanceUID** extracted from the folder name to match the segmentation folder to the correct CT series.

### 2. Consensus NIfTI Directory
Consensus segmentation outputs follow a parallel structure, organized by CT SeriesInstanceUID:
```
nifti_base/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│       └── CT_<SeriesInstanceUID>/
│           └── *_overlap.nii.gz
```

#### Explanation of each level

- **CT_<SeriesInstanceUID>**  
  Each folder corresponds to one CT series and must match the naming of the CT series folder in the DICOM directory.

- **<structure_name>_overlap.nii.gz**  
  One NIfTI file per anatomical structure. The structure name (before `_overlap`) is used in metadata.

---
## How the Scripts Work Together

The pipeline starts from two main data sources:

1. The **original CT DICOM data** (`dicom_base/`)
2. The **consensus NIfTI segmentations** (`nifti_base/`)

In addition, two CSV files are required:

- A **structure definition CSV** (e.g., `example_structure_codes.csv`) that defines each anatomical structure and its DICOM segmentation ontology codes (SNOMED-CT), including `label_name`, category/type codes, and `recommendedDisplayRGBValue`.
- A **model overview CSV** (e.g., `example_structures_overview_all_models.csv`) that lists, for each structure, how many models contribute to the consensus and which models they are.
  
The provided CSV files are examples for our specific use case. If other models or anatomical structures are used, custom CSV files with the corresponding structure definitions and model information must be created.

The three scripts are designed to be run in sequence:

---

### Step 1: Identify available structures per CT  
**Script:** `create_csv_file_for_consensus.py`

**Goal:** For each CT series folder in `nifti_base/`, create a `filtered_structures.csv` that contains **only** those structures for which a consensus NIfTI file (`<structure_name>_overlap.nii.gz`) exists, along with the required metadata (SNOMED-CT codes) needed for DICOM conversion.

**Input:**
- `base_folder` → root of the consensus NIfTI directory (`nifti_base/`)
- `structures_csv` → global structure definition CSV (e.g., `example_structure_codes.csv`)

**Terminal command:**
```bash
python create_csv_file_for_consensus.py /path/to/nifti_base /path/to/example_structure_codes.csv
```
**Effect:**
For each CT series folder under nifti_base/CT_<SeriesInstanceUID>/, the script:
- scans for all *_overlap.nii.gz files,
- extracts the structure names from the filenames,
- filters the structure definition CSV to only those structures
After running the script, the structure of the NIfTI base folder should look as follows:
```
nifti_base/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│        └── CT_<SeriesInstanceUID>/
│            ├── *_overlap.nii.gz
│            └── filtered_structures.csv
```

### Step 2: Create dcmqi metadata JSON per CT
**Script:** `convert_csv_to_json_for_consensus.py`
**Goal:** Convert each `filtered_structures.csv` into a dcmqi-compatible metadata JSON file (`<Algorithm>-dcmqi_seg_dict.json`) that describes all segments (codes, names, colors, and models contributing to the consensus).
**Input:**
- `base_folder` → root of the consensus NIfTI directory (`nifti_base/`)
- overview_csv → model overview CSV (e.g., `example_structures_overview_all_models.csv`)

**Terminal command:**
```bash
python convert_csv_to_json_for_consensus.py /path/to/nifti_base /path/to/structures_overview_all_models.csv
```

**Effect:**
For each CT folder that contains a filtered_structures.csv, the script:
- reads the filtered structures and their ontology codes,
- looks up the corresponding models for each structure from the overview CSV,
- constructs a segmentAttributes list for dcmqi and writes a JSON file
After running the script, the structure of the NIfTI base folder should look as follows:
```
nifti_base/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│        └── CT_<SeriesInstanceUID>/
│            ├── *_overlap.nii.gz
│            ├── filtered_structures.csv
│            └── Consensus-dcmqi_seg_dict.json
```

### Step 3: Convert consensus NIfTI + metadata into DICOM SEG
**Script:** `convert_consensus_to_dicom.py`
**Goal:** Combine the consensus NIfTI masks, the per-case JSON metadata, and the original CT DICOM series into a valid DICOM SEG object for each CT series.
**Input:**
- `nifti_base_dir` → root of the consensus NIfTI directory (`nifti_base/`)
- `output_base_dir` → root of the output directory where DICOM SEG files will be written
- `dicom_base_dir` → root of the original CT DICOM directory (`dicom_base/`)
- `itkimage2segimage_path` → path to the itkimage2segimage binary from dcmqi
**Terminal command:**
```bash
python convert_consensus_to_dicom.py \
  /path/to/nifti_base \
  /path/to/output_seg \
  /path/to/dicom_base \
  /path/to/dcmqi/bin/itkimage2segimage
```

**Effect:**
For each CT series folder under `nifti_base/CT_<SeriesInstanceUID>/`, the script:
- Reads the metadata JSON (e.g., Consensus-dcmqi_seg_dict.json).
- Extracts the expected segment labels (SegmentLabel) and matches them to files named `<structure_name>_overlap.nii.gz`.
- Identifies the corresponding DICOM CT folder under `dicom_base`/ by matching the same <SeriesInstanceUID> in the path.
- Calls itkimage2segimage with:
    --inputImageList → comma-separated list of NIfTI consensus masks
    --inputMetadata → the JSON file created in Step 2
    --inputDICOMDirectory → the original CT series folder
    --outputDICOM → output SEG file path

The resulting folder structure under output_base_dir looks like:
```
output_seg/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│        └── CT_<SeriesInstanceUID>/
│            └── SEG_Consensus.dcm
```
