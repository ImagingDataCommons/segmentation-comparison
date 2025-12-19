# In Search of Truth: Evaluating Concordance of AI-Based Anatomy Segmentation Models

This repository contains the code and analysis scripts accompanying the following preprint.

> Giebeler, L., Krishnaswamy, D., Clunie, D., Wasserthal, J., Sundar, L. K. S., Diaz-Pinto, A., Maier-Hein, K. H., Xu, M., Menze, B., Pieper, S., Kikinis, R. & Fedorov, A. In search of truth: Evaluating concordance of AI-based anatomy segmentation models. arXiv [eess.IV] (2025). [doi:10.48550/arXiv.2512.15921](https://doi.org/10.48550/arXiv.2512.15921)

The scripts implement a practical framework for harmonizing, comparing, and visually inspecting anatomy segmentation results from multiple AI models in the absence of ground-truth annotations. They aim to support informed model selection and transparent evaluation of AI-based segmentation methods.

> **Preprint:** https://doi.org/10.48550/arXiv.2512.15921
> **Interactive plots:** https://imagingdatacommons.github.io/segmentation-comparison/  
> **Public data:** https://doi.org/10.5281/zenodo.17860591  
> **3D Slicer CrossSegmentationExplorer Extension:** https://github.com/ImagingDataCommons/CrossSegmentationExplorer

---

## Repository Structure

This repository is organized into several folders, each corresponding to a specific stage of the workflow:

- **Segmentation Results Harmonization**  
  Scripts for harmonizing model-specific segmentation outputs into a standardized representation

- **Quantitative Evaluation using Dice Score**  
  Script to compute Dice scores and consensus segmentations.

- **Convert Consensus to DICOM**  
  Scripts to convert the consensus segmentations to DICOM using *dcmqi*.

- **Quantitative Evaluation using Volume**  
  Radiomics-based extraction of structure volumes.

- **Visualization of Model Agreement**  
  Scripts for generating interactive Dice and volume plots using Plotly and OHIF Viewer.

- **docs/**  
  Contains the static files used to deploy the interactive plots website.  
  This folder exists due to GitHub Pages requirements and can be ignored for code reuse.

---

## Workflow Description

### 1. Segmentation Harmonization

Once segmentation results from different models are available, they should first be harmonized into a standard representation.  
Example scripts for the conversion to DICOM using the harmonized metadata are provided in the **Segmentation Results Harmonization** folder.

For details on the underlying conversion workflow and parameters, please refer to the dcmqi documentation:
https://github.com/QIICR/dcmqi


### 2. Quantitative Evaluation

#### Dice Score Analysis and Consensus Generation

The Dice score script computes pairwise Dice scores between segmentations and generated consensus segmentations, which are stored as NIfTI files.

This step should be performed before radiomics analysis, since the consensus segmentation is required as input.

#### Radiomics-Based Volume Analysis

After Dice computation and consensus generation:

1. Convert the consensus segmentation to DICOM using the provided scripts in the **Convert Consensus to DICOM** folder
2. Run the `calculate_radiomics.py` script, which is located in the **Quantitative Evaluation using Volume** folder, to extract the radiomic features including volume.


### 3. Visualization of the Quantitative Evaluation and Interactive Analysis

Quantitative results can be visualized using the scripts in the **Visualization of Model Agreement** folder.
There are two types of interactive plots:
- Interactive **Dice score plots**
- Interactive **Volume plots**

Clicking on a data point in the interactive plots opens an **OHIF Viewer window** with the corresponding CT series all associated segmentations.
Within OHIF the layout can be adjusted using the toolbar at the top and segmentations can be assigned to views via drag-and-drop.

Further details on OHIF usage can be found in the official documentation:  
https://docs.ohif.org/

The interactive plots for the paper are publicly available at:  
https://imagingdatacommons.github.io/segmentation-comparison/

---

## Qualitative Comparison in 3D Slicer

For qualitative comparison, we developed a dedicated **3D Slicer extension** that streamlines loading and inspection of harmonized segmentations across models.

The extension is available here: https://github.com/ImagingDataCommons/CrossSegmentationExplorer

---

## Data Availability

All data used in this study is **publicly available** on Zenodo:  
https://doi.org/10.5281/zenodo.17860591

Users can reuse the scripts in this repository with their own data by following the same harmonization, conversion, analysis, and visualization steps described above.

