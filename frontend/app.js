const API = "";

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || JSON.stringify(err));
  }
  return res.json();
}

// ---------- Status ----------
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("statusText");
    if (s.ollama_available) {
      dot.className = "dot ok";
      text.textContent = `Ollama ready • ${s.models.length} models • ${s.recommendation.recommended}`;
    } else {
      dot.className = "dot err";
      text.textContent = "Ollama offline — local AI unavailable";
    }
    window.__status = s;
  } catch (e) {
    document.getElementById("statusDot").className = "dot err";
    document.getElementById("statusText").textContent = "API unreachable";
  }
}

// ---------- Views ----------
const views = {
  dashboard: renderDashboard,
  company: renderCompany,
  prospects: renderProspects,
  workflow: renderWorkflow,
  replies: renderReplies,
  logs: renderLogs,
};

function switchView(name) {
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.view === name));
  views[name]();
}

document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

document.getElementById("seedBtn").addEventListener("click", async () => {
  try {
    const r = await api("/api/demo/seed", { method: "POST" });
    alert(`Demo data seeded!\nCompany ID: ${r.company_id}\nProduct ID: ${r.product_id}\nProspects: ${r.prospects}`);
    switchView("dashboard");
  } catch (e) {
    alert("Seed failed: " + e.message);
  }
});

// ---------- Dashboard ----------
async function renderDashboard() {
  const el = document.getElementById("content");
  el.innerHTML = `<h2>Dashboard</h2><p class="subtitle">System health & quick overview</p><div class="card"><div class="spinner"></div> Loading…</div>`;

  const [status, companies, products, prospects] = await Promise.all([
    api("/api/status"),
    api("/api/companies"),
    api("/api/products"),
    api("/api/prospects"),
  ]);

  el.innerHTML = `
    <h2>Dashboard</h2>
    <p class="subtitle">Fully local • Zero paid LLM cost</p>

    <div class="grid grid-3">
      <div class="card metric">
        <div class="value">${status.ollama_available ? "Online" : "Offline"}</div>
        <div class="label">Ollama Status</div>
      </div>
      <div class="card metric">
        <div class="value">${status.hardware.ram_total_gb || "?"} GB</div>
        <div class="label">System RAM</div>
      </div>
      <div class="card metric">
        <div class="value">${status.recommendation.tier || "—"}</div>
        <div class="label">Model Tier</div>
      </div>
    </div>

    <div class="card">
      <h3>Hardware & Model Recommendation</h3>
      <p><strong>Recommended:</strong> <code>${status.recommendation.recommended}</code></p>
      <p><strong>Fallback:</strong> <code>${status.recommendation.fallback}</code></p>
      <p class="subtitle" style="margin:0.5rem 0 0">${status.recommendation.reason}</p>
      <p style="margin-top:0.75rem;font-size:0.85rem;color:var(--muted)">
        CPU: ${status.hardware.cpu_logical} logical • 
        GPU: ${status.hardware.has_gpu ? status.hardware.gpus.map(g=>g.name).join(", ") : "None detected"} •
        Available models: ${status.models.join(", ") || "none"}
      </p>
    </div>

    <div class="grid grid-3">
      <div class="card metric"><div class="value">${companies.length}</div><div class="label">Companies</div></div>
      <div class="card metric"><div class="value">${products.length}</div><div class="label">Products</div></div>
      <div class="card metric"><div class="value">${prospects.length}</div><div class="label">Prospects</div></div>
    </div>

    ${!status.ollama_available ? `
      <div class="alert error">
        <strong>Ollama is not running.</strong><br>
        Start it with <code>ollama serve</code> then pull a model:<br>
        <code>ollama pull qwen2.5:7b-instruct</code><br>
        No cloud fallback is available by design.
      </div>
    ` : ""}
  `;
}

// ---------- Company ----------
async function renderCompany() {
  const el = document.getElementById("content");
  el.innerHTML = `<h2>Company & Products</h2><p class="subtitle">Configure the business you are selling for</p>
    <div class="grid grid-2">
      <div class="card">
        <h3>Add Company</h3>
        <label>Name</label><input id="cName" placeholder="Bookwell" />
        <label>Website</label><input id="cWeb" placeholder="https://..." />
        <label>Industry</label><input id="cInd" placeholder="SaaS" />
        <label>Description</label><textarea id="cDesc"></textarea>
        <button class="btn" id="addCompany">Create Company</button>
      </div>
      <div class="card">
        <h3>Add Product</h3>
        <label>Company ID</label><input id="pCid" type="number" />
        <label>Product Name</label><input id="pName" />
        <label>Description</label><textarea id="pDesc"></textarea>
        <label>Value Props (comma separated)</label><input id="pProps" />
        <label>Pricing Model</label><input id="pPrice" />
        <button class="btn" id="addProduct">Create Product</button>
      </div>
    </div>
    <div class="card" id="companyList"><div class="spinner"></div></div>
  `;

  document.getElementById("addCompany").onclick = async () => {
    try {
      const r = await api("/api/companies", {
        method: "POST",
        body: JSON.stringify({
          name: document.getElementById("cName").value,
          website: document.getElementById("cWeb").value,
          industry: document.getElementById("cInd").value,
          description: document.getElementById("cDesc").value,
        }),
      });
      alert("Company created: ID " + r.id);
      renderCompany();
    } catch (e) { alert(e.message); }
  };

  document.getElementById("addProduct").onclick = async () => {
    try {
      const props = document.getElementById("pProps").value.split(",").map(s => s.trim()).filter(Boolean);
      const r = await api("/api/products", {
        method: "POST",
        body: JSON.stringify({
          company_id: +document.getElementById("pCid").value,
          name: document.getElementById("pName").value,
          description: document.getElementById("pDesc").value,
          value_props: props,
          pricing_model: document.getElementById("pPrice").value,
        }),
      });
      alert("Product created: ID " + r.id);
      renderCompany();
    } catch (e) { alert(e.message); }
  };

  const [companies, products] = await Promise.all([api("/api/companies"), api("/api/products")]);
  document.getElementById("companyList").innerHTML = `
    <h3>Existing Companies & Products</h3>
    <table class="table">
      <thead><tr><th>ID</th><th>Company</th><th>Industry</th><th>Products</th></tr></thead>
      <tbody>
        ${companies.map(c => {
          const prods = products.filter(p => p.company_id === c.id);
          return `<tr>
            <td>${c.id}</td>
            <td><strong>${c.name}</strong><br><span style="font-size:0.8rem;color:var(--muted)">${c.website||""}</span></td>
            <td>${c.industry||"—"}</td>
            <td>${prods.map(p => `#${p.id} ${p.name}`).join("<br>") || "—"}</td>
          </tr>`;
        }).join("") || "<tr><td colspan=4>No companies yet. Seed demo data or create one.</td></tr>"}
      </tbody>
    </table>
  `;
}

// ---------- Prospects ----------
async function renderProspects() {
  const el = document.getElementById("content");
  el.innerHTML = `<h2>Prospects</h2><p class="subtitle">Loaded or researched prospects</p>
    <div class="card">
      <h3>Add Prospect</h3>
      <div class="grid grid-2">
        <div>
          <label>Product ID</label><input id="prPid" type="number" />
          <label>Company Name</label><input id="prName" />
          <label>Website</label><input id="prWeb" />
          <label>Location</label><input id="prLoc" />
        </div>
        <div>
          <label>Contact Name</label><input id="prContact" />
          <label>Title</label><input id="prTitle" />
          <label>Email</label><input id="prEmail" />
          <label>Raw Notes / Data</label><textarea id="prRaw"></textarea>
        </div>
      </div>
      <button class="btn" id="addProspect">Add Prospect</button>
    </div>
    <div class="card" id="prospectList"><div class="spinner"></div></div>
  `;

  document.getElementById("addProspect").onclick = async () => {
    try {
      const r = await api("/api/prospects", {
        method: "POST",
        body: JSON.stringify({
          product_id: +document.getElementById("prPid").value || null,
          company_name: document.getElementById("prName").value,
          website: document.getElementById("prWeb").value,
          contact_name: document.getElementById("prContact").value,
          contact_title: document.getElementById("prTitle").value,
          contact_email: document.getElementById("prEmail").value,
          location: document.getElementById("prLoc").value,
          raw_data: document.getElementById("prRaw").value,
        }),
      });
      alert("Prospect added: ID " + r.id);
      renderProspects();
    } catch (e) { alert(e.message); }
  };

  const prospects = await api("/api/prospects");
  document.getElementById("prospectList").innerHTML = `
    <h3>All Prospects (${prospects.length})</h3>
    <table class="table">
      <thead><tr><th>ID</th><th>Company</th><th>Contact</th><th>Score</th><th>Status</th></tr></thead>
      <tbody>
        ${prospects.map(p => `
          <tr>
            <td>${p.id}</td>
            <td><strong>${p.company_name}</strong><br><span style="font-size:0.8rem;color:var(--muted)">${p.location||""}</span></td>
            <td>${p.contact_name||"—"}<br><span style="font-size:0.8rem;color:var(--muted)">${p.contact_title||""}</span></td>
            <td>${p.score ? p.score.toFixed(0) : "—"}</td>
            <td><span class="badge ${p.status}">${p.status}</span></td>
          </tr>
        `).join("") || "<tr><td colspan=5>No prospects. Seed demo data.</td></tr>"}
      </tbody>
    </table>
  `;
}

// ---------- Full Workflow ----------
async function renderWorkflow() {
  const el = document.getElementById("content");
  el.innerHTML = `
    <h2>Full Sales Workflow</h2>
    <p class="subtitle">Run the complete local AI pipeline on a company / product / prospect</p>

    <div class="card">
      <div class="grid grid-3">
        <div>
          <label>Company ID</label>
          <input id="wfCompany" type="number" placeholder="1" />
        </div>
        <div>
          <label>Product ID</label>
          <input id="wfProduct" type="number" placeholder="1" />
        </div>
        <div>
          <label>Prospect ID</label>
          <input id="wfProspect" type="number" placeholder="1" />
        </div>
      </div>
      <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.5rem">
        <button class="btn" data-step="profile">1. Business Profile</button>
        <button class="btn" data-step="icp">2. Generate ICP</button>
        <button class="btn" data-step="research">3. Research Prospect</button>
        <button class="btn" data-step="signals">4. Buying Signals</button>
        <button class="btn" data-step="problem">5. Problem Statement</button>
        <button class="btn" data-step="score">6. Score Prospect</button>
        <button class="btn" data-step="outreach">7. Generate Email</button>
      </div>
    </div>

    <div class="card">
      <h3>Output</h3>
      <div id="wfOutput" class="pre">Select a step and run…</div>
    </div>
  `;

  const out = document.getElementById("wfOutput");

  document.querySelectorAll("[data-step]").forEach(btn => {
    btn.onclick = async () => {
      const step = btn.dataset.step;
      const companyId = document.getElementById("wfCompany").value;
      const productId = document.getElementById("wfProduct").value;
      const prospectId = document.getElementById("wfProspect").value;

      out.innerHTML = `<span class="spinner"></span> Running ${step}… (local Ollama inference)`;
      btn.disabled = true;

      try {
        let result;
        if (step === "profile") {
          result = await api(`/api/workflows/business-profile/${companyId}`, { method: "POST" });
        } else if (step === "icp") {
          result = await api(`/api/workflows/icp/${productId}`, { method: "POST" });
        } else if (step === "research") {
          result = await api(`/api/workflows/research/${prospectId}`, { method: "POST" });
        } else if (step === "signals") {
          result = await api(`/api/workflows/signals/${prospectId}`, { method: "POST" });
        } else if (step === "problem") {
          result = await api(`/api/workflows/problem/${prospectId}`, { method: "POST" });
        } else if (step === "score") {
          result = await api(`/api/workflows/score/${prospectId}`, { method: "POST" });
        } else if (step === "outreach") {
          result = await api(`/api/workflows/outreach/${prospectId}?sequence_step=1`, { method: "POST" });
        }
        out.textContent = JSON.stringify(result, null, 2);
      } catch (e) {
        out.innerHTML = `<div class="alert error">${e.message}</div>`;
      } finally {
        btn.disabled = false;
      }
    };
  });
}

// ---------- Reply Classifier ----------
async function renderReplies() {
  const el = document.getElementById("content");
  el.innerHTML = `
    <h2>Reply Classification</h2>
    <p class="subtitle">Classify inbound replies using local model (works offline)</p>
    <div class="card">
      <label>Original outreach (optional)</label>
      <textarea id="origEmail" placeholder="Paste the email you sent…"></textarea>
      <label>Reply text</label>
      <textarea id="replyText" placeholder="Paste the prospect's reply…"></textarea>
      <label>Prospect ID (optional, for logging)</label>
      <input id="replyPid" type="number" />
      <button class="btn" id="classifyBtn">Classify Reply</button>
    </div>
    <div class="card">
      <h3>Sample replies (click to load — offline demo)</h3>
      <div id="sampleReplies" class="sample-list"><div class="spinner"></div></div>
    </div>
    <div class="card">
      <h3>Result</h3>
      <div id="replyOut" class="pre">Waiting…</div>
    </div>
  `;

  // Load sample replies for offline demo
  try {
    const samples = await api("/api/demo/sample-replies");
    const box = document.getElementById("sampleReplies");
    if (!samples.length) {
      box.innerHTML = "<p class='muted'>No sample replies. Click Seed Demo Data first.</p>";
    } else {
      box.innerHTML = samples.map((s, i) => `
        <button class="btn secondary sample-btn" data-idx="${i}">
          ${s.label || "Sample " + (i+1)}
        </button>
      `).join(" ");
      box.querySelectorAll(".sample-btn").forEach(btn => {
        btn.onclick = () => {
          const s = samples[+btn.dataset.idx];
          document.getElementById("replyText").value = s.reply_text || "";
          document.getElementById("origEmail").value = s.original_email_snippet || "";
        };
      });
    }
  } catch (e) {
    document.getElementById("sampleReplies").innerHTML = `<p class="muted">${e.message}</p>`;
  }

  document.getElementById("classifyBtn").onclick = async () => {
    const out = document.getElementById("replyOut");
    out.innerHTML = `<span class="spinner"></span> Classifying with local model…`;
    try {
      const r = await api("/api/workflows/classify-reply", {
        method: "POST",
        body: JSON.stringify({
          reply_text: document.getElementById("replyText").value,
          original_email: document.getElementById("origEmail").value,
          prospect_id: +document.getElementById("replyPid").value || null,
        }),
      });
      out.textContent = JSON.stringify(r, null, 2);
    } catch (e) {
      out.innerHTML = `<div class="alert error">${e.message}</div>`;
    }
  };
}

// ---------- Logs ----------
async function renderLogs() {
  const el = document.getElementById("content");
  el.innerHTML = `<h2>Inference Logs</h2><p class="subtitle">Every local model call is recorded</p>
    <div class="card" id="logList"><div class="spinner"></div></div>`;

  const logs = await api("/api/logs/inference?limit=40");
  document.getElementById("logList").innerHTML = `
    <table class="table">
      <thead><tr><th>ID</th><th>Agent</th><th>Model</th><th>Latency</th><th>Success</th><th>Time</th></tr></thead>
      <tbody>
        ${logs.map(l => `
          <tr>
            <td>${l.id}</td>
            <td>${l.agent}</td>
            <td><code>${l.model}</code></td>
            <td>${l.latency_ms} ms</td>
            <td>${l.success ? "✅" : "❌ " + (l.error || "")}</td>
            <td style="font-size:0.8rem">${l.created_at}</td>
          </tr>
        `).join("") || "<tr><td colspan=6>No inference logs yet. Run a workflow.</td></tr>"}
      </tbody>
    </table>
  `;
}

// Init
refreshStatus();
setInterval(refreshStatus, 15000);
switchView("dashboard");
