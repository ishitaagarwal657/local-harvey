# Model & Major Dependency Licences

LocalHarvey only recommends and documents models with **permissive open-source licences**
(Apache-2.0 or MIT). Do not assume every open-weight model is open source.

## Primary LLMs (via Ollama) — used by default

| Model | Ollama tag | Licence | Notes |
|-------|------------|---------|-------|
| Qwen2.5 Instruct 7B / 14B / 32B / 1.5B | `qwen2.5:7b-instruct` etc. | **Apache-2.0** | Default family |
| Phi-3 Mini | `phi3:mini` | **MIT** | Lightweight fallback |

**Not recommended / not pulled by setup.sh**

| Model | Reason |
|-------|--------|
| Some Qwen 3B variants | May be under Qwen Research License (restrictive) — avoid |
| Llama 3.x | Llama Community License (not pure Apache/MIT) — not default |
| Gemma | Google licence terms — not default |

Hardware recommendation (`backend/hardware.py`) only returns the safe models above.

## Embeddings

| Model | Package | Licence |
|-------|---------|---------|
| `all-MiniLM-L6-v2` | sentence-transformers | **Apache-2.0** |

(Config previously mislabelled this as MIT; corrected to Apache-2.0.)

## Core application libraries

| Library | Licence |
|---------|---------|
| FastAPI | MIT |
| Uvicorn | BSD-3-Clause |
| Pydantic | MIT |
| aiosqlite | MIT |
| httpx | BSD-3-Clause |
| BeautifulSoup4 | MIT |
| psutil | BSD-3-Clause |
| sentence-transformers | Apache-2.0 |
| Ollama | MIT |

## Explicitly excluded

- Any model whose licence prohibits commercial use or requires payment for inference.
- Closed-weight or proprietary hosted endpoints.
- Paid enrichment / prospecting APIs.

If a model licence changes upstream, replace it with another Apache-2.0 / MIT model before submission.
