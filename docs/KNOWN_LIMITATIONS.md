# Known Limitations — LocalHarvey

Be transparent with evaluators. The following are intentional or residual limitations.

## Fully implemented

- Local-only Ollama inference with localhost hard-lock
- Hardware / profile based model recommendation (safe Apache-2.0 / MIT models only)
- 8 sales-agent workflows (profile, ICP, research, signals, problem, score, outreach, reply class)
- Deterministic rule-based scorer when Ollama is down (no cloud fallback)
- Task queue for deferred local processing
- Local embeddings (sentence-transformers) with hash fallback
- Optional BeautifulSoup web enrichment (`allow_web=true`) — never required offline
- Idempotent demo seed + prospect import API
- Inference logging
- Offline sample data (10 prospects, 10 sample replies)

## Partial / constrained

| Area | Limitation |
|------|------------|
| Web research | BeautifulSoup basic page text only. Playwright is optional dependency; not wired as default path. |
| Embeddings | Used for ICP-fit similarity inside scoring. Not a full vector search index. |
| Task queue | Tasks are stored; automatic background worker to drain the queue is minimal (manual re-trigger). |
| Multi-product UI | Backend supports multiple products per company; dashboard is functional but not a polished CRM. |
| JSON reliability | Uses Ollama `format: json` + extraction retries. Very small models may still occasionally fail validation. |
| Original Harvey fork | This repository is a clean local re-implementation of the sales-agent idea. If the evaluator requires git fork history from `ethanplusai/harvey`, create the fork and merge this tree on top before submission. |

## Not included (by design / assignment constraints)

- Any paid LLM API or cloud inference
- Silent cloud fallback
- Paid prospecting / enrichment APIs
- Production multi-tenant auth

## How to prove offline operation

See `docs/OFFLINE_TEST.md`. After `ollama pull`, disconnect the network and run the eight workflows. Inference logs must show only local model names.
