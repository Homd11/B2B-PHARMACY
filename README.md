# Pharma Multi-Warehouse Sales — AI Ops Task Submission

## Contents
- `notebooks/` — the pipeline, in order:
  - `01_profiling_cleaning.ipynb` — data QA & cleaning (10,000 → 9,989 rows)
  - `02_entity_resolution.ipynb` — the core: products/pharmacies/reps unified with a layered, medically-safe matcher (requires `normalize.py` in the same folder)
  - `03_modeling_impact.ipynb` — star schema + before/after impact (22.3% of revenue was fragmented across name variants)
  - `04_ml.ipynb` — price-disambiguation feasibility study, demand forecasting, anomaly detection
  - All notebooks are pre-executed: outputs are visible without running anything.
- `dashboard/` — Streamlit app. Run: `pip install -r requirements.txt && streamlit run app.py`
  (includes the `warehouse/` star schema and all required data; Dockerfile included)
- `n8n/` — Human-in-the-Loop operationalization:
  - `Pharma_HITL_Review_Telegram.json`, `Pharma_Daily_Digest_Telegram.json` — importable workflows (Telegram review with Merge/Separate buttons; daily KPI digest + anomaly alerts)
  - `sync_to_n8n.py` — refreshes the n8n data tables from pipeline outputs, preserving human decisions
- `docs/` — `final_report.pdf` (methodology + findings), `qa_report.md`, `audit_sample.csv` (80 stratified pairs for match-quality verification)

## To reproduce
Python 3.10+, then: `pip install pandas numpy scikit-learn rapidfuzz networkx statsmodels matplotlib jupyter`
Run notebooks in order with the raw CSV in the same folder.
