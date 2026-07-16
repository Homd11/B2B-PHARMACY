# Pharma Sales Dashboard (Streamlit)

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Opens at http://localhost:8501

## Required files (same folder as app.py)
- `warehouse/` — star schema from Notebook 3 (+ ML outputs from Notebook 4)
- `hitl_queue.csv` — review queue from Notebook 2 (with NB4 price suggestions)
- `resolved_sales.csv` — resolved fact source (used by the impact page)

## Pages
Overview · Unification impact (before/after ROI) · Products · Pharmacies ·
Sales reps (person vs channel) · Anomalies & alerts · Forecast bench · HITL queue
