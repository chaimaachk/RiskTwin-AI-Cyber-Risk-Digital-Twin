"""
app.py
RiskTwin -- AI-Powered Cyber Risk Simulation & Compliance Intelligence
Streamlit UI. Run with: streamlit run app.py
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "engine"))
sys.path.append(os.path.join(os.path.dirname(__file__), "ai"))

import streamlit as st
import pandas as pd

from risk_engine import (
    load_assets, load_risks, load_controls,
    score_all_risks, organization_summary,
)
from scenario_engine import run_scenario, get_scenario
from risk_engine import load_scenarios
from doc_parser import extract_text_from_pdf, truncate_for_prompt

ORG_NAME = "AtlasPay"

st.set_page_config(page_title="RiskTwin", layout="wide")

# ---------- Sidebar ----------
st.sidebar.title("🛡️ RISKTWIN")
page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Risk Register", "What-If Simulator", "Compliance", "Evidence"],
)

assets = load_assets()
risks = load_risks()
controls = load_controls()
scenarios = load_scenarios()
scored_risks = score_all_risks(risks, assets)

# ============================================================
# DASHBOARD
# ============================================================
if page == "Dashboard":
    st.title(f"{ORG_NAME} Cyber Risk Overview")

    summary = organization_summary(risks, assets)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Assets", summary["total_assets"])
    c2.metric("Open Risks", summary["open_risks"])
    c3.metric("Critical Assets", summary["critical_assets"])
    c4.metric("Control Coverage", f"{summary['control_coverage_pct']}%")

    exposure_color = {
        "LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴",
    }
    st.subheader(
        f"Overall exposure: {exposure_color.get(summary['overall_exposure'], '')} "
        f"{summary['overall_exposure']}"
    )

    st.markdown("#### Risk distribution")
    
    # Polished and explicitly ordered category chart for judges
    level_order = ["Critical", "High", "Medium", "Low"]
    raw_counts = summary["level_counts"]
    # Reindex or map counts to the logical GRC severity order
    ordered_counts = {lvl: raw_counts.get(lvl, 0) for lvl in level_order}
    
    dist_df = pd.DataFrame({
        "Risk Level": list(ordered_counts.keys()),
        "Count": list(ordered_counts.values()),
    })
    
    st.bar_chart(dist_df, x="Risk Level", y="Count", color="Risk Level")

    if summary["top_risk"]:
        top = summary["top_risk"]
        st.markdown("#### Top Risk")
        st.error(f"**{top['name']}** — {top['level']} (score {top['score']}) on {top['asset_name']}")

# ============================================================
# RISK REGISTER
# ============================================================
elif page == "Risk Register":
    st.title("Risk Register")
    df = pd.DataFrame(scored_risks)[
        ["name", "asset_name", "likelihood", "impact", "score", "level"]
    ].rename(columns={
        "name": "Risk", "asset_name": "Asset", "likelihood": "Likelihood",
        "impact": "Impact", "score": "Score", "level": "Level",
    })

    def highlight_level(val):
        colors = {"Critical": "#ffcccc", "High": "#ffe0b3", "Medium": "#fff5cc", "Low": "#d9f2d9"}
        return f"background-color: {colors.get(val, '')}"

    st.dataframe(df.style.map(highlight_level, subset=["Level"]), use_container_width=True)

# ============================================================
# WHAT-IF SIMULATOR
# ============================================================
elif page == "What-If Simulator":
    st.title("What-If Simulator")

    scenario_names = {s["scenario_id"]: s["name"] for s in scenarios}
    chosen_id = st.selectbox(
        "Choose a scenario",
        options=list(scenario_names.keys()),
        format_func=lambda sid: scenario_names[sid],
    )
    scenario_meta = get_scenario(chosen_id, scenarios)
    st.caption(scenario_meta["description"])
    st.markdown("**Propagation chain:** " + " → ".join(scenario_meta["affected_chain"]))

    if st.button("Simulate", type="primary"):
        with st.spinner("Running deterministic scenario engine..."):
            result = run_scenario(chosen_id, assets, risks, controls, scenarios)
        st.session_state["last_scenario_result"] = result

    result = st.session_state.get("last_scenario_result")
    if result and result["scenario_id"] == chosen_id:
        colb, colm, cola = st.columns(3)
        colb.metric("Exposure before", result["exposure_before"])
        cola.metric("Exposure after", result["exposure_after"])

        st.markdown("#### Affected risks (before → after)")
        rows = []
        for r in result["affected_risks"]:
            rows.append({
                "Risk": r["name"], "Asset": r["asset_name"],
                "Before": f"{r['before']['score']} ({r['before']['level']})",
                "After": f"{r['after']['score']} ({r['after']['level']})",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        st.markdown("#### AI Analysis")
        if st.button("Generate AI explanation"):
            try:
                from nvidia_client import analyze_scenario
                with st.spinner("Calling NVIDIA model..."):
                    analysis = analyze_scenario(result, org_name=ORG_NAME)
                st.session_state["last_ai_analysis"] = analysis
            except Exception as e:
                st.error(f"AI call failed: {e}")

        analysis = st.session_state.get("last_ai_analysis")
        if analysis:
            if "raw_response" in analysis:
                st.warning("Model did not return valid JSON -- showing raw output.")
                st.write(analysis["raw_response"])
            else:
                st.markdown(f"**Priority: {analysis.get('priority', 'N/A')}**")
                st.markdown("**Executive Impact**")
                st.write(analysis.get("executive_impact", ""))
                st.markdown("**Technical Impact**")
                st.write(analysis.get("technical_impact", ""))
                st.markdown("**Affected Controls**")
                st.write(analysis.get("affected_controls", ""))
                st.markdown("**Recommended Actions**")
                for i, action in enumerate(analysis.get("recommended_actions", []), 1):
                    st.write(f"{i}. {action}")
                st.markdown("**Residual Risk**")
                st.write(analysis.get("residual_risk", ""))

# ============================================================
# COMPLIANCE
# ============================================================
elif page == "Compliance":
    st.title("ISO 27001 / NIST CSF Mapping")

    control_by_topic = {c["topic"]: c for c in controls}
    rows = []
    for r in scored_risks:
        c = control_by_topic.get(r.get("control_topic"))
        rows.append({
            "Risk": r["name"],
            "Level": r["level"],
            "ISO 27001": c["iso27001"] if c else "—",
            "NIST CSF": c["nist_csf"] if c else "—",
            "Recommended evidence": ", ".join(c["recommended_evidence"]) if c else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ============================================================
# EVIDENCE
# ============================================================
elif page == "Evidence":
    st.title("Evidence Analysis")
    st.caption("Upload a policy or vendor questionnaire PDF to check evidence coverage for a control topic.")

    topic_names = [c["topic"] for c in controls]
    chosen_topic = st.selectbox("Control topic", options=topic_names)
    control = next(c for c in controls if c["topic"] == chosen_topic)
    st.write("**Required evidence:**", ", ".join(control["recommended_evidence"]))

    uploaded = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded and st.button("Analyze evidence"):
        try:
            with st.spinner("Extracting text..."):
                text = extract_text_from_pdf(uploaded.read())
                text = truncate_for_prompt(text)
            from nvidia_client import analyze_evidence
            with st.spinner("Calling NVIDIA model..."):
                result = analyze_evidence(text, chosen_topic, control["recommended_evidence"])
            if "raw_response" in result:
                st.warning("Model did not return valid JSON -- showing raw output.")
                st.write(result["raw_response"])
            else:
                st.markdown(f"**Coverage: {result.get('coverage', 'N/A')}**")
                st.markdown("✅ Found evidence:")
                for item in result.get("found_evidence", []):
                    st.write(f"- {item}")
                st.markdown("❌ Missing evidence:")
                for item in result.get("missing_evidence", []):
                    st.write(f"- {item}")
                if result.get("notes"):
                    st.caption(result["notes"])
        except Exception as e:
            st.error(f"Evidence analysis failed: {e}")