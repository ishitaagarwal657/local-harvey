Append these rows to the "Partial / constrained" table in docs/KNOWN_LIMITATIONS.md and remove the "Original Harvey fork" row (the repo is now a real fork):

| Area | Limitation |
|------|------------|
| Sample data | The 10 prospects, companies and 10 replies are seeded demo data, not live-discovered leads. |
| Output accuracy | Observed: email invented "reduce no-shows by 40%" and left `[Your Name]` unfilled; signal `evidence` repeats the signal text. A human must review all generated outreach. |
| Task queue | Only the research route auto-queues on Ollama failure; others return 503. Queue is drained manually. |
| Legacy code | Upstream `harvey/`, `sellbird/`, `skills/`, `prompts/` remain in the fork and are unused by LocalHarvey (see LEGACY_CODE_NOTICE.md). |
| Cold start | First call after model load took ~75 s on a CPU laptop. |
