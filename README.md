# RiskTwin — AI-Powered Cyber Risk Simulation & Compliance Intelligence

AI cyber risk digital twin for a fictional Moroccan fintech, **AtlasPay**:
upload/enter security data → deterministic risk engine → what-if scenario
simulation → AI-generated business impact analysis → ISO 27001 / NIST CSF
mapping → evidence gap analysis from uploaded documents.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Get a free NVIDIA NIM API key at https://build.nvidia.com and export it:

```bash
export NVIDIA_API_KEY="your-key-here"     # Windows: set NVIDIA_API_KEY=your-key-here
```

## Run

```bash
streamlit run app.py
```

## Project structure

```
risktwin/
├── data/
│   ├── assets.json       # 15 AtlasPay assets
│   ├── risks.json        # 13 seeded risks (Likelihood x Impact scoring)
│   ├── controls.json     # ISO 27001 / NIST CSF mapping, ~15 topics
│   └── scenarios.json    # 4 what-if scenarios (MFA failure, unpatched vuln,
│                          #   vendor breach, backup unavailable)
├── engine/
│   ├── risk_engine.py     # deterministic scoring (no AI)
│   ├── scenario_engine.py # what-if propagation (no AI)
│   └── doc_parser.py      # PDF text extraction
├── ai/
│   └── nvidia_client.py   # NVIDIA NIM prompt templates + API call
├── app.py                 # Streamlit UI (5 screens)
└── requirements.txt
```

## Design principle

The risk engine and scenario engine are **fully deterministic** — scores are
always `Likelihood x Impact`, and scenario deltas are fixed values from
`scenarios.json`. The AI layer only explains structured output it is handed;
it is explicitly instructed not to invent assets, controls, or scores.

## Core screens

1. **Dashboard** — org-level KPIs, risk distribution, overall exposure.
2. **Risk Register** — full scored risk list.
3. **What-If Simulator** — pick a scenario, see before/after scores, get an
   AI-generated executive/technical impact analysis with priority and
   recommended actions.
4. **Compliance** — ISO 27001 / NIST CSF mapping per risk, with recommended
   evidence.
5. **Evidence** — upload a PDF (policy, vendor questionnaire) and get an
   AI-generated evidence coverage report against a chosen control topic.

## If you're short on time

Priority order if you need to cut scope: keep **Risk Engine → What-If
Simulator → AI Analysis → ISO/NIST Mapping**. Drop the Evidence screen last.
