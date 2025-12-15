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

## 1. Transform Dice Scores `transform_dice_scores.py`

### Purpose

The Dice scores produced by the *analysis disagreement script* are stored in a file called: `segmentation_dice_scores_pivot.csv`. This file is in a pivoted format and must be converted into a long / tidy format before it can be used for plotting or statistical analysis.

### Terminal Prompt
```bash
python transform_dice_scores.py \
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


## 3. Interactive Dice Scatter Plot `interactive_dice_scatter.py`

### Purpose

The interactive plot visualizes Dice Similarity Coefficients (DSC) across anatomical structures and segmentation models. Grey points show individual case-level DSC values, while colored markers indicate mean DSC per model and structure. Clicking on a data point opens an OHIF Viewer displaying the corresponding CT image together with all associated segmentations for visual inspection.
### Terminal Prompt
```bash
python interactive_dice_scatter.py \
  <dice_scores_transformed.csv> \
  <output_plot.html>
```

### Input
- `dice_scores_transformed.csv`: Output CSV from `transform_dice_scores.py`
- `dice_statistics.csv`: Output path for the interactive HTML file

### Output
- Interactive HTML file containing the Dice scatter plot

### Notes
- The following variables control **which segmentation methods and anatomical structures** are displayed in the interactive plots and can be adapted in the code:

```python
methods_selected = ['Auto3Dseg','Moose','MultiTalent','OMAS','TotalSegmentator_1.5','TotalSegmentator_2.6']

custom_segment_order = ['vertebrae_t2','vertebrae_t3', 'vertebrae_t4','vertebrae_t5','vertebrae_t6','vertebrae_t7','vertebrae_t8', 'vertebrae_t9','vertebrae_t10']
```

- The interactive plot script assumes access to a DICOMweb-compatible backend
for loading images in the OHIF Viewer. For external users, viewer-related code must be adapted to their own
DICOM store and OHIF Viewer setup. Therefore the user has to change the following code parts:
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





