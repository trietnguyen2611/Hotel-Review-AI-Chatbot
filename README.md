# Aspect-Based Q&A Chatbot for Hotel Reviews

## Overview
This repository contains the research and development code for a Question Answering Chatbot focused on hotel reviews. Unlike broad, multi-task sentiment models, this system is specifically designed around manually labeled aspect and sentiment data to provide accurate and context-aware responses to user queries.

## Project Structure
* `Data/TripAdvisor_EN.json`: The core dataset containing manually labeled hotel reviews with specific service aspects (e.g., Facility, Service, Experience) and their corresponding sentiments.
* `Project.ipynb`: The main notebook for local environment setup, data exploration, aspect extraction, and data preprocessing.
* `Training_Colab.ipynb`: Training notebook configured for Google Colab environments.
* `Training_Kaggle.ipynb`: Training notebook configured for Kaggle environments.
* `Plan/`: Contains project planning documents and baseline methods research.
* `requirements.txt`: Python dependencies required to run the local Jupyter notebooks.

## Getting Started

### Local Setup
1. Clone the repository.
2. Ensure you have Python 3 installed.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run `Project.ipynb` to execute the data preprocessing and aspect extraction pipeline.

### Model Training
To train the aspect extraction and intent classification models using a GPU environment:
* **Google Colab:** Open `Training_Colab.ipynb`, upload the `TripAdvisor_EN.json` file to the `Data/dataset/` directory in your Colab workspace, and run the cells.
* **Kaggle:** Open `Training_Kaggle.ipynb`, upload the dataset via Kaggle's interface, update the dataset path variable in the notebook to match your dataset name, and run the cells.

