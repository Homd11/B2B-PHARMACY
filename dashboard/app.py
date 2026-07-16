# -*- coding: utf-8 -*-
"""
Pharma Multi-Warehouse Sales Dashboard
Run:  streamlit run app.py
Reads the star schema produced by Notebook 3 from ./warehouse/
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Pharma Sales — Unified", page_icon="💊",
                   layout="wide", initial_sidebar_state="expanded")

WH = Path(__file__).parent / "warehouse"

# ---------------------------------------------------------------- data layer
@st.cache_data
def load():
    fact = pd.read_csv(WH / "fact_sales.csv", parse_dates=["tx_date"])
    d = {
        "product":  pd.read_csv(WH / "dim_product.csv"),
        "pharmacy": pd.read_csv(WH / "dim_pharmacy.csv"),
        "rep":      pd.read_csv(WH / "dim_rep.csv"),
        "supplier": pd.read_csv(WH / "dim_supplier.csv", parse_dates=["first_tx", "last_tx"]),
    }
    extras = {}
    for name in ["anomalies_supplier_weeks", "anomalies_transactions", "forecast_benchmark"]:
        p = WH / f"{name}.csv"
        extras[name] = pd.read_csv(p) if p.exists() else pd.DataFrame()
    impact = pd.read_json(WH / "impact_summary.json", typ="series") if (WH / "impact_summary.json").exists() else pd.Series(dtype=float)
    hq_p = Path(__file__).parent / "hitl_queue.csv"
    extras["hitl"] = pd.read_csv(hq_p) if hq_p.exists() else pd.DataFrame()
    src_p = Path(__file__).parent / "resolved_sales.csv"
    extras["src"] = pd.read_csv(src_p, parse_dates=["tx_date"]) if src_p.exists() else pd.DataFrame()
    return fact, d, extras, impact

fact, dim, extras, impact = load()
ACCENT, GOOD, BAD, MUTED = "#0F766E", "#15803D", "#B91C1C", "#64748B"
PALETTE = ["#0F766E", "#B45309", "#1D4ED8", "#9333EA", "#BE123C",
           "#047857", "#A16207", "#4338CA", "#C2410C", "#0E7490"]

def egp(x): return f"EGP {x:,.0f}"

# ---------------------------------------------------------------- sidebar
st.sidebar.title("💊 Pharma Sales — Unified")
page = st.sidebar.radio("Pages", [
    "Overview", "Unification impact", "Products", "Pharmacies",
    "Sales reps", "Anomalies & alerts", "Forecast bench", "HITL queue"])
sups = sorted(fact["supplier_id"].unique())
sel_sups = st.sidebar.multiselect("Suppliers", sups, default=sups)
f = fact[fact["supplier_id"].isin(sel_sups)]
st.sidebar.caption("Data: 10 warehouses · entities resolved by the "
                   "Notebook 2 pipeline · source keys retained for lineage.")

# ---------------------------------------------------------------- pages
if page == "Overview":
    st.title("Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Revenue", egp(f["total_amount"].sum()))
    c2.metric("Transactions", f"{len(f):,}")
    c3.metric("Master products", f"{f['product_key'].nunique():,}")
    c4.metric("Master pharmacies", f"{f['pharmacy_key'].nunique():,}")
    c5.metric("Suppliers", f["supplier_id"].nunique())

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Monthly revenue per supplier")
        st.caption("Plotted per supplier deliberately — export windows are disjoint "
                   "(supplier 60 is a single day; 76 is 2022–24 history). "
                   "A unified trend line would be an artifact, not a trend.")
        t = f.copy(); t["month"] = t["tx_date"].dt.to_period("M").astype(str)
        piv = t.groupby(["month", "supplier_id"])["total_amount"].sum().reset_index()
        figm = px.line(piv, x="month", y="total_amount", color="supplier_id",
                       color_discrete_sequence=PALETTE, labels={"total_amount": "EGP"})
        figm.update_layout(height=380, legend_title="supplier")
        st.plotly_chart(figm, use_container_width=True)
    with right:
        st.subheader("Revenue by supplier")
        rs = f.groupby("supplier_id")["total_amount"].sum().sort_values()
        figb = px.bar(rs, orientation="h", color_discrete_sequence=[ACCENT],
                      labels={"value": "EGP", "supplier_id": "supplier"})
        figb.update_layout(height=380, showlegend=False)
        st.plotly_chart(figb, use_container_width=True)

    st.subheader("Supplier coverage windows")
    cov = dim["supplier"].copy()
    figg = px.timeline(cov, x_start="first_tx", x_end="last_tx", y="supplier_id",
                       color_discrete_sequence=[MUTED])
    figg.update_yaxes(autorange="reversed"); figg.update_layout(height=300)
    st.plotly_chart(figg, use_container_width=True)

elif page == "Unification impact":
    st.title("Before vs after entity resolution")
    st.markdown("The ROI of the resolution pipeline, measured — *before* = aggregating raw "
                "name strings, *after* = aggregating master entities.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue that was fragmented", egp(impact.get("fragmented_revenue_egp", 0)),
              f"{impact.get('fragmented_revenue_pct', 0)}% of total")
    c2.metric("Products under multiple names", int(impact.get("masters_with_multiple_names", 0)))
    c3.metric("Pharmacies unified", int(impact.get("pharmacies_unified", 0)))
    c4.metric("Channel revenue un-crowned", egp(impact.get("channel_revenue_egp", 0)),
              "excluded from rep leaderboard", delta_color="off")

    src = extras["src"]
    if not src.empty:
        st.subheader("Top-15 products — raw names vs masters")
        colA, colB = st.columns(2)
        before = (src.groupby("product_name")["total_amount"].sum()
                     .nlargest(15).reset_index()
                     .rename(columns={"product_name": "raw name", "total_amount": "EGP"}))
        with colA:
            st.markdown("**Before** · raw strings")
            st.dataframe(before, use_container_width=True, height=560, hide_index=True)
        merged = f.merge(dim["product"][["product_key", "canonical_name", "n_name_variants"]],
                         on="product_key")
        after = (merged.groupby(["canonical_name", "n_name_variants"])["total_amount"].sum()
                       .nlargest(15).reset_index()
                       .rename(columns={"canonical_name": "master product",
                                        "n_name_variants": "variants", "total_amount": "EGP"}))
        with colB:
            st.markdown("**After** · master entities")
            st.dataframe(after, use_container_width=True, height=560, hide_index=True)

        st.subheader("Biggest climbers — true size hidden by fragmentation")
        name2m = src.groupby("product_name")["product_master_id"].first()
        rb = src.groupby("product_name")["total_amount"].sum().rank(ascending=False)
        ra = src.groupby("product_master_id")["total_amount"].sum().rank(ascending=False)
        variants = name2m.reset_index().groupby("product_master_id")["product_name"].apply(list)
        rows = []
        for m, names in variants.items():
            if len(names) < 2:
                continue
            rows.append({"master": m, "variants": len(names),
                         "best rank before": min(rb.get(n, np.inf) for n in names),
                         "rank after": ra.get(m, np.nan)})
        sh = pd.DataFrame(rows)
        sh["rank gain"] = sh["best rank before"] - sh["rank after"]
        canon = dim["product"].set_index("master_idx")["canonical_name"]
        sh["product"] = sh["master"].map(canon)
        st.dataframe(sh.nlargest(12, "rank gain")
                       [["product", "variants", "best rank before", "rank after", "rank gain"]],
                     use_container_width=True, hide_index=True)

elif page == "Products":
    st.title("Products — master catalog")
    merged = f.merge(dim["product"][["product_key", "canonical_name", "n_name_variants",
                                     "form", "manufacturer"]], on="product_key")
    q = st.text_input("Search product (Arabic or Latin)")
    if q:
        merged = merged[merged["canonical_name"].str.contains(q, case=False, na=False)]
    top = (merged.groupby(["canonical_name", "n_name_variants"])
                 .agg(revenue=("total_amount", "sum"), units=("quantity", "sum"),
                      transactions=("id", "count"), suppliers=("supplier_id", "nunique"))
                 .nlargest(25, "revenue").reset_index())
    st.dataframe(top.rename(columns={"canonical_name": "product",
                                     "n_name_variants": "name variants"}),
                 use_container_width=True, height=520, hide_index=True)
    figp = px.bar(top.head(12), x="revenue", y="canonical_name", orientation="h",
                  color_discrete_sequence=[ACCENT], labels={"canonical_name": ""})
    figp.update_layout(height=420, yaxis=dict(autorange="reversed"))
    st.plotly_chart(figp, use_container_width=True)

elif page == "Pharmacies":
    st.title("Pharmacies — true top customers")
    st.caption("Multi-supplier pharmacies were undercounted before unification; "
               "`suppliers` shows how many warehouses each buys from.")
    merged = f.merge(dim["pharmacy"][["pharmacy_key", "pharmacy_canonical", "n_suppliers",
                                      "address"]], on="pharmacy_key")
    top = (merged.groupby(["pharmacy_canonical", "n_suppliers", "address"])
                 .agg(revenue=("total_amount", "sum"), transactions=("id", "count"))
                 .nlargest(25, "revenue").reset_index()
                 .rename(columns={"pharmacy_canonical": "pharmacy",
                                  "n_suppliers": "suppliers"}))
    st.dataframe(top, use_container_width=True, height=520, hide_index=True)
    multi = dim["pharmacy"][dim["pharmacy"]["n_suppliers"] > 1]
    st.metric("Pharmacies confirmed buying from multiple suppliers", len(multi))

elif page == "Sales reps":
    st.title("Sales reps")
    st.caption("Channel/system accounts (كلاستر، اي سبلاي، توريد…) are tagged and excluded "
               "from the people leaderboard; unattributable revenue is shown as UNKNOWN, not guessed.")
    split = f.groupby("rep_type")["total_amount"].sum().reset_index()
    figd = px.pie(split, names="rep_type", values="total_amount", hole=0.55,
                  color="rep_type", color_discrete_map={"person": ACCENT,
                                                        "channel": "#B45309",
                                                        "unknown": MUTED})
    c1, c2 = st.columns([1, 2])
    with c1:
        figd.update_layout(height=320, showlegend=True)
        st.plotly_chart(figd, use_container_width=True)
    with c2:
        people = (f[f["rep_type"] == "person"]
                  .merge(dim["rep"][["rep_key", "rep_canonical"]], on="rep_key")
                  .groupby("rep_canonical")
                  .agg(revenue=("total_amount", "sum"), transactions=("id", "count"),
                       suppliers=("supplier_id", "nunique"), avg_discount=("discount", "mean"))
                  .nlargest(15, "revenue").round(1).reset_index()
                  .rename(columns={"rep_canonical": "rep"}))
        st.dataframe(people, use_container_width=True, height=380, hide_index=True)

elif page == "Anomalies & alerts":
    st.title("Anomalies & alerts")
    aw = extras["anomalies_supplier_weeks"]
    if not aw.empty:
        st.subheader("Supplier-week revenue anomalies (|robust z| > 3)")
        aw2 = aw[aw["supplier_id"].isin(sel_sups)].copy()
        figa = px.scatter(aw2, x="week", y="total_amount", color="direction",
                          color_discrete_map={"DROP": BAD, "SPIKE": GOOD},
                          hover_data=["supplier_id", "rzscore"], size_max=12)
        figa.update_layout(height=360)
        st.plotly_chart(figa, use_container_width=True)
        st.dataframe(aw2.sort_values("rzscore").round(1), use_container_width=True,
                     hide_index=True)
    at = extras["anomalies_transactions"]
    if not at.empty:
        st.subheader("Transaction-level outliers (IsolationForest, top 1%)")
        at2 = at[at["supplier_id"].isin(sel_sups)]
        st.dataframe(at2.sort_values("iso_score", ascending=False).head(50).round(2),
                     use_container_width=True, height=420, hide_index=True)

elif page == "Forecast bench":
    st.title("Forecast benchmark — champion/challenger")
    st.caption("WMAPE on a 4-week holdout. Where ETS fails to beat the naive baselines, "
               "the naive forecast ships. Suppliers without continuous coverage are excluded.")
    fb = extras["forecast_benchmark"]
    if not fb.empty:
        st.dataframe(fb.round(2), use_container_width=True, hide_index=True)
        avg = fb[[c for c in ["naive", "ma4", "ets"] if c in fb]].mean().round(2)
        st.bar_chart(avg)
    st.subheader("Weekly series viewer")
    merged = f.merge(dim["product"][["product_key", "canonical_name"]], on="product_key")
    stats = (merged.groupby("canonical_name")
                   .agg(tx=("id", "count")).nlargest(40, "tx").reset_index())
    pick = st.selectbox("Product", stats["canonical_name"])
    s = merged[merged["canonical_name"] == pick].copy()
    s["week"] = s["tx_date"].dt.to_period("W").dt.start_time
    ws = s.groupby(["week", "supplier_id"])["quantity"].sum().reset_index()
    figw = px.bar(ws, x="week", y="quantity", color="supplier_id",
                  color_discrete_sequence=PALETTE)
    figw.update_layout(height=360)
    st.plotly_chart(figw, use_container_width=True)

elif page == "HITL queue":
    st.title("Human-in-the-loop review queue")
    st.caption("Uncertain pairs the pipeline refuses to auto-decide, revenue-impact sorted. "
               "In production this queue is served pair-by-pair on Telegram via n8n; "
               "price-based suggestions appear as pre-selected defaults.")
    hq = extras["hitl"]
    if not hq.empty:
        ent = st.selectbox("Entity", hq["entity"].unique().tolist())
        sub = hq[hq["entity"] == ent]
        c1, c2, c3 = st.columns(3)
        c1.metric("Pairs awaiting review", len(sub))
        if "impact_egp" in sub:
            c2.metric("Revenue at stake", egp(sub["impact_egp"].sum()))
        if "price_evidence" in sub:
            c3.metric("With price suggestion", int(sub["price_evidence"].notna().sum()))
        cols = [c for c in ["raw_a", "raw_b", "score", "impact_egp",
                            "price_suggested_strength", "price_evidence"] if c in sub]
        st.dataframe(sub[cols].head(200), use_container_width=True, height=560,
                     hide_index=True)

st.sidebar.divider()
st.sidebar.caption("Pipeline: NB1 cleaning → NB2 entity resolution → NB3 star schema "
                   "→ NB4 ML → this dashboard.")
