# Interactive Plots

This folder contains scripts used to generate the **interactive plots** shown in the paper "In search of truth: Evaluating concordance of AI-based anatomy segmentation models", for both the **interactive Dice score visualizations** and the **interactive Volume visualizations**.

---

## Interactive Dice Score Plots

The scripts are designed to work on the output of the **analyze_disagreement_dice_score.py** script. To generate the interactive Dice plots, the following steps are required:

1. **Transform Dice score CSV**
2. **Compute Dice statistics (optional)**
3. **Generate interactive plots**

Each step is implemented in a separate script to keep the workflow modular and reusable.

---

## 1. Transform Dice Scores `transform_dice_csv.py`

### Purpose

The Dice scores produced by the *analysis disagreement script* are stored in a file called: `segmentation_dice_scores_pivot.csv`. This file is in a pivoted format and must be converted into a long / tidy format before it can be used for plotting or statistical analysis.

### Terminal Prompt
```bash
python transform_dice_csv.py \
  <segmentation_dice_scores_pivot.csv> \
  <dice_scores_transformed.csv>
```

### Input
- `segmentation_dice_scores_pivot.csv`: Output of the disagreement analysis pipeline
- `dice_scores_transformed.csv`: Output path of the transformed csv file

### Output
- A transformed CSV with the following columns:`segment`, `method`, `dsc`, `caseID`. This transformed file is the **input for all subsequent scripts**.

## 2. Compute Dice Statistics (Optional) `compute_dice_statistics.py`

### Purpose

Basic statistics (mean, median, standard deviation, min, max, IQR) can be computed from the transformed Dice scores.

### Terminal Prompt
```bash
python compute_dice_statistics.py \
  <dice_scores_transformed.csv> \
  <dice_statistics.csv>
```

### Input
- `dice_scores_transformed.csv`: Output CSV from `transform_dice_scores.py`
- `dice_statistics.csv`: Output path for the statistics csv file

### Output
- CSV files containing per-structure Dice statistics


## 3. Interactive Dice Scatter Plot `plot_interactive_dice.py`

### Purpose

The interactive plot visualizes Dice Similarity Coefficients (DSC) across anatomical structures and segmentation models. Grey points show individual case-level DSC values, while colored markers indicate mean DSC per model and structure. Clicking on a data point opens an OHIF Viewer displaying the corresponding CT image together with all associated segmentations for visual inspection.
### Terminal Prompt
```bash
python plot_interactive_dice.py \
  <dice_scores_transformed.csv> \
  <output_plot.html>
```

### Input
- `dice_scores_transformed.csv`: Output CSV from `transform_dice_scores.py`
- `output_plot.html`: Output path for the interactive HTML file

### Output
- Interactive HTML file containing the Dice scatter plot

### Notes
- The following variables control **which segmentation methods and anatomical structures** are displayed in the interactive plots and can be adapted in the code:

```python
methods_selected = ['Auto3Dseg','Moose','MultiTalent','OMAS','TotalSegmentator_1.5','TotalSegmentator_2.6']

custom_segment_order = ['vertebrae_t2','vertebrae_t3', 'vertebrae_t4','vertebrae_t5','vertebrae_t6','vertebrae_t7','vertebrae_t8', 'vertebrae_t9','vertebrae_t10']
```

### Access to a DICOM Store
The DICOM images used in this study are stored in a publicly accessible, DICOMweb-compatible DICOM store. Metadata describing the relationships between CT series and segmentation series is derived from this DICOM store and exposed through a project-specific BigQuery index to enable efficient querying. This BigQuery metadata table is **not publicly accessible**. Consequently, while the underlying DICOM data itself is public, the scripts provided here **will not work out of the box for external users**.

External users who wish to reproduce the interactive visualizations must either **recreate the required metadata mappings** (e.g., CT–SEG relationships) or adapt the scripts to their own metadata backend. Alternatively, users may set up their own DICOM store using the publicly available data provided on Zenodo (https://doi.org/10.5281/zenodo.17860591) and generate the necessary metadata index themselves.

The following SQL query is specific to the internal BigQuery-based metadata index used in this project and must be adapted accordingly when using a different DICOM store or metadata backend:
  ```sql
  SELECT 
      main.SeriesInstanceUID AS seg_SeriesInstanceUID, 
      main.StudyInstanceUID,  
      main.SeriesDescription, 
      main.Modality, 
      ref.SeriesInstanceUID AS ct_SeriesInstanceUID 
  FROM `idc-external-031.af_segmentation_benchmarking.18_cases_pilot` AS main,  
  UNNEST(main.ReferencedSeriesSequence) AS ref

```
### OHIF Viewer URL configuration
If users want to visualize their own segmentations, the OHIF Viewer must be configured to point to their own DICOMweb endpoint, and the viewer URL construction in the script must be updated accordingly.
In particular, the following code block needs to be adapted to match the user’s OHIF Viewer deployment and DICOMweb proxy:

```python 
df['url'] = df.apply(
    lambda r:
        f"https://segverify-viewer.web.app/viewer?"
        f"StudyInstanceUIDs={r['studyID']}&"
        f"SeriesInstanceUIDs={r['caseID']},{all_seg_for(r['studyID'], r['caseID'])}&"
        f"dicomweb=us-central1-idc-external-031.cloudfunctions.net/segverify_proxy1",
    axis=1
)
```
---

## Interactive Volume Plots

The interactive volume plots visualize **structure-wise volume agreement** between individual segmentation models and a consensus segmentation. They are based on volumetric features extracted from the radiomics pipeline (`calculate_radiomics.py`).

To generate the interactive volume plots, the following steps are required:

1. **Extract structure volumes from radiomics outputs**
2. **Generate interactive volume plots**

---

## 1. Extract Volumes from Radiomics (`get_volume_csv.py`)

### Purpose

This script collects **structure volumes** from radiomics feature JSON files generated by the radiomics extraction pipeline.  
It traverses the radiomics output directory, extracts volumes for each anatomical structure, segmentation method, and CT series, and stores them in a single CSV file.

This CSV serves as the **input for the interactive volume plots**.

---

### Terminal Prompt

```bash
python get_volume_csv.py \
  <features_reports_base_dir> \
  <segmentation_volumes.csv>
```

### Input
 - **features_reports_base_dir:** Base directory containing radiomics feature outputs (*_features.json), organized by CT series and segmentation method. Each JSON file is expected to contain radiomics features per anatomical structure. The directory should be organized as follows:
 ```
features_reports_base_dir/
├── <PatientID>/
│   └── <StudyInstanceUID>/
│       └── CT_<SeriesInstanceUID>/
│           ├── SEG_<ModelOrTask_1>_SEG/
│           │    └── *_features.json
```

- `segmentation_volumes.csv`: Output path for the csv file containing all volumes for each anatomical structure, segmentation method, and CT series

### Output
- CSV file containing the label name, the segmentation model, the structure volume in mm³, and the CT SeriesInstanceUID. This file is the required input for the interactive volume visualization script.

## 2. Generate Interactive Volume Scatter Plots (`plot_interactive_volume_plot.py`)

### Purpose
This script generates interactive scatter plots that relate model-specific structure volumes to the percentage of overlap with the consensus volume.
- The x-axis shows the structure volume (in mL) predicted by each model.
- The y-axis shows the overlap volume as a percentage of the model’s structure volume.
- Colored points represent different segmentation models.
- Different marker symbols correspond to different anatomical structures.
- Grey dashed lines connect measurements of the same anatomical structure from the same CT series across different segmentation models.
- Clicking on a data point opens an OHIF Viewer, displaying the corresponding CT image together with all associated segmentations for visual inspection.

### Terminal Prompt
```bash
python plot_interactive_volume_plot.py \
  <segmentation_volumes.csv> \
  <output_dir>
```

### Input
- `segmentation_volumes.csv`: Output of `get_volume_csv.py`, containing structure volumes per case and segmentation model.
- **output_dir**: Directory where the `Overlap_percent_of_model_volumes_grouped_{group_name}.html` files are saved

### Output
- One HTML file per predefined anatomical group (e.g., lungs, ribs, vertebrae), written to the specified output directory.

### Notes
- The anatomical structures displayed in the plots are controlled via predefined custom segment groups in the script and can be adapted as needed.
```python
custom_segment_groups = [
    ("lung", ["lung_upper_lobe_left", "lung_upper_lobe_right", "lung_middle_lobe_right", "lung_lower_lobe_left", "lung_lower_lobe_right"]),
    ("heart", ["heart"]),
    ...
]
```

### Access to a DICOM Store
The DICOM images used in this study are stored in a publicly accessible, DICOMweb-compatible DICOM store. Metadata describing the relationships between CT series and segmentation series is derived from this DICOM store and exposed through a project-specific BigQuery index to enable efficient querying. This BigQuery metadata table is **not publicly accessible**. Consequently, while the underlying DICOM data itself is public, the scripts provided here **will not work out of the box for external users**.

External users who wish to reproduce the interactive visualizations must either **recreate the required metadata mappings** (e.g., CT–SEG relationships) or adapt the scripts to their own metadata backend. Alternatively, users may set up their own DICOM store using the publicly available data provided on Zenodo (https://doi.org/10.5281/zenodo.17860591) and generate the necessary metadata index themselves.

The following SQL query is specific to the internal BigQuery-based metadata index used in this project and must be adapted accordingly when using a different DICOM store or metadata backend:
  ```sql
client = bigquery.Client(credentials=credentials, project="idc-external-031")

query = """
    SELECT 
        main.SeriesInstanceUID AS seg_SeriesInstanceUID, 
        main.StudyInstanceUID,  
        main.SeriesDescription, 
        main.Modality, 
        ref.SeriesInstanceUID AS ct_SeriesInstanceUID 
    FROM `idc-external-031.af_segmentation_benchmarking.18_cases_pilot` AS main,  
    UNNEST(main.ReferencedSeriesSequence) AS ref  
"""
```
### OHIF Viewer URL configuration
If users want to visualize their own segmentations, the OHIF Viewer must be configured to point to their own DICOMweb endpoint, and the viewer URL construction in the script must be updated accordingly.
In particular, the following code block needs to be adapted to match the user’s OHIF Viewer deployment and DICOMweb proxy:

```python 
df_long["url"] = df_long.apply(lambda row:
    f"https://segverify-viewer.web.app/viewer?"
    f"StudyInstanceUIDs={row['studyID']}&"
    f"SeriesInstanceUIDs={row['caseID']},{get_all_segmentations(row['studyID'], row['caseID'])}&"
    f"dicomweb=us-central1-idc-external-031.cloudfunctions.net/segverify_proxy1",
    axis=1)
```


