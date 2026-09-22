"""
scenario_engine.py
Deterministic what-if propagation for RiskTwin.

Given a scenario_id, this identifies affected assets and risks, computes
before/after scores using the scenario's fixed deltas, and packages a
structured payload for the AI layer to explain. No AI is used here --
this is the transparent, reproducible core the AI layer must not override.
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))
from risk_engine import (  # noqa: E402
    load_assets, load_risks, load_controls, load_scenarios,
    risk_score, risk_level,
)


def get_scenario(scenario_id, scenarios=None):
    scenarios = scenarios if scenarios is not None else load_scenarios()
    for s in scenarios:
        if s["scenario_id"] == scenario_id:
            return s
    raise ValueError(f"Unknown scenario_id: {scenario_id}")


def run_scenario(scenario_id, assets=None, risks=None, controls=None, scenarios=None):
    """
    Returns a structured dict describing the scenario's effect:
      - scenario metadata (name, description, chain)
      - affected assets (full records)
      - affected risks, each with before/after score + level
      - relevant controls (ISO/NIST mapping)
    """
    assets = assets if assets is not None else load_assets()
    risks = risks if risks is not None else load_risks()
    controls = controls if controls is not None else load_controls()
    scenario = get_scenario(scenario_id, scenarios)

    asset_by_id = {a["asset_id"]: a for a in assets}
    target_ids = set(scenario["target_asset_ids"])

    affected_assets = [asset_by_id[aid] for aid in target_ids if aid in asset_by_id]

    affected_risks = []
    for r in risks:
        if r["asset_id"] not in target_ids:
            continue
        before_score = risk_score(r["likelihood"], r["impact"])
        new_likelihood = min(5, r["likelihood"] + scenario.get("likelihood_delta", 0))
        new_impact = min(5, r["impact"] + scenario.get("impact_delta", 0))
        after_score = risk_score(new_likelihood, new_impact)
        affected_risks.append({
            "risk_id": r["risk_id"],
            "name": r["name"],
            "asset_id": r["asset_id"],
            "asset_name": asset_by_id.get(r["asset_id"], {}).get("name", "Unknown"),
            "control_topic": r.get("control_topic"),
            "before": {
                "likelihood": r["likelihood"], "impact": r["impact"],
                "score": before_score, "level": risk_level(before_score),
            },
            "after": {
                "likelihood": new_likelihood, "impact": new_impact,
                "score": after_score, "level": risk_level(after_score),
            },
        })

    relevant_topics = set(scenario.get("related_control_topics", []))
    relevant_controls = [c for c in controls if c["topic"] in relevant_topics]

    # Overall before/after exposure, using the worst affected risk level
    def worst_level(items, key):
        order = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
        levels = [i[key]["level"] for i in items] if items else ["Low"]
        return max(levels, key=lambda lv: order[lv])

    exposure_before = worst_level(affected_risks, "before")
    exposure_after = worst_level(affected_risks, "after")

    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["name"],
        "description": scenario["description"],
        "affected_chain": scenario["affected_chain"],
        "affected_assets": affected_assets,
        "affected_risks": affected_risks,
        "relevant_controls": relevant_controls,
        "exposure_before": exposure_before,
        "exposure_after": exposure_after,
    }


if __name__ == "__main__":
    import json
    result = run_scenario("SCN-A")
    print(json.dumps(result, indent=2))
