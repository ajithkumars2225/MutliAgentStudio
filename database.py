import sqlite3
import os
from typing import Optional

DB_FILE = "developer_studio.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create requirements history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requirements_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        prompt TEXT NOT NULL,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        max_iterations INTEGER NOT NULL,
        status TEXT NOT NULL
    )
    """)
    
    # Run column migration for parent_id if not exists
    try:
        cursor.execute("PRAGMA table_info(requirements_history)")
        columns = [row[1] for row in cursor.fetchall()]
        if "parent_id" not in columns:
            cursor.execute("ALTER TABLE requirements_history ADD COLUMN parent_id INTEGER DEFAULT NULL")
            print("[Database Migration] Added parent_id column to requirements_history table.")
    except Exception as e:
        print(f"[Database Warning] Migration check failed: {str(e)}")

    # Run column migration for history_id if not exists on telemetry_logs
    try:
        cursor.execute("PRAGMA table_info(telemetry_logs)")
        columns = [row[1] for row in cursor.fetchall()]
        if "history_id" not in columns:
            cursor.execute("ALTER TABLE telemetry_logs ADD COLUMN history_id INTEGER DEFAULT NULL")
            print("[Database Migration] Added history_id column to telemetry_logs table.")
    except Exception as e:
        print(f"[Database Warning] Telemetry migration check failed: {str(e)}")
        
    # 2. Create settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # 3. Create semantic cache table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS semantic_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        prompt TEXT NOT NULL,
        embedding TEXT,
        response TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. Create Codebase RAG Vector table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS codebase_rag (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace TEXT NOT NULL,
        filepath TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        symbol_name TEXT,
        chunk_text TEXT NOT NULL,
        embedding TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Populate settings default values if empty or missing
    defaults = {
        "provider": "gemini",
        "gemini_model": "gemini-2.5-flash",
        "openai_model": "gpt-4o-mini",
        "ollama_model": "qwen2.5-coder:7b",
        "claude_model": "claude-3-5-sonnet-latest",
        "openrouter_model": "google/gemini-2.5-flash",
        "groq_model": "llama-3.3-70b-specdec",
        "deepseek_model": "deepseek-chat",
        "together_model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "mistral_model": "codestral-latest",
        "cohere_model": "command-r-plus",
        "xai_model": "grok-2",
        "azure_model": "gpt-4o",
        "bedrock_model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "zai_model": "glm-4-flash",
        "omnirouter_model": "meta-llama/llama-3.3-70b-instruct",
        "nvidia_model": "nvidia/llama-3.1-nemotron-70b-instruct",
        "gemini_api_key": "",
        "openai_api_key": "",
        "anthropic_api_key": "",
        "openrouter_api_key": "",
        "groq_api_key": "",
        "deepseek_api_key": "",
        "together_api_key": "",
        "mistral_api_key": "",
        "cohere_api_key": "",
        "xai_api_key": "",
        "azure_api_key": "",
        "zai_api_key": "",
        "omnirouter_api_key": "",
        "nvidia_api_key": "",
        "ollama_base_url": "http://localhost:11434",
        "openrouter_base_url": "https://openrouter.ai/api/v1",
        "omnirouter_base_url": "http://localhost:20128/v1",
        "azure_endpoint": "",
        "azure_api_version": "2024-08-01-preview",
        "bedrock_region": "us-east-1",
        "max_iterations": "3",
        "approval_mode": "strict",
        "coder_provider": "llm",
        "coder_cli_command": 'agy run "{prompt_file}"',
        "semantic_cache": "true",
        "enable_free_limit": "false",
        "free_limit_rpm": "15",
        "active_workspace": os.path.abspath(os.path.join(os.getcwd(), "workspace"))
    }
    
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    # Migration: Update deprecated grok-beta to grok-2
    cursor.execute("UPDATE settings SET value = 'grok-2' WHERE key = 'xai_model' AND value = 'grok-beta'")
    
    # Migration: Upgrade old {prompt} inline CLI command to safe {prompt_file} version
    cursor.execute("UPDATE settings SET value = 'agy run \"{prompt_file}\"' WHERE key = 'coder_cli_command' AND value = 'agy run \"{prompt}\"'")
    
    # 4. Create telemetry logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telemetry_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        agent_name TEXT,
        provider TEXT,
        model TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_tokens INTEGER,
        latency_sec REAL,
        cost_usd REAL,
        prompt_text TEXT,
        response_text TEXT
    )
    """)
        
    conn.commit()
    conn.close()

# History Helpers
def get_all_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requirements_history ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_history_record(prompt: str, provider: str, model: str, max_iterations: int, status: str, parent_id: Optional[int] = None) -> int:
    from typing import Optional
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO requirements_history (prompt, provider, model, max_iterations, status, parent_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (prompt, provider, model, max_iterations, status, parent_id))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id

def update_history_record_status(record_id: int, status: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE requirements_history SET status = ? WHERE id = ?", (status, record_id))
    conn.commit()
    conn.close()

def delete_history_record(record_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM requirements_history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def clear_all_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM requirements_history")
    conn.commit()
    conn.close()

# Settings Helpers
def get_all_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def get_setting(key: str, default_value: str = "") -> str:
    settings = get_all_settings()
    return settings.get(key, default_value)

def update_db_settings(settings_dict: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    for key, value in settings_dict.items():
        cursor.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, str(value)))
    conn.commit()
    conn.close()

def get_active_workspace() -> str:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'active_workspace'")
        row = cursor.fetchone()
        conn.close()
        if row and row['value'] and os.path.isdir(row['value']):
            return os.path.abspath(row['value'])
    except Exception:
        pass
    return os.path.abspath(os.path.join(os.getcwd(), "workspace"))

# Semantic Cache Helpers
def get_semantic_cache(provider: str, model: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT prompt, embedding, response FROM semantic_cache WHERE provider = ? AND model = ?", (provider, model))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_semantic_cache(provider: str, model: str, prompt: str, embedding: str, response: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO semantic_cache (provider, model, prompt, embedding, response)
    VALUES (?, ?, ?, ?, ?)
    """, (provider, model, prompt, embedding, response))
    conn.commit()
    conn.close()

def clear_semantic_cache():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM semantic_cache")
    conn.commit()
    conn.close()

def get_all_semantic_cache() -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, provider, model, prompt, response FROM semantic_cache ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_semantic_cache_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM semantic_cache WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

from typing import Optional

def get_prompt_chain(history_id: Optional[int]) -> list:
    if history_id is None:
        return []
    prompts = []
    current_id = history_id
    conn = get_db_connection()
    cursor = conn.cursor()
    depth = 0
    while current_id is not None and depth < 50:
        cursor.execute("SELECT prompt, parent_id FROM requirements_history WHERE id = ?", (current_id,))
        row = cursor.fetchone()
        if not row:
            break
        prompts.append(row["prompt"])
        current_id = row["parent_id"]
        depth += 1
    conn.close()
    prompts.reverse()
    return prompts

def get_latest_history_id() -> Optional[int]:
    """
    Returns the ID of the most recent requirements history record.
    Used to auto-link follow-up prompts across sessions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM requirements_history ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row["id"] if row else None


def insert_telemetry_log(agent_name: str, provider: str, model: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, latency_sec: float, cost_usd: float, prompt_text: str, response_text: str, history_id: Optional[int] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO telemetry_logs (agent_name, provider, model, prompt_tokens, completion_tokens, total_tokens, latency_sec, cost_usd, prompt_text, response_text, history_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (agent_name, provider, model, prompt_tokens, completion_tokens, total_tokens, latency_sec, cost_usd, prompt_text, response_text, history_id))
    conn.commit()
    conn.close()

def get_telemetry_data() -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Totals
    cursor.execute("""
    SELECT 
        SUM(cost_usd) as total_cost,
        SUM(total_tokens) as total_tokens,
        COUNT(id) as total_calls,
        AVG(latency_sec) as avg_latency
    FROM telemetry_logs
    """)
    totals_row = cursor.fetchone()
    summary = {
        "total_cost": totals_row["total_cost"] or 0.0,
        "total_tokens": totals_row["total_tokens"] or 0,
        "total_calls": totals_row["total_calls"] or 0,
        "avg_latency": round(totals_row["avg_latency"] or 0.0, 2)
    }
    
    # 2. Agent Breakdown
    cursor.execute("""
    SELECT agent_name, SUM(cost_usd) as cost, SUM(total_tokens) as tokens
    FROM telemetry_logs
    GROUP BY agent_name
    """)
    agent_rows = cursor.fetchall()
    agent_breakdown = {row["agent_name"]: {"cost": row["cost"] or 0.0, "tokens": row["tokens"] or 0} for row in agent_rows}
    
    # 3. Grouped Runs (Parent logs)
    cursor.execute("""
    SELECT 
        h.id, 
        h.timestamp, 
        h.prompt, 
        h.provider, 
        h.model,
        COALESCE(SUM(t.total_tokens), 0) as total_tokens,
        COUNT(t.id) as total_calls,
        COALESCE(SUM(t.cost_usd), 0.0) as total_cost,
        COALESCE(AVG(t.latency_sec), 0.0) as avg_latency
    FROM requirements_history h
    INNER JOIN telemetry_logs t ON h.id = t.history_id
    GROUP BY h.id, h.timestamp, h.prompt, h.provider, h.model
    ORDER BY h.timestamp DESC
    """)
    grouped_rows = cursor.fetchall()
    grouped_runs = []
    for row in grouped_rows:
        run_id = row["id"]
        # Fetch the detailed individual calls for this run
        cursor.execute("SELECT * FROM telemetry_logs WHERE history_id = ? ORDER BY timestamp ASC", (run_id,))
        details = [dict(d) for d in cursor.fetchall()]
        
        grouped_runs.append({
            "id": run_id,
            "timestamp": row["timestamp"],
            "prompt": row["prompt"],
            "provider": row["provider"],
            "model": row["model"],
            "total_tokens": row["total_tokens"],
            "total_calls": row["total_calls"],
            "total_cost": round(row["total_cost"], 6),
            "avg_latency": round(row["avg_latency"], 2),
            "details": details
        })
        
    # 4. Fetch orphaned logs (where history_id is NULL)
    cursor.execute("SELECT * FROM telemetry_logs WHERE history_id IS NULL ORDER BY timestamp DESC LIMIT 50")
    orphaned_logs = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return {
        "summary": summary,
        "totals": summary,
        "agent_breakdown": agent_breakdown,
        "grouped_runs": grouped_runs,
        "orphaned_logs": orphaned_logs
    }

# ----------------- CODEBASE RAG DATABASE HELPERS -----------------

def clear_rag_chunks(workspace: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM codebase_rag WHERE workspace = ?", (workspace,))
    conn.commit()
    conn.close()

def save_rag_chunks(workspace: str, chunks: list):
    conn = get_db_connection()
    cursor = conn.cursor()
    for idx, item in enumerate(chunks):
        cursor.execute("""
        INSERT INTO codebase_rag (workspace, filepath, chunk_index, symbol_name, chunk_text, embedding)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (workspace, item["filepath"], idx, item.get("symbol_name"), item["chunk_text"], item.get("embedding")))
    conn.commit()
    conn.close()

def get_rag_chunks(workspace: str) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM codebase_rag WHERE workspace = ? ORDER BY filepath, chunk_index", (workspace,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def reset_telemetry_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM telemetry_logs")
    conn.commit()
    conn.close()

def get_all_telemetry_logs() -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM telemetry_logs ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
