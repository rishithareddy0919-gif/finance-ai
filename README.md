# Personal Financial Intelligence & Risk Analysis System

An AI-agent decision-support app for an Artificial Intelligence course. All data is synthetic. This is NOT a banking app.
The system advises ("potentially unusual"); the user decides.

## Run it
Backend (Python 3.10+), from `backend/`:

    pip install fastapi "uvicorn[standard]" python-multipart pytest httpx
    pytest -v
    uvicorn main:app --reload          # API docs at http://127.0.0.1:8000/docs

Frontend (Node 18+), in a second terminal, from `frontend/`:

    npm install
    npm run dev                        # http://localhost:5173

Open the app, click **Reset demo data** on the Dashboard, then **Demo scenario**.

Optional Gemini features (screenshot reading and written explanations):

    export GEMINI_API_KEY=your-key     # backend only; optional GEMINI_MODEL
Without a key the app still works: screenshots open an empty form to fill in, and explanations use template text.

Evaluation report in the terminal: `python seed.py && python evaluate.py`

## Where the AI lives (all plain Python, one concept per file)
| File | Concept |
|---|---|
| `profile.py` | Statistical learning of "normal" (mean, std, normal range, typical hours) |
| `knowledge_base.py` | Knowledge representation (merchant and keyword categories) |
| `rules.py` | Forward-chaining rule engine; rules are data |
| `bayes.py` + `bayes_cpt.json` | Bayesian network, inference by marginalization, explanation by removal |
| `agent.py` + `agent_config.json` | Goal-based agent choosing tools; thresholds in config |
| `prediction.py` | Run-rate and least-squares regression |
| `evaluate.py` | Leave-one-out evaluation against hidden labels |
| `vision.py`, `explain.py`, `gemini.py` | Gemini: reads screenshots, writes explanations. Never calculates risk. |

## Design decisions worth knowing
- Transactions awaiting the user's answer, and flagged ones, are `pending_confirmation` and are excluded from learning "normal".
  The seed applies the same rule to its 9 planted anomalies. The Evaluation page also shows a "contaminated profile" run for comparison.
- A merchant is "new" if it appeared fewer than 2 times in confirmed history before the transaction's date.
- Monthly averages use completed months; the current month is compared against them.
- `planted_label` is never returned by the API. The Evaluation report shows only a plain-language group.
