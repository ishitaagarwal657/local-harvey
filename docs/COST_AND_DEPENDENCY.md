# Cost & Dependency Statement — LocalHarvey

## Zero paid LLM cost (hard requirement)

| Item | Status |
|------|--------|
| OpenAI API | **Not used** |
| Anthropic / Claude API | **Not used** |
| Google Gemini API | **Not used** |
| Any cloud LLM endpoint | **Not used** |
| Claude Code / Codex subscription | **Not used** |
| Paid agent platforms | **Not used** |
| Token / request billing | **None** |
| Silent cloud fallback | **Forbidden by design** |

All generative AI requests are routed exclusively to a **local Ollama** process at `http://127.0.0.1:11434`.

The Ollama client (`backend/ollama_client.py`) refuses any non-localhost host.  
If Ollama is unreachable the application:

1. Returns a clear HTTP 503 error with setup instructions.
2. Optionally queues the task in the local `task_queue` table.
3. **Never** substitutes a cloud API.

## Local AI stack

| Component | Role | Licence (typical) | Cost after install |
|-----------|------|-------------------|--------------------|
| Ollama | Local inference server | MIT | Free |
| Qwen2.5 (1.5B–32B) | Primary LLM family | Apache-2.0 | Free |
| Phi-3 mini (fallback) | Lightweight model | MIT | Free |
| Sentence-Transformers `all-MiniLM-L6-v2` | Local embeddings | Apache-2.0 / MIT | Free |
| SQLite | Data store | Public domain | Free |
| FastAPI + Uvicorn | Backend | MIT | Free |
| BeautifulSoup / httpx | Optional public-web research | MIT | Free |

## Internet usage

| Activity | Requires internet? | Notes |
|----------|--------------------|-------|
| Initial model download (`ollama pull`) | Yes (once) | After download, models stay local |
| Core AI workflows (profile, ICP, research from stored data, signals, problem, score, email, reply class) | **No** | Offline acceptance test |
| Optional website enrichment (`allow_web=true`) | Yes | Explicit, never required for offline test |
| Fresh prospect discovery from the open web | Yes | Clearly separated from local inference |

## Verification steps for evaluators

1. Start the app and open `/api/status` — confirms Ollama host and recommended model.
2. Run any workflow and inspect `/api/logs/inference` — every row shows a local model name and latency.
3. Disconnect the network after models are pulled and re-run core workflows — they continue to succeed.
4. Inspect `backend/ollama_client.py` — host is hard-locked to localhost; no API keys for external LLM providers exist in the codebase.

## Known non-AI dependencies that may use the network

- First-time `pip install` and `ollama pull`.
- Optional BeautifulSoup page fetch when the operator sets `allow_web=true`.
- No paid prospecting / enrichment APIs are integrated.

**Conclusion:** After installation and model download, LocalHarvey performs all required sales-agent AI workflows with zero token cost and zero external LLM dependency.
