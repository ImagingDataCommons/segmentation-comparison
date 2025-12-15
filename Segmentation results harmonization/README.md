# Example dcmqi Pipeline for MultiTalent Segmentations

This repository provides **example scripts demonstrating how to convert MultiTalent segmentation outputs into DICOM SEG objects using the dcmqi toolkit** using our harmonized mapping of the model-specific labels to SNOMED-CT codes and color assignments. For other segmentation models and output formats, please refer to the official dcmqi documentation to adapt the pipeline accordingly.

The workflow closely follows the concepts described in the dcmqi documentation: https://qiicr.gitbook.io/dcmqi-guide/quick-start

---

## Overview of the Pipeline

The pipeline consists of **two main steps**:

1. **Create a dcmqi-compatible JSON metadata file**  
   A CSV (exported from an Excel mapping file) defines the semantic meaning of each segmentation label.  
   This CSV is converted into a dcmqi-compatible JSON metadata file.

2. **Convert NIfTI segmentations to DICOM SEG**  
   The NIfTI segmentation outputs are converted into a DICOM SEG object using `itkimage2segimage` from the dcmqi toolkit.

---

### segment_snomed_mapping.xlsx
A harmonized mapping of model-specific labels to SNOMED-CT codes and recommended display colors is maintained in a single Excel sheet. This sheet contains a harmonized label map for TotalSegmentator v1.5, TotalSegmentator v2.6, MOOSE, MultiTalen, Auto3DSeg, and CADS.
Each worksheet corresponds to one segmentation model and defines: Harmonized label names, Corresponding SNOMED-CT codes, DICOM Segmentation categories and types, and recommended display RGB color values.

Each worksheet can be exported to a CSV file, which is then used as input for the JSON-generation script that creates a dcmqi-compatible segmentation dictionary.

---

## Script 1: Create dcmqi Segmentation JSON

### Purpose
This script:
- Reads a CSV file containing the label mapping
- Generates a **dcmqi-compatible segmentation dictionary JSON**

### Terminal prompt
```bash
python example_multitalent_csv_to_json.py <mapping.csv> <algorithm_name> <output_dir>
```

#### Input:
- `mapping.csv`: CSV exported from the Excel mapping file
- `algorithm_name` Name of the segmentation algorithm (e.g. MultiTalent)
- `output_dir`: Output directory for the generated JSON

#### Output:
- `<algorithm_name>-dcmqi_seg_dict.json`: A JSON file compatible with itkimage2segimage

## Script 2: Convert NIfTI to DICOM SEG
### Purpose:
This script:
- Matches NIfTI segmentations to the correct CT series
- Updates the JSON metadata with series information
- Converts the segmentations into a DICOM SEG object

### Terminal prompt
```bash
python example_multitalent_to_dicom.py \
  <dicom_base_dir> \
  <nifti_base_dir> \
  <json_base_dir> \
  <output_base_dir> \
  <itkimage2segimage_path>
```

#### Input:
- `dicom_base_dir`:	Base directory containing the original CT DICOM data. They should be stored in the following hierarchical structure commonly used by IDC and other imaging archives:

```text
dicom_base_dir/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│       └── CT_<SeriesInstanceUID>/
│           └── *.dcm
```

- `nifti_base_dir`:	Base directory containing MultiTalent NIfTI segmentation outputs. One .nii.gz file per anatomical structure is expected. The `nifti_base_dir` is expected to have the following structure:
```
nifti_base/
├── <SeriesInstanceUID>/
│   ├── adrenal_gland_left.nii.gz
│   ├── adrenal_gland_right.nii.gz
│   ├── aorta.nii.gz
│   └── ...
```

- `json_base_dir`: Directory containing the dcmqi-compatible segmentation dictionary JSON generated in Script 1.
- `output_base_dir`: Output directory where the generated DICOM SEG objects will be stored.
- `itkimage2segimage_path`:	Path to the itkimage2segimage executable from the dcmqi toolkit.

#### Output:
One DICOM SEG file (.dcm) per CT series stored in: `<output_base_dir>/<SeriesInstanceUID>/SEG_MultiTalent_CT_<SeriesInstanceUID>.dcm`
