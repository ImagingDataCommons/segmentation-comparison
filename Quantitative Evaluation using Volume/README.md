# Extract Radiomics - Volume
The primary purpose of this script is radiomics feature extraction. This requires that both the CT images and the segmentation (SEG) data are available in **NIfTI format** (`.nii` / `.nii.gz`). For this reason, the script is organized into two tasks:

- **Task 1 (optional): Conversion**  
  If your data is still in DICOM format, the script can first **convert** it to NIfTI by mirroring the input directory tree and running:
  - CT DICOM slices → **CT NIfTI** (`.nii.gz`) using **dcm2niix**
  - DICOM SEG objects (`SEG_*.dcm`) → **Segmentation NIfTI** using **dcmqi** (`segimage2itkimage`)

- **Task 2: Radiomics extraction**  
  Once CT and segmentation files are available as NIfTI, the script extracts **PyRadiomics** features for each label in a segmentation NIfTI, using the CT NIfTI as the reference image. The mapping from label IDs to anatomical structure names is taken from a `meta.json` file located next to the segmentation outputs.

---

## Usage

### 1) Radiomics extraction
Use this mode if CT images and segmentations already exist in NIfTI format

#### Terminal Prompt
```bash
python calculate_radiomics.py radiomics \
  <ct_nifti_base_dir> \
  <seg_nifti_base_dir> \
  <results_dir>
```

#### Arguments
- **ct_nifti_base_dir:** Base directory containing CT images in NIfTI format (one CT NIfTI per CT series), organized as:
```
ct_nifti_base/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│       └── CT_<SeriesInstanceUID>/
│           ├── CT_<SeriesInstanceUID>.nii.gz
│           └── CT_<SeriesInstanceUID>.json
```
- **seg_nifti_base_dir:** Base directory containing segmentation outputs in NIfTI format. Each segmentation folder must include a meta.json file that maps label IDs to anatomical structure names. The seg_nifti_base_dir should be organized as follows:
```
seg_nifti_base/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│        └── CT_<SeriesInstanceUID>/
│            ├── SEG_<ModelOrTask_1>_SEG/
│            │   ├── 1.nii.gz
│            │   └── meta.json
│            ├── SEG_<ModelOrTask_2>_SEG/
│            └── ...
```

- **results_dir:** Output directory where radiomics feature reports are written. The relative directory structure of the segmentation inputs is preserved.

### 2) Convert DICOM to NIfTI (Optional)
Use this mode if your data is still available as DICOM CT slices and DICOM SEG objects.
```bash
python calculate_radiomics.py convert \
  <dicom_input_dir> \
  <dicom_output_dir> \
  <dcm2niix_path> \
  <segimage2itkimage_path>
```

### Arguments
- **dicom_input_dir:** Base directory containing the original DICOM data (CT DICOM slice files or DICOM SEG objects (SEG_*.dcm)) organized as:
```
dicom_base/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│       └── CT_<SeriesInstanceUID>/
│           └── *.dcm
```
- **dicom_output_dir:** Output directory where the mirrored directory structure and converted NIfTI files will be written.
- **dcm2niix_path:** Path to the dcm2niix executable used to convert CT DICOM series to NIfTI.
- **segimage2itkimage_path:** Path to the segimage2itkimage executable from the dcmqi toolkit, used to convert DICOM SEG objects to NIfTI.