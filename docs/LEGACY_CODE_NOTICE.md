# Legacy upstream code in this fork

This repository was forked from the upstream project (now named Sellbird, formerly Harvey). The fork still contains upstream directories — `harvey/`, `sellbird/`, `skills/`, `prompts/`, `Dockerfile`, `CLAUDE.md`, etc. — which are designed to drive outreach through a Claude/ChatGPT subscription.

**The LocalHarvey assignment application does not use any of it.**

- Entry point: `uvicorn backend.main:app`
- Code used: `backend/`, `frontend/`, `sample_data/`, `tests/`, `scripts/`
- Nothing in `backend/` imports from `harvey/` or `sellbird/` (verify: `grep -rnE "from (harvey|sellbird)|import (harvey|sellbird)" backend`)
- No Claude / OpenAI / Gemini credentials are read or required.

Evaluators should treat the upstream directories as inherited history, not part of the submitted system.
