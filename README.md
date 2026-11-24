# LocalHarvey — Fully Local Multi-Product AI Sales Agent

Zero paid LLM cost. All inference via local Ollama. Offline-capable after model download.

Built for the EDXSO AI Engineer Intern Assignment 2 (Harvey AI Sales Agent — local multi-product extension).

## What works fully offline (after model download)

- Business profile generation from stored company data
- Product-specific ICP generation
- Prospect research from previously downloaded / seeded data
- Buying-signal classification
- Problem statement generation
- Prospect scoring & prioritisation (LLM **or** deterministic rules if Ollama is down)
- Personalised outreach email generation
- Reply classification on sample conversations
- Inference logging & hardware-aware model recommendation

Optional public-web enrichment is **explicit** (`allow_web=true`) and is never required for the offline acceptance test.

## Quick start

```bash
# 1. Setup
chmod +x scripts/setup.sh run.sh
./scripts/setup.sh

# 2. Ollama (separate terminal)
ollama serve
ollama pull qwen2.5:7b-instruct   # or phi3:mini on low RAM

# 3. Run
source .venv/bin/activate
export PROFILE=standard          # auto | standard | high | minimal
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 → **Seed Demo Data** → run Full Workflow.

## Hardware profiles

| Profile | Target | Default model (Apache-2.0 / MIT) |
|---------|--------|----------------------------------|
| `minimal` | &lt; 8 GB RAM | `phi3:mini` |
| `standard` | Ordinary laptop 8–16 GB | `qwen2.5:7b-instruct` |
| `high` | 16–32 GB / modest GPU | `qwen2.5:14b-instruct` |
| `auto` | Detect at runtime | Chooses from above |

Set `PROFILE` or `DEFAULT_MODEL` in `.env`. Recommendation is applied at runtime (not only displayed).

## Project structure

```
local-harvey/
├── backend/
│   ├── main.py              # FastAPI app + workflows
│   ├── config.py            # Settings + profiles
│   ├── database.py          # SQLite schema (incl. task_queue)
│   ├── ollama_client.py     # Local-only client, format=json, fallback model
│   ├── hardware.py          # RAM/GPU detection + safe model recommendation
│   ├── embeddings.py        # Sentence-Transformers + hash fallback
│   ├── agents/              # 8 sales agents
│   └── utils/web_research.py# Optional BeautifulSoup enrichment
├── frontend/                # Dashboard (served by FastAPI)
├── sample_data/             # Offline companies, products, 10 prospects, 10 replies
├── docs/                    # Architecture, licences, offline test, cost statement, limitations
├── tests/                   # pytest suite (no Ollama required)
└── scripts/setup.sh
```

## Failure handling

- Ollama down → HTTP 503 + clear message (no cloud fallback).
- Scoring still works via **deterministic rule-based scorer**.
- Failed tasks can be written to `task_queue` for later local processing.

## Documentation

- `docs/COST_AND_DEPENDENCY.md` — zero paid LLM proof
- `docs/MODEL_LICENCES.md` — Apache-2.0 / MIT only
- `docs/OFFLINE_TEST.md` — acceptance test checklist
- `docs/KNOWN_LIMITATIONS.md` — honest scope
- `DEMO.md` — screen-recording script

## Tests

```bash
pip install pytest
pytest tests/ -q
```

## Licence note

Application code is provided for the assignment evaluation. Models and libraries retain their upstream licences (see `docs/MODEL_LICENCES.md`).
> Built on ideas from the open-source Sellbird project. See [docs/LEGACY_CODE_NOTICE.md](docs/LEGACY_CODE_NOTICE.md) for details. Upstream code is not included in this repo.