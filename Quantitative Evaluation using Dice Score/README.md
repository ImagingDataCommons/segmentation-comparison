# Consensus Generation and Dice Score Analysis

This folder contains a Python script that computes **consensus segmentations** across multiple AI models and evaluates **model agreement using Dice scores**.  
Consensus masks are saved as NIfTI files, and Dice results are stored in a summary CSV file.

---
## Required Input Data
The script requires two main inputs:
 1. A **DICOM base directory** containing DICOM-SEG files produced by multiple AI segmentation models
 2. A **structure overview CSV file** defining which anatomical structures are segmented by how many models

### 1. DICOM Base Directory Structure
The DICOM input directory must contain CT studies organized in the hierarchical format provided by the Imaging Data Commons (IDC):
``````
<dicom_base>/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│       └── CT_<SeriesInstanceUID>/
│           ├── SEG_<ModelA>_<UID>.dcm
│           ├── SEG_<ModelB>_<UID>.dcm
│           ├── SEG_<ModelC>_<UID>.dcm
│           └── ... additional SEG files ...
``````
#### Explanation of each level
- **PatientID**  
  A subject identifier assigned by the dataset (e.g., NLST). Each patient folder may contain one or more imaging studies.
- **StudyInstanceUID**  
  A unique identifier for a specific imaging study. A study may include multiple imaging series.
- **CT_<SeriesInstanceUID>**  
  The folder containing a CT series. Its name begins with `CT_` followed by the `SeriesInstanceUID`.  
  This is the *leaf folder* that contains the individual `.dcm` files.
- **SEG_<Model>_*.dcm**  
    A DICOM-SEG file containing multiple anatomical structures predicted by one segmentation model. The script automatically detects all SEG files inside each CT folder and converts them into NIfTI format for further analysis.

### 2. DICOM Base Directory Structure
A CSV file is required to define which anatomical structures should be included in the consensus and Dice score evaluation.
Example:
| final_label | count | models                    |
|-------------|-------|---------------------------|
| heart       | 6     | auto3dseg,moose,... |

**Fields**
- *final_label:* The lowercase structure name used across segmentation models.
- *count:* Number of models that segment this structure. The script uses this to decide whether a structure should be included (e.g., ≥ 4 models required).
- *models (optional):* List of contributing models (informational only).

**Important:** If you use different segmentation models or additional anatomical structures, you must prepare your own CSV file following this layout. An example file is provided in the repository.


## Running the Script

The script is executed from the command line and requires four arguments:

```bash
python analyze_disagreement_dice_score.py \
    <dicom_base> \
    <output_nii_folder> \
    <structure_overview_csv> \
    <segimage2itkimage_path>
```

- `dicom_base`: Path to the base directory containing the DICOM-SEG files organized by patient, study, and CT series.
- `output_nii_folder`: Output directory where consensus NIfTI masks and the Dice score summary CSV will be written. The script mirrors the input folder hierarchy under this directory.
- `structure_overview_csv`: CSV file defining which anatomical structures are included in the analysis and how many models segment each structure.
- `segimage2itkimage_path`: Path to the segimage2itkimage executable provided by dcmqi, used to convert DICOM-SEG files into NRRD segmentations.

### What the Script Does
For each CT series (CT_<SeriesInstanceUID>), the script performs the following steps:
1. *Detects all DICOM-SEG files:* All segmentation DICOM files produced by different AI models are identified within the CT folder.
2. *Converts DICOM-SEG to NIfTI:* Each DICOM-SEG file is converted into individual per-structure NRRD masks using segimage2itkimage. This step also extracts the corresponding metadata (meta.json) required for structure identification.
3. *Selects structures for analysis:* Only structures that are segmented by **at least four models** are included in the analysis. The minimum number of required models is **configurable in the code** and can be adjusted at the following locations:
   - When selecting eligible structures from the structure overview CSV:
     ```python
     structures_list = df_structures[df_structures["count"] >= 4]["final_label"].str.lower().tolist()
     ```
   - When validating the number of available segmentations per structure:
     ```python
     if len(paths) < 4:
         continue
     ```
   By modifying the value `4` in these two places, the minimum number of contributing models required for inclusion can be changed.
4. *Loads and resamples segmentation masks:* All model segmentations are resampled to a common reference geometry to ensure voxel-wise correspondence.
5. *Computes a consensus segmentation:* A consensus mask is generated using a logical AND across all available model segmentations for a given structure.
6. *Saves consensus masks:* The resulting consensus segmentation is saved as a compressed NIfTI file: `<structure_name>_overlap.nii.gz``
7. *Computes Dice similarity scores:* For each model, the Dice score between the model segmentation and the consensus mask is computed. All Dice scores are aggregated into a pivot-table CSV file summarizing model agreement across structures and CT series.

### Restricting the Analysis to Specific Structures

By default, the script processes all eligible anatomical structures listed in the structure overview CSV.  
If only a **subset of structures** (e.g., a single organ or a small group) should be analyzed, this can be restricted directly in the code.

This is controlled by defining a list of structures of interest:

```python
structures_of_interest = [
    "label_name"
]
```

Only structures whose normalized names match this list will be loaded and processed.
The filtering is applied during NIfTI extraction:

```python
for label_id, structure_name in label_map.items():
    if structure_name in structures_of_interest and label_id in nifti_data:
        nifti_path = nifti_data[label_id]
        nifti_files.setdefault(structure_name, []).append((model_name, nifti_path))
```

## Output
1. Consensus NIfTI Files
Consensus masks are written to the output directory using a mirrored folder structure:
```
<output_nii_folder>/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│       └── CT_<SeriesInstanceUID>/
│           └── <structure_name>_overlap.nii.gz
```

2. Dice Score Summary
A summary CSV file containing all Dice scores is written to: `<output_nii_folder>/segmentation_dice_scores_pivot.csv`. Each entry represents the Dice similarity between a model’s segmentation and the consensus mask.
