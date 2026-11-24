# Offline Acceptance Test

Proves all 8 AI workflows run with **no internet** and **no external AI service**.

## A. Prerequisites (online, once)

```bash
pip install -r requirements.txt
ollama serve                         # terminal 1
ollama pull qwen2.5:7b-instruct      # or phi3:mini on < 8 GB RAM
PROFILE=standard uvicorn backend.main:app --host 0.0.0.0 --port 8000   # terminal 2
```
Open http://localhost:8000 → **Seed Demo Data**. Look up valid IDs (they do not always start at 1 if you seeded more than once):
`http://localhost:8000/api/companies`, `/api/products`, `/api/prospects`.

## B. Online baseline (completed 2026-11-23)

All 8 workflows succeeded on Bookwell Pro / Highline Roofing — see `TECHNICAL_REPORT.md` §6. Inference Logs rows 1–20, all `qwen2.5:7b-instruct`.

## C. Go offline

1. Turn on airplane mode / disable Wi-Fi and unplug Ethernet.
2. Prove it in the terminal (screenshot this):
   ```bash
   ping -c 2 8.8.8.8                      # should fail
   curl -m 5 https://api.openai.com       # should fail: could not resolve host
   curl -s http://127.0.0.1:11434/api/tags  # should still list models
   ```
3. Refresh the dashboard → **Ollama ready • 3 models • qwen2.5:7b-instruct** still green.

## D. Run the workflows offline

| # | Workflow | UI action | Pass if | ✔ |
|---|---|---|---|---|
| 1 | Business profile | Full Workflow → 1 | structured JSON, `model_used` local | ☐ |
| 2 | Product ICP | → 2 | firmographics, personas, triggers | ☐ |
| 3 | Research (stored data) | → 3 | `data_sources_used` has `stored_raw_data`; `web_enrichment.attempted=false` | ☐ |
| 4 | Buying signals | → 4 | signals + overall strength | ☐ |
| 5 | Problem statement | → 5 | problem + why_now | ☐ |
| 6 | Scoring | → 6 | score 0–100, breakdown, `fallback:false` | ☐ |
| 7 | Email | → 7 | subject + body | ☐ |
| 8 | Reply classification | Reply Classifier → sample → Classify | class + confidence | ☐ |

Then open **Inference Logs**: new rows (ID > 20) must have timestamps from the offline period and model `qwen2.5:7b-instruct`.

## E. Failure-handling check (still offline)

1. Stop Ollama (`pkill ollama` or Ctrl+C the serve terminal).
2. Run **Research Prospect** → expect **503** with "Ollama is not running…" and "Task queued for later local processing". Check `http://localhost:8000/api/queue` → a `pending` row.
3. Run **Score Prospect** → expect deterministic result with `"fallback": true` (no LLM).
4. Restart `ollama serve`, re-run Research → succeeds.
5. Confirm there is no cloud result anywhere.

## F. Evidence checklist (save in `docs/screenshots/`)

- [ ] `01_status_offline.png` — dashboard, Ollama green, airplane-mode icon visible
- [ ] `02_terminal_no_internet.png` — failed ping/curl + working `127.0.0.1:11434`
- [ ] `03_workflow_offline_*.png` — outputs from section D
- [ ] `04_reply_offline.png`
- [ ] `05_inference_logs_offline.png` — rows with offline timestamps
- [ ] `06_ollama_down_503.png` and `07_queue.png`
- [ ] `pytest_output.txt` — output of `pytest tests/ -q`

## G. Results (fill in)

| Item | Value |
|---|---|
| Date / time offline test | |
| Machine (RAM/CPU/GPU) | |
| Offline log row IDs | |
| Latencies offline | |
| Result | PASS / FAIL |

## What must not happen
Any request to a cloud LLM host; silent cloud fallback; hard-coded output passed off as model output.
