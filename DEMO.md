# Screen Recording Demo Script (5–10 min)

Use this exact flow for the assignment video.

## 0. Preparation (before recording)

```bash
# Terminal 1
ollama serve

# Terminal 2
cd local-harvey
source .venv/bin/activate
ollama pull qwen2.5:7b-instruct   # or 3b if low RAM
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## 1. Show System Status (30 s)

- Dashboard loads
- Ollama status = Online
- Hardware numbers visible
- Recommended model shown
- Point out “Zero paid LLM • Ollama only”

## 2. Seed Demo Data (20 s)

- Click **Seed Demo Data**
- Show the success alert with company_id / product_id / 3 prospects

## 3. Company & Products (30 s)

- Switch to Company view
- Show the seeded Bookwell company and Bookwell Pro product

## 4. Full Workflow (4–5 min) — this is the core

Go to **Full Workflow** view.

Enter the IDs from the seed step.

Run each button in order and briefly show the JSON output:

1. **Business Profile** → structured company summary
2. **Generate ICP** → firmographics, personas, buying triggers
3. **Research Prospect** (pick one of the 3) → research summary from stored data
4. **Buying Signals** → classified signals + overall strength
5. **Problem Statement** → problem narrative
6. **Score Prospect** → numeric score + breakdown + priority
7. **Generate Email** → subject + personalised body

While one of the longer calls is running, mention:  
“All of this is happening on my machine via Ollama. No external LLM API is being called.”

## 5. Reply Classification (1 min)

- Switch to Reply Classifier
- Paste one of the sample replies from `docs/OFFLINE_TEST.md`
- Show classification, confidence and suggested next action

## 6. Inference Logs (30 s)

- Open Inference Logs
- Show rows with local model name, latency, success = true

## 7. Offline Proof (1–1.5 min)

**Important for the assignment**

- Say: “Now I will disconnect the internet.”
- Turn off Wi-Fi / unplug / enable airplane mode (show the network icon)
- Refresh the dashboard — Ollama still online (local)
- Re-run **Score Prospect** or **Generate Email** on another prospect
- Show it still works
- Open Inference Logs again — still only local model calls

## 8. Closing (20 s)

- Return to Dashboard
- Recap: fully local, multi-product, offline-capable, zero paid LLM cost
- Point to the GitHub repo and the docs folder

---

### Tips for a clean recording

- Use a large font / zoom the browser a little
- Keep the terminal with `ollama serve` visible in a second window if possible
- Speak clearly when you disable the network
- Total length target: 6–8 minutes
