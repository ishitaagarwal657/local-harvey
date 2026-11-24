"""
SQLite database layer — fully local, no external dependencies.
"""
import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    website TEXT,
    description TEXT,
    industry TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    value_props TEXT,          -- JSON list
    pricing_model TEXT,
    target_segments TEXT,      -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS business_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    profile_json TEXT NOT NULL,
    model_used TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS icps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    icp_json TEXT NOT NULL,
    model_used TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    company_name TEXT NOT NULL,
    website TEXT,
    contact_name TEXT,
    contact_title TEXT,
    contact_email TEXT,
    location TEXT,
    raw_data TEXT,             -- JSON
    research_notes TEXT,
    buying_signals TEXT,       -- JSON list
    problem_statement TEXT,
    score REAL DEFAULT 0.0,
    score_reason TEXT,
    status TEXT DEFAULT 'new', -- new / researched / scored / outreach / replied
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS outreach_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    subject TEXT,
    body TEXT,
    sequence_step INTEGER DEFAULT 1,
    model_used TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER,
    direction TEXT,            -- inbound / outbound
    content TEXT,
    classification TEXT,       -- interested / objection / not_interested / out_of_office / other
    confidence REAL,
    model_used TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id)
);

CREATE TABLE IF NOT EXISTS inference_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT,
    model TEXT,
    prompt_hash TEXT,
    latency_ms INTEGER,
    success INTEGER,
    error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS task_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,          -- e.g. business_profile, icp, research, signals, ...
    payload_json TEXT NOT NULL,       -- JSON args needed to re-run the task
    status TEXT DEFAULT 'pending',    -- pending / processing / done / failed
    error TEXT,
    result_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def log_inference(agent: str, model: str, prompt_hash: str, latency_ms: int, success: bool, error: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO inference_logs (agent, model, prompt_hash, latency_ms, success, error) VALUES (?, ?, ?, ?, ?, ?)",
            (agent, model, prompt_hash, latency_ms, 1 if success else 0, error)
        )
        await db.commit()
