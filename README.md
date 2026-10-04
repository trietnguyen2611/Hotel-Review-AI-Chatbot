# Xây dựng hệ thống Chatbot hỏi đáp thông tin khách sạn dựa trên phân tích đánh giá đa khía cạnh
## Development of an Aspect-Based Review QA Chatbot for Hotel Services
**DAP391m - AI2002 - Group 5**

## Overview
This project develops an intelligent, evidence-grounded **Aspect-Based Review Question Answering (QA) Chatbot** for hotel services. The system extracts and analyzes customer reviews across fine-grained aspects (**Service, Facility, Amenity, Experience, Loyalty, Branding, Location, Cleanliness**) annotated with sentiment polarities (Positive, Neutral, Negative) from **`TripAdvisor_EN.json`** and large-scale hotel review benchmarks.

The core AI engine combines:
1. **Aspect-Based Knowledge Base:** Indexes human-annotated review rationales and sentiment polarities to provide factual, evidence-backed answers.
2. **Selective Rationalization & Rating Prediction:** An aspect-disentangled model (PLMR with Weighted CORN Loss and Overlap Penalty) to predict satisfaction ratings and extract faithful rationale spans while mitigating cross-aspect leakage.
3. **Conversational QA Interface:** Answers multi-aspect user inquiries with customer satisfaction percentages and real positive/negative review quotations.

## Project Structure
* `data/dataset/`: Directory for datasets including `TripAdvisor_EN.json` (9,990 fine-grained labeled reviews) and hotel review benchmarks.
* `Project.ipynb`: Core notebook for data preprocessing, EDA, rationale F1 evaluation, cross-aspect leakage analysis, and the Aspect-Based Hotel Review AI Chatbot engine.
* `Training_Colab.ipynb`: Training notebook configured for Google Colab GPU environments to train aspect generator and predictor models.
* `Training_Kaggle.ipynb`: Training notebook configured for Kaggle GPU environments.
* `plan/`: Contains the research plan (`Research_Plan.md`).
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
