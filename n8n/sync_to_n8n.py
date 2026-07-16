
import os, sys, json
import requests
import pandas as pd

N8N_URL = os.environ.get("N8N_URL", "").rstrip("/")
API_KEY = os.environ.get("N8N_API_KEY", "")
if not N8N_URL or not API_KEY:
    sys.exit("Set N8N_URL and N8N_API_KEY environment variables first.")

H = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}

TABLES = {  
    "hitl_review_queue":   "kyjcN3233zocREtV",
    "supplier_week_alerts": "rT6fhLh8agn1GXFe",
    "kpi_summary":          "hKUWaP8Toekwb2Xz",
}

def api(method, path, **kw):
    r = requests.request(method, f"{N8N_URL}/api/v1{path}", headers=H, timeout=30, **kw)
    r.raise_for_status()
    return r.json() if r.text else {}

def clear_pending(table_id):
    """Delete only pending rows — human decisions (status=done) are preserved."""
    api("DELETE", f"/data-tables/{table_id}/rows",
        params={"filter": json.dumps({"type": "and",
                "filters": [{"columnName": "status", "condition": "eq", "value": "pending"}]})})

def insert(table_id, rows, batch=50):
    for i in range(0, len(rows), batch):
        api("POST", f"/data-tables/{table_id}/rows",
            json={"data": rows[i:i+batch], "returnType": "count"})

def main():
    hq = pd.read_csv("hitl_queue.csv")
    hq["impact_egp"] = hq["impact_egp"].fillna(0)
    hq["suggestion"] = hq.apply(
        lambda r: f"{r['price_evidence']} ({r['price_suggested_strength']})"
        if pd.notna(r.get("price_evidence")) else "", axis=1)
    sel = hq.nlargest(150, "impact_egp")
    rows = [{"pair_id": int(r.pair_id), "entity": r.entity,
             "raw_a": str(r.raw_a)[:180], "raw_b": str(r.raw_b)[:180],
             "score": round(float(r.score), 3), "impact_egp": round(float(r.impact_egp)),
             "suggestion": r.suggestion, "decision": "", "status": "pending"}
            for r in sel.itertuples()]
    clear_pending(TABLES["hitl_review_queue"])
    insert(TABLES["hitl_review_queue"], rows)
    print(f"queue: {len(rows)} pending pairs synced")

    # ---- alerts (new only: upsert-ish by full delete of unsent + reinsert) ----
    aw = pd.read_csv("warehouse/anomalies_supplier_weeks.csv")
    arows = [{"supplier_id": int(r.supplier_id), "week": str(r.week)[:10],
              "total_amount": round(float(r.total_amount)), "rzscore": round(float(r.rzscore), 2),
              "direction": r.direction, "sent": False} for r in aw.itertuples()]
    api("DELETE", f"/data-tables/{TABLES['supplier_week_alerts']}/rows",
        params={"filter": json.dumps({"type": "and",
                "filters": [{"columnName": "sent", "condition": "eq", "value": False}]})})
    insert(TABLES["supplier_week_alerts"], arows)
    print(f"alerts: {len(arows)} synced")

    # ---- KPIs (replace all) ----
    fact = pd.read_csv("warehouse/fact_sales.csv")
    dp = pd.read_csv("warehouse/dim_product.csv"); dr = pd.read_csv("warehouse/dim_rep.csv")
    dph = pd.read_csv("warehouse/dim_pharmacy.csv")
    rep = (fact[fact["rep_type"] == "person"]
           .merge(dr[["rep_key", "rep_canonical"]], on="rep_key")
           .groupby("rep_canonical")["total_amount"].sum())
    kpis = [
        {"metric": "total_revenue_egp", "value_text": "", "value_num": round(float(fact["total_amount"].sum()))},
        {"metric": "total_transactions", "value_text": "", "value_num": int(len(fact))},
        {"metric": "top_product", "value_text": fact.merge(dp[["product_key", "canonical_name"]], on="product_key")
            .groupby("canonical_name")["total_amount"].sum().idxmax(), "value_num": 0},
        {"metric": "top_rep", "value_text": rep.idxmax(), "value_num": round(float(rep.max()))},
        {"metric": "top_pharmacy", "value_text": fact.merge(dph[["pharmacy_key", "pharmacy_canonical"]],
            on="pharmacy_key").groupby("pharmacy_canonical")["total_amount"].sum().idxmax(), "value_num": 0},
        {"metric": "top_supplier", "value_text": str(int(fact.groupby("supplier_id")["total_amount"].sum().idxmax())),
         "value_num": round(float(fact.groupby("supplier_id")["total_amount"].sum().max()))},
    ]
    api("DELETE", f"/data-tables/{TABLES['kpi_summary']}/rows",
        params={"filter": json.dumps({"type": "and", "filters": []})})
    insert(TABLES["kpi_summary"], kpis)
    print("kpis: 6 synced")

if __name__ == "__main__":
    main()
