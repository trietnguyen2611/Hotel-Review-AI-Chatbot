# Cross-Aspect Leakage in Ordinal Rationalization of Hotel Reviews

## Overview
This research project focuses on Selective Rationalization for hotel reviews. The goal is to read a hotel review, predict a 1-5 score for three specific aspects (Location, Service, and Cleanliness), and simultaneously extract the text rationale (evidence) for each score. 

The main contribution is extending traditional binary rationalization to ordinal 5-level ratings, analyzing cross-aspect leakage, and proposing improvements to the PLMR model (adding ordinal loss and overlap penalty) to keep rationales faithful to their specific aspects.

## Project Structure
* `Data/`: Directory for datasets. You will need the standard `HotelReview` benchmark and the original 5-level rating dataset (Wang et al., KDD 2010).
* `Project.ipynb`: Main notebook for local environment setup, dataset merging (mapping 5-level labels to the benchmark), exploratory data analysis, and checking the pipeline.
* `Training_Colab.ipynb`: Training notebook configured for Google Colab environments to train RNP, MGR, MRD, and PLMR models.
* `Training_Kaggle.ipynb`: Training notebook configured for Kaggle environments.
* `Plan/`: Contains the core research plan (`Research_Plan.md`).
* `requirements.txt`: Python dependencies.

## Getting Started

### Prerequisites
Install the required dependencies:
```bash
pip install -r requirements.txt
```

### Data Preparation
1. Place the `HotelReview` benchmark and the 5-level rating dataset in the `Data/` directory.
2. Run `Project.ipynb` to merge the 5-level labels with the rationale annotations and perform initial EDA (RQ1 & RQ2 data prep).

### Model Training & Evaluation
To train the selective rationalization models (e.g., PLMR with CORN loss and overlap penalty) using a GPU environment:
* **Google Colab:** Open `Training_Colab.ipynb`, upload your preprocessed dataset to Colab, and run the cells.
* **Kaggle:** Open `Training_Kaggle.ipynb`, upload the dataset via Kaggle's interface, update the dataset path, and run the cells.

## Research Questions
1. **RQ1:** How much does rationale F1 drop when shifting from 2-class to 5-class ordinal classification?
2. **RQ2:** What is the extent of cross-aspect leakage (rationales of one aspect falling into sentences of another aspect)?
3. **RQ3:** Does adding ordinal loss and overlap penalty to PLMR reduce leakage and macro-MAE without sacrificing rationale F1?
