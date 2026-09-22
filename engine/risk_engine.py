"""
risk_engine.py
Deterministic, non-AI risk scoring for RiskTwin.

Score = Likelihood x Impact (both 1-5)

Bands:
  1-4    Low
  5-9    Medium
  10-16  High
  17-25  Critical
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_assets():
    return load_json("assets.json")


def load_risks():
    return load_json("risks.json")


def load_controls():
    return load_json("controls.json")


def load_scenarios():
    return load_json("scenarios.json")


def risk_score(likelihood: int, impact: int) -> int:
    return likelihood * impact


def risk_level(score: int) -> str:
    if score <= 4:
        return "Low"
    if score <= 9:
        return "Medium"
    if score <= 16:
        return "High"
    return "Critical"


def score_all_risks(risks=None, assets=None):
    """
    Returns risks enriched with score, level, and asset name.
    """
    risks = risks if risks is not None else load_risks()
    assets = assets if assets is not None else load_assets()
    asset_by_id = {a["asset_id"]: a for a in assets}

    scored = []
    for r in risks:
        score = risk_score(r["likelihood"], r["impact"])
        level = risk_level(score)
        asset = asset_by_id.get(r["asset_id"], {})
        scored.append({
            **r,
            "asset_name": asset.get("name", "Unknown asset"),
            "score": score,
            "level": level,
        })
    return sorted(scored, key=lambda x: x["score"], reverse=True)


def organization_summary(risks=None, assets=None):
    """
    Aggregate KPIs for the dashboard screen.
    """
    risks = risks if risks is not None else load_risks()
    assets = assets if assets is not None else load_assets()
    scored = score_all_risks(risks, assets)

    total_assets = len(assets)
    critical_assets = len([a for a in assets if a["business_criticality"] >= 5])
    open_risks = len(scored)
    high_risks = len([r for r in scored if r["level"] in ("High", "Critical")])

    # Simple, transparent coverage proxy: assets with at least one mapped risk
    # under a topic assumed "controlled" is out of scope for MVP -- use a
    # placeholder deterministic formula instead: 100 - (high risk ratio * 100),
    # floored at 0, capped at 100.
    if open_risks > 0:
        coverage = max(0, round(100 - (high_risks / open_risks) * 100))
    else:
        coverage = 100

    level_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for r in scored:
        level_counts[r["level"]] += 1

    if level_counts["Critical"] > 0:
        overall_exposure = "CRITICAL"
    elif level_counts["High"] > 0:
        overall_exposure = "HIGH"
    elif level_counts["Medium"] > 0:
        overall_exposure = "MEDIUM"
    else:
        overall_exposure = "LOW"

    return {
        "total_assets": total_assets,
        "critical_assets": critical_assets,
        "open_risks": open_risks,
        "high_risks": high_risks,
        "control_coverage_pct": coverage,
        "overall_exposure": overall_exposure,
        "level_counts": level_counts,
        "top_risk": scored[0] if scored else None,
    }


if __name__ == "__main__":
    # Quick manual check: python engine/risk_engine.py
    summary = organization_summary()
    print(json.dumps(summary, indent=2))
