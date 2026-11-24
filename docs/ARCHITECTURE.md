# Architecture — LocalHarvey

## High-level Design

```
┌─────────────────────────────────────────────────────────┐
│                     Browser Dashboard                    │
│              (static HTML/CSS/JS served by FastAPI)      │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────┐
│                     FastAPI Backend                      │
│  /api/status  /api/companies  /api/products              │
│  /api/prospects  /api/workflows/*  /api/logs             │
└────────┬─────────────────┬──────────────────┬───────────┘
         │                 │                  │
   ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼──────┐
   │  SQLite   │    │   Agents    │    │   Ollama    │
   │ localharvey.db │ (profile,   │    │ 127.0.0.1  │
   │             │    ICP, research│    │ :11434     │
   │             │    signals,    │    │ (Qwen etc) │
   │             │    outreach…)  │    └────────────┘
   └─────────────┘    └────────────┘
```

## Core Principles

1. **Zero paid LLM** — every generation call goes only to Ollama on localhost.
2. **Fail closed** — if Ollama is unreachable the API returns a clear 503. No silent cloud fallback exists in the code.
3. **Hardware awareness** — on startup and `/api/status` the system measures RAM/CPU/GPU and recommends an appropriate model size.
4. **Offline-first AI** — after models are pulled, all listed acceptance-test workflows run without internet.
5. **Traceability** — every inference is logged (agent, model, prompt hash, latency, success).

## Agent Responsibilities

| Agent                  | Input                         | Output                          | Offline? |
|------------------------|-------------------------------|---------------------------------|----------|
| Business Profile       | Company + products            | Structured profile JSON         | Yes      |
| ICP                    | Product + business profile    | Full ICP                        | Yes      |
| Research               | Prospect + stored raw data    | Research summary                | Yes*     |
| Buying Signals         | Prospect + research + ICP     | Signal list + strength          | Yes      |
| Problem Statement      | Prospect + research + signals | Problem narrative               | Yes      |
| Scoring                | All of the above              | 0-100 score + breakdown         | Yes      |
| Outreach               | Prospect + problem + product  | Subject + body                  | Yes      |
| Reply Classifier       | Reply text (+ optional original) | Classification + confidence  | Yes      |

\* Research can optionally use live public web when online; the demo path uses pre-seeded raw_data so it works offline.

## Data Model (SQLite)

- `companies` / `products` — multi-product support
- `business_profiles` / `icps` — versioned AI outputs
- `prospects` — central entity with status progression
- `outreach_emails` / `conversations` — generated content + reply classifications
- `inference_logs` — audit trail of every local model call

## Security / Constraint Enforcement

`backend/ollama_client.py` contains an explicit host check:

```python
if not (host.startswith("http://127.0.0.1") or host.startswith("http://localhost")):
    raise LocalLLMError("SECURITY: ... Cloud endpoints are forbidden")
```

`settings.allow_external_llm` is hard-coded `False`.

## Failure Handling

- Ollama down → clear HTTP 503 with instructions
- JSON parse failure from model → one controlled retry with stronger instruction
- Missing prospect / company → 404
- No silent degradation to any external inference service
