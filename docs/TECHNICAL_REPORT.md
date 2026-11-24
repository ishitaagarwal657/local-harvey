# Technical Report — LocalHarvey
**EDXSO AI Engineer Intern — Assignment 2 (Local Multi-Product AI Sales Agent)**
Repository: https://github.com/ishitaagarwal657/harvey
video-https://drive.google.com/file/d/1b9_3qRTjloXjOo51HbsmbUnHYdBgzeio/view?usp=sharing
---

## 1. Summary

LocalHarvey is a multi-product AI sales agent in which **every LLM call is served by a local Ollama instance** (`qwen2.5:7b-instruct`, Apache-2.0). It covers the 8 required workflows (business profile, product ICP, prospect research, buying signals, problem statement, scoring, personalised email, reply classification), stores data in SQLite, serves a dashboard from FastAPI, and logs every inference call.

The offline acceptance test was run with the network disabled after the model download. Results are in section 7.

> **Repository note.** This fork also contains upstream directories (`harvey/`, `sellbird/`, `skills/`, `prompts/`) from the original project, which is designed to run on a Claude/ChatGPT plan. **None of that code is imported or executed by LocalHarvey.** The LocalHarvey application lives in `backend/`, `frontend/`, `sample_data/`, `docs/`, `tests/`. See `docs/LEGACY_CODE_NOTICE.md`.

## 2. Architecture

```
Browser dashboard (frontend/)  ──HTTP──►  FastAPI (backend/main.py)
                                              │
              ┌───────────────────────────────┼──────────────────────────┐
              ▼                               ▼                          ▼
        8 agents (backend/agents)     SQLite (database.py)      hardware.py (RAM/CPU/GPU)
              │                       companies, products,       → model recommendation
              ▼                       prospects, inference_logs,
   ollama_client.py  ──127.0.0.1:11434──►  Ollama (local)   task_queue
   (host lock, JSON mode, logging)          qwen2.5:7b-instruct
              ┊
   utils/web_research.py  (BeautifulSoup, optional, only if allow_web=true;
                           fetches web pages only — never sends data to an LLM service)
```

Local inference and external web research are separate modules. Web research is opt-in per request and is not used in the offline test (`"web_enrichment": {"attempted": false}` in the research output).

## 3. Zero-cost / local-only enforcement

| Control | Where |
|---|---|
| `allow_external_llm = False` | `backend/config.py` |
| Ollama host must be `127.0.0.1` / `localhost`, otherwise the client refuses to start | `backend/ollama_client.py` |
| No OpenAI / Anthropic / Gemini SDKs in `requirements.txt` or `backend/` | verify: `grep -rniE "openai\|anthropic\|gemini" backend requirements.txt` |
| Every call written to `inference_logs` (agent, model, latency, success, timestamp) | `ollama_client.py` → dashboard "Inference Logs" |
| No API keys needed; `.env.example` contains only local settings | `.env.example` |

## 4. Hardware awareness

`/api/status` reports total/available RAM, CPU count and GPU/VRAM, and recommends a model:

| Profile | Machine | Model |
|---|---|---|
| minimal | < 8 GB RAM | `phi3:mini` (MIT) |
| **standard** (used in the demo) | 8–16 GB laptop, CPU only OK | `qwen2.5:7b-instruct` (Apache-2.0) |
| high | 16–32 GB / modest GPU | `qwen2.5:14b-instruct` (Apache-2.0) |
| auto | detect at runtime | picks from above |

No GPU is assumed. The demo ran on a CPU laptop: latencies 6–23 s per call (section 6).

## 5. Failure handling

| Situation | Behaviour |
|---|---|
| Ollama not running | HTTP **503** with a clear message. **No cloud fallback exists anywhere in code.** |
| Scoring while Ollama is down | Deterministic rule-based scorer (no LLM) returns a result with `"fallback": true`. |
| Research while Ollama is down | Task is written to `task_queue` (`status='pending'`) and the 503 message says it was queued. |
| Other agents while Ollama is down | 503 with clear error. They are not auto-queued; `POST /api/queue` can be used manually. |
| Queue draining | Manual re-trigger; no background worker (documented limitation). |
| Malformed model JSON | Ollama `format=json` + extraction/retry; fallback model configured. |

## 6. Test evidence (online run, 2026-11-23)

Demo data: Bookwell Pro (appointment-booking SaaS); prospect **Highline Roofing** (Denver, CO; owner Marcus Reed).

| # | Workflow | Result | Latency |
|---|---|---|---|
| 1 | Business profile | structured profile | 23.1 s |
| 2 | Product ICP | firmographics, personas, triggers | 23.3 s |
| 3 | Research (from stored data) | `data_sources_used: [stored_raw_data, website_excerpt]`, `web_enrichment.attempted=false`, confidence Medium | 16.4 s |
| 4 | Buying signals | 3 signals (strong / moderate / weak), overall **moderate** | 9.7 s |
| 5 | Problem statement | problem, why-now, impact, how-we-help | 6.4 s |
| 6 | Score | **75 / high priority** (icp_fit 20, signal 25, data 15, urgency 20, seniority 15) | 6.1 s |
| 7 | Email | subject + personalised body, CTA `soft_question` | 6.8 s |
| 8 | Reply classification | `objection`, confidence 0.9, key phrases extracted | 5.4 s |

`inference_logs` shows 20 successful calls, all `qwen2.5:7b-instruct`, across agents `business_profile, icp, research, signals, problem_statement, scoring, outreach, reply_classifier`. First call 74.9 s (cold model load); warm calls 3–10 s.

## 7. Offline acceptance test

Procedure: `docs/OFFLINE_TEST.md`. Evidence (screenshots/logs) is in `docs/screenshots/` and `docs/evidence/`.

| Item | Result |
|---|---|
| Network disabled (airplane mode / Wi-Fi off) after model download | ✅ |
| Dashboard still shows "Ollama ready" | ✅ |
| Workflows re-run offline | *(fill: list which, e.g. Score, Email, Reply classification)* |
| New `inference_logs` rows after network off, model = `qwen2.5:7b-instruct` | *(fill: IDs 21–N, timestamps)* |
| Outbound request to a cloud AI host fails | *(fill after running `curl -m 5 https://api.openai.com` → "Could not resolve host")* |

## 8. Licences

Documented in `docs/MODEL_LICENCES.md` (Qwen2.5-7B: Apache-2.0; Phi-3-mini: MIT; FastAPI MIT; Ollama MIT; BeautifulSoup MIT; sentence-transformers Apache-2.0).
Repository code inherited from upstream is AGPL-3.0 / MIT per `LICENSE` and `NOTICE`; LocalHarvey additions are released under the same terms.

## 9. Known limitations (summary — details in `docs/KNOWN_LIMITATIONS.md`)

- Prospects are **seeded sample data** (clearly labelled); live discovery needs internet and is optional.
- Model quality is bounded by a 7B model. Observed example: the generated email contained an unsupported claim ("reduce no-shows by 40%") and an unfilled `[Your Name]` placeholder. A human must review output before sending.
- Buying-signal output echoes the same text in `signal` and `evidence`; evidence extraction is shallow.
- Queue draining is manual; only the research route auto-queues.
- Playwright is optional and not on the default path; email sending is not implemented.
- Dashboard is functional, not a polished CRM.

## 10. Reproduce

```bash
git clone https://github.com/ishitaagarwal657/harvey.git && cd harvey
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
ollama serve &                       # separate terminal
ollama pull qwen2.5:7b-instruct
PROFILE=standard uvicorn backend.main:app --host 0.0.0.0 --port 8000
pytest tests/ -q
```
