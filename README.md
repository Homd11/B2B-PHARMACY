# B2B Pharma Sales Analytics & Entity Resolution Pipeline

## Overview
This project is an end-to-end Data Operations and Machine Learning pipeline designed to resolve fragmented B2B pharmaceutical sales data. When multiple suppliers use different spelling, formatting, and naming conventions for the same products and pharmacies, the true revenue and market share remain hidden. 

This pipeline processes raw sales exports, unifies entities using a hybrid NLP/ML approach, models the data into a Star Schema, and provides actionable insights via a Streamlit dashboard and n8n automation.

## Architecture & Key Components

1. **Data QA & Cleaning (`01_profiling_cleaning.ipynb`):** 
   - Handles corrupted dates, extracts features, and removes non-transactional noise.
2. **Entity Resolution Engine (`02_entity_resolution.ipynb` & `normalize.py`):** 
   - **Candidate Generation:** Uses Character n-gram TF-IDF and Cosine Nearest Neighbors to reduce 12.7M possible pairs to ~10K candidates.
   - **Pairwise Classification:** A Random Forest classifier scores pairs based on string similarity and extracted medical attributes (strength, form, pack size).
   - **Safety Rules:** Strict medical rules prevent unsafe merges (e.g., merging different drug strengths). Uncertain matches are routed to a Human-in-the-Loop (HITL) queue.
3. **Data Modeling & ROI (`03_modeling_impact.ipynb`):**
   - Builds a Star Schema (Products, Pharmacies, Reps, Suppliers).
   - Quantifies the business impact (e.g., discovering that ~28.9% of revenue was fragmented across naming variants).
4. **Machine Learning (`04_ml.ipynb`):**
   - Demand forecasting using Exponential Smoothing (ETS).
   - Transaction anomaly detection using Isolation Forests.
5. **Operationalization:**
   - **Streamlit Dashboard:** For visualizing revenue, market composition, and anomalies.
   - **n8n Automation:** Telegram bot integration for HITL review and daily KPI digests.

## Tech Stack
- **Data Processing:** Python, Pandas, Numpy
- **Machine Learning & NLP:** Scikit-Learn, RapidFuzz, NetworkX, Statsmodels
- **Visualization & Automation:** Streamlit, n8n, Docker

## To reproduce
Python 3.10+, then: `pip install pandas numpy scikit-learn rapidfuzz networkx statsmodels matplotlib jupyter`
Run notebooks in order with the raw CSV in the same folder.
