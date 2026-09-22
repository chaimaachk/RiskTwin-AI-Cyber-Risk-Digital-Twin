"""
nvidia_client.py
Thin client around an NVIDIA NIM (or any OpenAI-compatible) chat completion
endpoint, plus the two structured prompt templates RiskTwin needs:

  1. analyze_scenario()  -> executive/technical impact analysis
  2. analyze_evidence()  -> evidence-gap analysis from an uploaded document

Design rule: the engine (risk_engine.py / scenario_engine.py) computes all
scores. The AI only *explains* structured data it is given -- it is
explicitly instructed not to invent assets, controls, or scores.
"""

import os
import json
import requests

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
# Any NVIDIA-hosted chat model works here; swap as needed.
DEFAULT_MODEL = "meta/llama-3.1-70b-instruct"


def _call_model(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL,
                 max_tokens: int = 900, temperature: float = 0.2) -> str:
    if not NVIDIA_API_KEY:
        raise RuntimeError(
            "NVIDIA_API_KEY environment variable is not set. "
            "Get a key at https://build.nvidia.com and export it before running the app."
        )

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    response = requests.post(NVIDIA_API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _safe_parse_json(raw: str) -> dict:
    """
    Models sometimes wrap JSON in markdown fences -- strip those before parsing.
    Falls back to a raw-text wrapper if parsing fails, so the UI never crashes.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw_response": raw}


SCENARIO_SYSTEM_PROMPT = """You are a cybersecurity GRC analyst assistant embedded in RiskTwin, \
a cyber risk digital twin tool. You are given structured organizational data: affected assets, \
risk scores computed by a deterministic engine (before and after a what-if scenario), and \
relevant ISO 27001 / NIST CSF controls. Analyze ONLY the data provided. Do not invent assets, \
controls, or risk scores that are not present in the supplied data. Respond ONLY with a JSON \
object with exactly these keys: executive_impact, technical_impact, affected_controls, \
recommended_actions (an array of short strings, ordered by priority), residual_risk, priority \
(one of LOW, MEDIUM, HIGH, CRITICAL). No text outside the JSON object."""


def analyze_scenario(scenario_payload: dict, org_name: str = "AtlasPay",
                      model: str = DEFAULT_MODEL) -> dict:
    """
    scenario_payload: the dict returned by scenario_engine.run_scenario().
    Returns a dict with the 6 fixed sections described in SCENARIO_SYSTEM_PROMPT.
    """
    user_prompt = f"""Organization: {org_name}

Scenario: {scenario_payload['scenario_name']}
Description: {scenario_payload['description']}
Affected chain: {" -> ".join(scenario_payload['affected_chain'])}

Affected assets:
{json.dumps(scenario_payload['affected_assets'], indent=2)}

Affected risks (before/after the scenario, scores computed deterministically):
{json.dumps(scenario_payload['affected_risks'], indent=2)}

Relevant controls (ISO 27001 / NIST CSF mapping):
{json.dumps(scenario_payload['relevant_controls'], indent=2)}

Overall exposure: {scenario_payload['exposure_before']} -> {scenario_payload['exposure_after']}

Analyze this scenario using only the data above. Explain the business impact, technical impact, \
affected controls, recommended mitigations (ordered by priority), and residual risk."""

    raw = _call_model(SCENARIO_SYSTEM_PROMPT, user_prompt, model=model)
    return _safe_parse_json(raw)


EVIDENCE_SYSTEM_PROMPT = """You are a compliance evidence reviewer embedded in RiskTwin. You are \
given the extracted text of an uploaded document and a list of evidence items required for a \
specific risk/control topic. Determine which required evidence items are clearly present in the \
document text, which are missing, and give an overall coverage rating. Do not assume evidence \
exists if it is not explicitly stated in the document text. Respond ONLY with a JSON object with \
exactly these keys: found_evidence (array of strings), missing_evidence (array of strings), \
coverage (one of NONE, PARTIAL, FULL), notes (a short string). No text outside the JSON object."""


def analyze_evidence(document_text: str, control_topic: str, required_evidence: list,
                      model: str = DEFAULT_MODEL) -> dict:
    user_prompt = f"""Control topic: {control_topic}

Required evidence items:
{json.dumps(required_evidence, indent=2)}

Document text (extracted from uploaded file):
{document_text}

Identify which required evidence items are present and which are missing, based only on this \
document text."""

    raw = _call_model(EVIDENCE_SYSTEM_PROMPT, user_prompt, model=model)
    return _safe_parse_json(raw)
