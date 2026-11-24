"""
LocalHarvey — Fully Local Multi-Product AI Sales Agent
FastAPI application entry point.
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import aiosqlite
import json
from pathlib import Path
from typing import Optional, List

from .config import settings, BASE_DIR, DATA_DIR
from .database import init_db, get_db, DB_PATH
from .hardware import get_system_info, recommend_model, resolve_model
from .ollama_client import llm, LocalLLMError
from .agents import (
    generate_business_profile,
    generate_icp,
    research_prospect,
    classify_buying_signals,
    generate_problem_statement,
    generate_outreach_email,
    score_prospect,
    classify_reply,
)
from .schemas import (
    CompanyCreate, ProductCreate, ProspectCreate,
    ReplyClassifyRequest, StatusResponse
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print(f"✅ LocalHarvey started — DB at {DB_PATH}")
    yield
    print("LocalHarvey shutdown")

app = FastAPI(
    title="LocalHarvey",
    description="Fully local multi-product AI Sales Agent — zero paid LLM cost",
    version=settings.app_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Health & System ----------

@app.get("/api/status", response_model=StatusResponse)
async def status():
    available = await llm.is_available()
    models = []
    if available:
        try:
            models = await llm.list_models()
        except Exception:
            models = []
    info = get_system_info()
    rec = resolve_model(settings, info)
    msg = (
        f"Ready — using {rec['recommended']} ({rec.get('tier')})"
        if available
        else "Ollama not running — start with `ollama serve` then `ollama pull qwen2.5:7b-instruct`. Deterministic fallbacks available for scoring."
    )
    return StatusResponse(
        status="ok" if available else "degraded",
        ollama_available=available,
        models=models,
        hardware=info,
        recommendation=rec,
        message=msg
    )

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "LocalHarvey"}

# ---------- Companies & Products ----------

@app.post("/api/companies")
async def create_company(payload: CompanyCreate):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO companies (name, website, description, industry) VALUES (?, ?, ?, ?)",
            (payload.name, payload.website, payload.description, payload.industry)
        )
        await db.commit()
        return {"id": cursor.lastrowid, **payload.model_dump()}

@app.get("/api/companies")
async def list_companies():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall("SELECT * FROM companies ORDER BY id DESC")
        return [dict(r) for r in rows]

@app.post("/api/products")
async def create_product(payload: ProductCreate):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO products (company_id, name, description, value_props, pricing_model, target_segments)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                payload.company_id,
                payload.name,
                payload.description,
                json.dumps(payload.value_props or []),
                payload.pricing_model,
                json.dumps(payload.target_segments or [])
            )
        )
        await db.commit()
        return {"id": cursor.lastrowid, **payload.model_dump()}

@app.get("/api/products")
async def list_products(company_id: Optional[int] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if company_id:
            rows = await db.execute_fetchall(
                "SELECT * FROM products WHERE company_id = ?", (company_id,)
            )
        else:
            rows = await db.execute_fetchall("SELECT * FROM products ORDER BY id DESC")
        results = []
        for r in rows:
            d = dict(r)
            d["value_props"] = json.loads(d["value_props"] or "[]")
            d["target_segments"] = json.loads(d["target_segments"] or "[]")
            results.append(d)
        return results

# ---------- Core AI Workflows ----------

@app.post("/api/workflows/business-profile/{company_id}")
async def workflow_business_profile(company_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        company = await db.execute_fetchall("SELECT * FROM companies WHERE id = ?", (company_id,))
        if not company:
            raise HTTPException(404, "Company not found")
        company = dict(company[0])
        products = await db.execute_fetchall(
            "SELECT * FROM products WHERE company_id = ?", (company_id,)
        )
        products = [dict(p) for p in products]
        for p in products:
            p["value_props"] = json.loads(p["value_props"] or "[]")

    try:
        result = await generate_business_profile(company, products)
    except LocalLLMError as e:
        raise HTTPException(503, str(e))

    # Persist
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO business_profiles (company_id, profile_json, model_used) VALUES (?, ?, ?)",
            (company_id, json.dumps(result["profile"]), result["model_used"])
        )
        await db.commit()

    return result

@app.post("/api/workflows/icp/{product_id}")
async def workflow_icp(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        product = await db.execute_fetchall("SELECT * FROM products WHERE id = ?", (product_id,))
        if not product:
            raise HTTPException(404, "Product not found")
        product = dict(product[0])
        product["value_props"] = json.loads(product["value_props"] or "[]")

        # Get latest business profile for the company
        profiles = await db.execute_fetchall(
            "SELECT profile_json FROM business_profiles WHERE company_id = ? ORDER BY id DESC LIMIT 1",
            (product["company_id"],)
        )
        business_profile = json.loads(profiles[0]["profile_json"]) if profiles else {}

    try:
        result = await generate_icp(product, business_profile)
    except LocalLLMError as e:
        raise HTTPException(503, str(e))

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO icps (product_id, icp_json, model_used) VALUES (?, ?, ?)",
            (product_id, json.dumps(result["icp"]), result["model_used"])
        )
        await db.commit()

    return result

@app.post("/api/prospects")
async def create_prospect(payload: ProspectCreate):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO prospects
               (product_id, company_name, website, contact_name, contact_title, contact_email, location, raw_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payload.product_id, payload.company_name, payload.website,
                payload.contact_name, payload.contact_title, payload.contact_email,
                payload.location, payload.raw_data
            )
        )
        await db.commit()
        return {"id": cursor.lastrowid, **payload.model_dump()}

@app.get("/api/prospects")
async def list_prospects(product_id: Optional[int] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if product_id:
            rows = await db.execute_fetchall(
                "SELECT * FROM prospects WHERE product_id = ? ORDER BY score DESC, id DESC",
                (product_id,)
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM prospects ORDER BY score DESC, id DESC"
            )
        return [dict(r) for r in rows]

@app.post("/api/workflows/research/{prospect_id}")
async def workflow_research(prospect_id: int, allow_web: bool = False):
    """
    Research a prospect from stored data (offline-safe).
    Set allow_web=true only when you explicitly want optional public-page enrichment.
    Core offline acceptance test must use allow_web=false (default).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall("SELECT * FROM prospects WHERE id = ?", (prospect_id,))
        if not rows:
            raise HTTPException(404, "Prospect not found")
        prospect = dict(rows[0])
        product = None
        if prospect["product_id"]:
            prows = await db.execute_fetchall("SELECT * FROM products WHERE id = ?", (prospect["product_id"],))
            if prows:
                product = dict(prows[0])
                product["value_props"] = json.loads(product["value_props"] or "[]")

    try:
        result = await research_prospect(prospect, product, allow_web=allow_web)
    except LocalLLMError as e:
        # Queue for later instead of cloud fallback
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO task_queue (task_type, payload_json, status) VALUES (?, ?, 'pending')",
                ("research", json.dumps({"prospect_id": prospect_id, "allow_web": allow_web}))
            )
            await db.commit()
        raise HTTPException(503, str(e) + " | Task queued for later local processing.")

    # Update prospect
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE prospects SET research_notes = ?, status = 'researched', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(result["research"]), prospect_id)
        )
        await db.commit()

    return result

@app.post("/api/workflows/signals/{prospect_id}")
async def workflow_signals(prospect_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        prosp = await db.execute_fetchall("SELECT * FROM prospects WHERE id = ?", (prospect_id,))
        if not prosp:
            raise HTTPException(404, "Prospect not found")
        prospect = dict(prosp[0])
        research = json.loads(prospect["research_notes"] or "{}")

        icp = {}
        if prospect["product_id"]:
            icps = await db.execute_fetchall(
                "SELECT icp_json FROM icps WHERE product_id = ? ORDER BY id DESC LIMIT 1",
                (prospect["product_id"],)
            )
            if icps:
                icp = json.loads(icps[0]["icp_json"])

    try:
        result = await classify_buying_signals(prospect, research, icp)
    except LocalLLMError as e:
        raise HTTPException(503, str(e))

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE prospects SET buying_signals = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(result["signals"]), prospect_id)
        )
        await db.commit()

    return result

@app.post("/api/workflows/problem/{prospect_id}")
async def workflow_problem(prospect_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        prosp = await db.execute_fetchall("SELECT * FROM prospects WHERE id = ?", (prospect_id,))
        if not prosp:
            raise HTTPException(404, "Prospect not found")
        prospect = dict(prosp[0])
        research = json.loads(prospect["research_notes"] or "{}")
        signals = json.loads(prospect["buying_signals"] or "{}")

        product = {"name": "Unknown", "description": ""}
        if prospect["product_id"]:
            prows = await db.execute_fetchall("SELECT * FROM products WHERE id = ?", (prospect["product_id"],))
            if prows:
                product = dict(prows[0])

    try:
        result = await generate_problem_statement(prospect, research, signals, product)
    except LocalLLMError as e:
        raise HTTPException(503, str(e))

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE prospects SET problem_statement = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(result["problem"]), prospect_id)
        )
        await db.commit()

    return result

@app.post("/api/workflows/score/{prospect_id}")
async def workflow_score(prospect_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        prosp = await db.execute_fetchall("SELECT * FROM prospects WHERE id = ?", (prospect_id,))
        if not prosp:
            raise HTTPException(404, "Prospect not found")
        prospect = dict(prosp[0])
        research = json.loads(prospect["research_notes"] or "{}")
        signals = json.loads(prospect["buying_signals"] or "{}")

        icp = {}
        if prospect["product_id"]:
            icps = await db.execute_fetchall(
                "SELECT icp_json FROM icps WHERE product_id = ? ORDER BY id DESC LIMIT 1",
                (prospect["product_id"],)
            )
            if icps:
                icp = json.loads(icps[0]["icp_json"])

    try:
        result = await score_prospect(prospect, research, signals, icp)
    except LocalLLMError as e:
        raise HTTPException(503, str(e))

    scoring = result["scoring"]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE prospects SET score = ?, score_reason = ?, status = 'scored', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (scoring.get("score", 0), scoring.get("reason", ""), prospect_id)
        )
        await db.commit()

    return result

@app.post("/api/workflows/outreach/{prospect_id}")
async def workflow_outreach(prospect_id: int, sequence_step: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        prosp = await db.execute_fetchall("SELECT * FROM prospects WHERE id = ?", (prospect_id,))
        if not prosp:
            raise HTTPException(404, "Prospect not found")
        prospect = dict(prosp[0])
        problem = json.loads(prospect["problem_statement"] or "{}")

        product = {"name": "Our Product", "value_props": []}
        icp = None
        if prospect["product_id"]:
            prows = await db.execute_fetchall("SELECT * FROM products WHERE id = ?", (prospect["product_id"],))
            if prows:
                product = dict(prows[0])
                product["value_props"] = json.loads(product["value_props"] or "[]")
            icps = await db.execute_fetchall(
                "SELECT icp_json FROM icps WHERE product_id = ? ORDER BY id DESC LIMIT 1",
                (prospect["product_id"],)
            )
            if icps:
                icp = json.loads(icps[0]["icp_json"])

    try:
        result = await generate_outreach_email(prospect, problem, product, icp=icp, sequence_step=sequence_step)
    except LocalLLMError as e:
        raise HTTPException(503, str(e))

    email = result["email"]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO outreach_emails (prospect_id, subject, body, sequence_step, model_used) VALUES (?, ?, ?, ?, ?)",
            (prospect_id, email.get("subject"), email.get("body"), sequence_step, result["model_used"])
        )
        await db.execute(
            "UPDATE prospects SET status = 'outreach', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (prospect_id,)
        )
        await db.commit()

    return result

@app.post("/api/workflows/classify-reply")
async def workflow_classify_reply(payload: ReplyClassifyRequest):
    try:
        result = await classify_reply(payload.reply_text, payload.original_email or "")
    except LocalLLMError as e:
        raise HTTPException(503, str(e))

    if payload.prospect_id:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO conversations (prospect_id, direction, content, classification, confidence, model_used)
                   VALUES (?, 'inbound', ?, ?, ?, ?)""",
                (
                    payload.prospect_id,
                    payload.reply_text,
                    result["classification"].get("classification"),
                    result["classification"].get("confidence"),
                    result["model_used"]
                )
            )
            await db.commit()

    return result

@app.get("/api/logs/inference")
async def inference_logs(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            "SELECT * FROM inference_logs ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in rows]


# ---------- Prospect import (previously downloaded data) ----------

@app.post("/api/prospects/import")
async def import_prospects(payload: dict):
    """
    Import prospects from a JSON list (previously downloaded / offline data).
    Body: { "product_id": 1, "prospects": [ {company_name, website, contact_name, ...}, ... ] }
    """
    product_id = payload.get("product_id")
    items = payload.get("prospects") or []
    if not items:
        raise HTTPException(400, "prospects list is required")
    inserted = 0
    async with aiosqlite.connect(DB_PATH) as db:
        for s in items:
            if not s.get("company_name"):
                continue
            await db.execute(
                """INSERT INTO prospects
                   (product_id, company_name, website, contact_name, contact_title, contact_email, location, raw_data, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (
                    product_id or s.get("product_id"),
                    s["company_name"],
                    s.get("website"),
                    s.get("contact_name"),
                    s.get("contact_title"),
                    s.get("contact_email"),
                    s.get("location"),
                    s.get("raw_data") or s.get("notes") or "",
                )
            )
            inserted += 1
        await db.commit()
    return {"imported": inserted, "message": "Prospects loaded from offline data"}


# ---------- Seed sample data for offline demo ----------

@app.post("/api/demo/seed")
async def seed_demo_data(reset: bool = True):
    """
    Load sample companies, products, prospects and conversations
    so the offline acceptance test can run immediately without internet.
    Prefers sample_data/*.json when present.
    By default resets previous demo rows so repeated clicks are idempotent.
    """
    from .config import SAMPLE_DIR

    def _load_json(name, default):
        p = SAMPLE_DIR / name
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return default
        return default

    companies = _load_json("companies.json", [{
        "name": "Bookwell",
        "website": "https://bookwell.example",
        "description": "Online booking and scheduling platform for local service businesses.",
        "industry": "SaaS / Vertical Software"
    }])
    products = _load_json("products.json", [])
    prospects = _load_json("prospects.json", [])
    replies = _load_json("sample_replies.json", [])

    created = {"companies": [], "products": [], "prospects": 0, "sample_replies": len(replies)}

    async with aiosqlite.connect(DB_PATH) as db:
        if reset:
            # Idempotent: clear prior demo data (all current rows for simplicity in demo mode)
            await db.execute("DELETE FROM outreach_emails")
            await db.execute("DELETE FROM conversations")
            await db.execute("DELETE FROM prospects")
            await db.execute("DELETE FROM icps")
            await db.execute("DELETE FROM business_profiles")
            await db.execute("DELETE FROM products")
            await db.execute("DELETE FROM companies")
            await db.commit()

        name_to_company_id = {}
        for c in companies:
            cur = await db.execute(
                "INSERT INTO companies (name, website, description, industry) VALUES (?, ?, ?, ?)",
                (c["name"], c.get("website"), c.get("description"), c.get("industry"))
            )
            cid = cur.lastrowid
            name_to_company_id[c["name"]] = cid
            created["companies"].append({"id": cid, "name": c["name"]})

        name_to_product_id = {}
        for p in products:
            cname = p.get("company_name")
            cid = name_to_company_id.get(cname)
            if not cid and name_to_company_id:
                cid = list(name_to_company_id.values())[0]
            if not cid:
                continue
            cur = await db.execute(
                """INSERT INTO products (company_id, name, description, value_props, pricing_model, target_segments)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    cid,
                    p["name"],
                    p.get("description"),
                    json.dumps(p.get("value_props") or []),
                    p.get("pricing_model"),
                    json.dumps(p.get("target_segments") or []),
                )
            )
            pid = cur.lastrowid
            name_to_product_id[p["name"]] = pid
            created["products"].append({"id": pid, "name": p["name"], "company_id": cid})

        for s in prospects:
            pname = s.get("product_name")
            pid = name_to_product_id.get(pname)
            if not pid and name_to_product_id:
                pid = list(name_to_product_id.values())[0]
            await db.execute(
                """INSERT INTO prospects
                   (product_id, company_name, website, contact_name, contact_title, contact_email, location, raw_data, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (
                    pid,
                    s["company_name"],
                    s.get("website"),
                    s.get("contact_name"),
                    s.get("contact_title"),
                    s.get("contact_email"),
                    s.get("location"),
                    s.get("raw_data"),
                )
            )
            created["prospects"] += 1

        await db.execute(
            "INSERT OR REPLACE INTO system_meta (key, value) VALUES (?, ?)",
            ("sample_replies", json.dumps(replies))
        )
        await db.commit()

    first_company = created["companies"][0]["id"] if created["companies"] else None
    first_product = created["products"][0]["id"] if created["products"] else None

    return {
        "message": "Demo data seeded (idempotent reset)" if reset else "Demo data appended",
        "company_id": first_company,
        "product_id": first_product,
        "created": created,
        "prospects": created["prospects"],
        "sample_replies_available": len(replies),
    }


@app.get("/api/demo/sample-replies")
async def get_sample_replies():
    """Return pre-loaded sample conversation replies for offline reply classification demo."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await db.execute_fetchall(
            "SELECT value FROM system_meta WHERE key = ?", ("sample_replies",)
        )
        if row:
            return json.loads(row[0]["value"])
    # Fallback to file
    from .config import SAMPLE_DIR
    p = SAMPLE_DIR / "sample_replies.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return []


# ---------- Task queue (when Ollama is unavailable) ----------

@app.post("/api/queue")
async def enqueue_task(payload: dict):
    """
    Queue a workflow task for later processing when local inference is unavailable.
    Does NOT fall back to any cloud LLM.
    """
    task_type = payload.get("task_type")
    task_payload = payload.get("payload") or {}
    if not task_type:
        raise HTTPException(400, "task_type is required")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO task_queue (task_type, payload_json, status) VALUES (?, ?, 'pending')",
            (task_type, json.dumps(task_payload))
        )
        await db.commit()
        return {"id": cur.lastrowid, "status": "pending", "message": "Queued for local processing when Ollama is available"}


@app.get("/api/queue")
async def list_queue(status: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            rows = await db.execute_fetchall(
                "SELECT * FROM task_queue WHERE status = ? ORDER BY id DESC LIMIT 50", (status,)
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM task_queue ORDER BY id DESC LIMIT 50"
            )
        return [dict(r) for r in rows]

# Serve simple frontend
frontend_path = BASE_DIR / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def root():
    index = frontend_path / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "message": "LocalHarvey API is running",
        "docs": "/docs",
        "status": "/api/status",
        "seed_demo": "POST /api/demo/seed"
    }
