import os
import sys
import io
import json
import threading
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure local dir is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load env
load_dotenv()

# Setup system logs interception
class WebLogStream(io.StringIO):
    def __init__(self):
        super().__init__()
        self.logs = []
        self._lock = threading.Lock()
        
    def write(self, s):
        # Console output
        sys.__stdout__.write(s)
        # Web intercept
        clean_s = s.strip()
        if clean_s:
            with self._lock:
                # Split multiline logs
                for line in clean_s.splitlines():
                    if line.strip():
                        self.logs.append(line.strip())
                        
    def get_logs(self):
        with self._lock:
            return list(self.logs)
            
    def clear(self):
        with self._lock:
            self.logs.clear()

log_stream = WebLogStream()
sys.stdout = log_stream
sys.stderr = log_stream

# Import local modules AFTER setting up stdout intercept
from utils import scan_workspace, read_workspace_file
import agents
import database
database.init_db()

app = FastAPI(title="Multi-Agent Developer Studio")

# State holders
agent_thread: Optional[threading.Thread] = None
agent_running = False
final_state = {}
last_execution_error = ""

class StartRequest(BaseModel):
    prompt: str
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_iterations: int
    parent_id: Optional[int] = None
    start_fresh: Optional[bool] = False

class FeedbackRequest(BaseModel):
    feedback: str

def run_agent_in_thread(prompt: str, max_iterations: int, provider: str, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None, history_id: int = 0):
    global agent_running, final_state, last_execution_error
    agents.active_history_id = history_id
    agent_running = True
    log_stream.clear()
    
    # Load all settings from the SQLite database
    settings = database.get_all_settings()
    for key, val in settings.items():
        if val is not None:
            os.environ[key.upper()] = str(val)

    # Configure provider and dynamic model/credentials override
    os.environ["LLM_PROVIDER"] = provider
    if provider == "gemini":
        os.environ["GEMINI_MODEL"] = model_name
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
    elif provider == "openai":
        os.environ["OPENAI_MODEL"] = model_name
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
    elif provider == "ollama":
        os.environ["OLLAMA_MODEL"] = model_name
        if base_url:
            os.environ["OLLAMA_BASE_URL"] = base_url
    elif provider == "claude" or provider == "anthropic":
        os.environ["LLM_PROVIDER"] = "claude"
        os.environ["ANTHROPIC_MODEL"] = model_name
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
    elif provider == "openrouter":
        os.environ["OPENROUTER_MODEL"] = model_name
        if api_key:
            os.environ["OPENROUTER_API_KEY"] = api_key
        if base_url:
            os.environ["OPENROUTER_BASE_URL"] = base_url
    elif provider == "groq":
        os.environ["GROQ_MODEL"] = model_name
        if api_key:
            os.environ["GROQ_API_KEY"] = api_key
    elif provider == "deepseek":
        os.environ["DEEPSEEK_MODEL"] = model_name
        if api_key:
            os.environ["DEEPSEEK_API_KEY"] = api_key
    elif provider == "together":
        os.environ["TOGETHER_MODEL"] = model_name
        if api_key:
            os.environ["TOGETHER_API_KEY"] = api_key
    elif provider == "mistral":
        os.environ["MISTRAL_MODEL"] = model_name
        if api_key:
            os.environ["MISTRAL_API_KEY"] = api_key
    elif provider == "cohere":
        os.environ["COHERE_MODEL"] = model_name
        if api_key:
            os.environ["COHERE_API_KEY"] = api_key
    elif provider == "xai":
        os.environ["XAI_MODEL"] = model_name
        if api_key:
            os.environ["XAI_API_KEY"] = api_key
    elif provider == "azure":
        os.environ["AZURE_MODEL"] = model_name
        if api_key:
            os.environ["AZURE_API_KEY"] = api_key
        if base_url:
            os.environ["AZURE_ENDPOINT"] = base_url
    elif provider == "bedrock":
        os.environ["BEDROCK_MODEL"] = model_name
        if base_url:
            os.environ["BEDROCK_REGION"] = base_url
    elif provider == "zai":
        os.environ["ZAI_MODEL"] = model_name
        if api_key:
            os.environ["ZAI_API_KEY"] = api_key
    elif provider == "omnirouter":
        os.environ["OMNIROUTER_MODEL"] = model_name
        if api_key:
            os.environ["OMNIROUTER_API_KEY"] = api_key
        if base_url:
            os.environ["OMNIROUTER_BASE_URL"] = base_url
    elif provider == "nvidia":
        os.environ["NVIDIA_MODEL"] = model_name
        if api_key:
            os.environ["NVIDIA_API_KEY"] = api_key
        
    agents.web_mode = True
    
    # Strip history header wrapper context from prompt to parse path from current request only
    search_prompt = prompt
    if "=== CONVERSATION CHAT HISTORY ===" in prompt:
        parts = prompt.split("Current follow-up request to execute:\n")
        if len(parts) > 1:
            search_prompt = parts[-1]

    import re
    mentioned_path = None
    if os.name == 'nt':
        # On Windows, only parse Windows-style absolute paths (e.g. C:\folder or C:/folder)
        win_match = re.search(r'([a-zA-Z]:[\\/][^:<>\"|?*\r\n\t]+)', search_prompt)
        if win_match:
            potential_path = win_match.group(1).strip()
            potential_path = re.sub(r'[\.\;\,\?\!\"\']+$', '', potential_path).strip()
            if "." in os.path.basename(potential_path) and not os.path.isdir(potential_path):
                mentioned_path = os.path.dirname(os.path.abspath(potential_path))
            else:
                mentioned_path = os.path.abspath(potential_path)
    else:
        # On Unix systems, parse Unix absolute paths (e.g. /home/user/project)
        unix_match = re.search(r'(/[a-zA-Z0-9_\.\-]+/[a-zA-Z0-9_\.\-/]+)', search_prompt)
        if unix_match:
            potential_path = unix_match.group(1).strip()
            potential_path = re.sub(r'[\.\;\,\?\!\"\']+$', '', potential_path).strip()
            if "." in os.path.basename(potential_path) and not os.path.isdir(potential_path):
                mentioned_path = os.path.dirname(os.path.abspath(potential_path))
            else:
                mentioned_path = os.path.abspath(potential_path)

    if mentioned_path and ".github" not in mentioned_path:
        if len(mentioned_path) > 3:  # avoid single letters or bare "C:\" being parsed
            print(f"Detected mentioned workspace path in prompt: {mentioned_path}")
            try:
                os.makedirs(mentioned_path, exist_ok=True)
                database.update_db_settings({"active_workspace": mentioned_path})
                print(f"Workspace dynamically updated to: {mentioned_path}")
            except Exception as e:
                print(f"Failed to create/set mentioned workspace path: {e}")

    workspace_dir = database.get_active_workspace()
    
    # Initialize Git & Checkout isolated task branch
    from utils import git_init, git_checkout_branch
    git_init(workspace_dir)
    git_checkout_branch(workspace_dir, f"studio-task-{history_id}")
    
    print(f"Scanning workspace folder for existing codebase: {workspace_dir}")
    existing_codebase = scan_workspace(workspace_dir)
    
    import json
    state_file = os.path.join(workspace_dir, ".studio", "state.json")
    loaded_state = {}
    
    # Strip history header wrapper context from prompt comparison to match correctly
    comp_prompt = prompt
    if "=== CONVERSATION CHAT HISTORY ===" in prompt:
        parts = prompt.split("Current follow-up request to execute:\n")
        if len(parts) > 1:
            comp_prompt = parts[-1]
            
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                stored_prompt = data.get("prompt", "")
                if "=== CONVERSATION CHAT HISTORY ===" in stored_prompt:
                    s_parts = stored_prompt.split("Current follow-up request to execute:\n")
                    if len(s_parts) > 1:
                        stored_prompt = s_parts[-1]
                if stored_prompt.strip() == comp_prompt.strip():
                    loaded_state = data
                    print(f"🔄 [Resuming Simulation] Found matching state for prompt. Resuming from next_agent={data.get('next_agent')}")
                else:
                    print(f"[State Resumer] Stored prompt mismatch. Starting clean run.")
        except Exception as e:
            print(f"[State Resumer Warning] Failed to load previous state: {e}")
            
    # ── Smart State Resume Logic ─────────────────────────────────────────────
    # Case 1: Same prompt → resume from exact saved checkpoint
    # Case 2: New prompt on existing codebase → detect intent:
    #   - Bug report / fix request → inject prompt as error → ImplementEngineer
    #   - New feature on same project → fresh BA run but carry requirements context
    
    # Keywords indicating the user is reporting a bug or issue to fix
    BUG_INTENT_PHRASES = [
        "fix", "bug", "error", "issue", "problem", "not working", "broken",
        "fails", "failing", "crash", "exception", "incorrect", "wrong",
        "doesn't work", "does not work", "cant", "cannot", "unable to",
        "facing issue", "getting error", "shows error", "why is", "why does",
    ]
    
    new_prompt_lower = comp_prompt.lower()
    is_bug_report = any(phrase in new_prompt_lower for phrase in BUG_INTENT_PHRASES)
    has_existing_code = bool(existing_codebase)
    is_new_prompt = not loaded_state  # True when no state was resumed
    
    # If it's a new prompt describing a bug on an existing codebase,
    # load requirements/impact context from saved state (if present) but
    # treat the new prompt description as the error to fix
    context_state = {}
    if is_new_prompt and is_bug_report and has_existing_code and os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                context_state = json.load(f)
            print(f"🐛 [Smart Resume] Bug-report detected on existing codebase. Loading context from previous run.")
            print(f"🐛 [Smart Resume] Routing to ImplementEngineer to fix: '{comp_prompt[:120]}...'")
        except Exception:
            context_state = {}

    initial_state = {
        "prompt": prompt,
        # Carry requirements & impact from saved state so agents have full context
        "requirements": loaded_state.get("requirements", "") or context_state.get("requirements", ""),
        "impact_analysis": loaded_state.get("impact_analysis", "") or context_state.get("impact_analysis", ""),
        "files_to_modify": loaded_state.get("files_to_modify", []) or context_state.get("files_to_modify", []),
        "codebase": existing_codebase,
        "test_plan": "",
        "test_results": "",
        "deployment_plan": "",
        "deployment_logs": "",
        # Bug report: inject the user's description as the error to fix
        # Normal resume: carry forward the saved errors
        "errors": f"User reported issue:\n{comp_prompt}" if (is_new_prompt and is_bug_report and has_existing_code) else loaded_state.get("errors", ""),
        "iterations": loaded_state.get("iterations", 0) if loaded_state else 0,
        "max_iterations": max_iterations,
        "next_agent": loaded_state.get("next_agent", "BusinessAnalyst"),
        "incidents": []
    }

    
    try:
        from main import build_graph
        graph = build_graph()
        final_state = graph.invoke(initial_state)
        
        errors = final_state.get("errors", "")
        iterations = final_state.get("iterations", 0)
        max_iter = int(final_state.get("max_iterations", 3))
        
        if errors and (iterations >= max_iter or final_state.get("next_agent") == "FINISH"):
            print("\n❌ SIMULATION ENDED WITH UNRESOLVED ERRORS (RETRY LIMIT EXCEEDED).")
            database.update_history_record_status(history_id, "failed")
            last_execution_error = f"Iteration Limit Reached: Failed to resolve codebase errors within {max_iter} attempts.\nFinal QA Error Trace:\n{errors}"
        else:
            print("\n🎉 SIMULATION COMPLETED SUCCESSFULLY!")
            database.update_history_record_status(history_id, "completed")
            last_execution_error = ""
    except (SystemExit, agents.AgentTerminatedException):
        print("\n🛑 SIMULATION TERMINATED BY USER.")
        database.update_history_record_status(history_id, "terminated")
        last_execution_error = "Simulation terminated by user."
    except Exception as e:
        if "terminated" in str(e).lower():
            print("\n🛑 SIMULATION TERMINATED BY USER.")
            database.update_history_record_status(history_id, "terminated")
            last_execution_error = "Simulation terminated by user."
        else:
            print(f"\n[FATAL ERROR DURING GRAPH EXECUTION]: {str(e)}")
            database.update_history_record_status(history_id, "failed")
            last_execution_error = str(e)
    finally:
        agent_running = False
        agents.web_mode = False
        agents.pause_event.set()
        agents.active_agent_name = "idle"
        agents.active_history_id = None

@app.post("/api/start")
def start_agent(req: StartRequest):
    global agent_thread, agent_running
    agents.stop_event.clear()
    workspace_dir = database.get_active_workspace()
    
    # ── 1. True Fresh Start Cleanup ──────────────────────────────────────────
    if req.start_fresh:
        files_to_wipe = [
            os.path.join(workspace_dir, ".studio", "state.json"),
            os.path.join(workspace_dir, ".studio", "session_summary.json"),
            os.path.join(workspace_dir, ".studio", "prompt.txt"),
            os.path.join(workspace_dir, "walkthrough_agent.md"),
            os.path.join(workspace_dir, "test_report.md"),
            os.path.join(workspace_dir, "test_report.html"),
        ]
        for fpath in files_to_wipe:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                    print(f"[Start Fresh 🧹] Removed old session artifact: {os.path.basename(fpath)}")
                except Exception as e:
                    print(f"[Start Fresh Warning] Failed to delete {fpath}: {e}")

    # ── 2. Smart Follow-up vs. New Requirement Detection ───────────────────
    prompt_lower = req.prompt.lower().strip()
    
    # Keywords indicating a brand-new application creation request
    NEW_PROJECT_PHRASES = [
        "create a ", "create new ", "build a ", "build new ", "develop a ", "develop new ",
        "generate a ", "generate new ", "make a new ", "start a new ", "design a "
    ]
    is_new_app_request = any(prompt_lower.startswith(phrase) or f" {phrase}" in prompt_lower for phrase in NEW_PROJECT_PHRASES)
    
    # Keywords indicating an explicit follow-up or bug fix
    FOLLOWUP_PHRASES = [
        "add ", "update ", "fix ", "modify ", "change ", "also ", "now ", "extend ",
        "feature ", "issue ", "bug ", "improve ", "refactor ", "delete ", "remove "
    ]
    is_explicit_followup = any(phrase in prompt_lower for phrase in FOLLOWUP_PHRASES)

    parent_id_to_use = req.parent_id

    # Auto-link parent_id ONLY if it's NOT a fresh start, NOT a new app request, AND looks like a follow-up
    if not parent_id_to_use and not req.start_fresh and not is_new_app_request:
        latest_id = database.get_latest_history_id()
        if latest_id and is_explicit_followup:
            parent_id_to_use = latest_id
            print(f"[Session Context 🔗] Auto-linked follow-up prompt to session history record #{parent_id_to_use}")

    # ── 3. Build Context Header ──────────────────────────────────────────────
    # Only load previous session history & summary if start_fresh is False AND it's a follow-up
    is_fresh_run = req.start_fresh or is_new_app_request
    history_text = ""
    if parent_id_to_use and not is_fresh_run:
        chain = database.get_prompt_chain(parent_id_to_use)
        if chain:
            pruned_chain = chain if len(chain) <= 6 else [chain[0]] + chain[-4:]
            history_blocks = []
            for idx, past_prompt in enumerate(pruned_chain, 1):
                clean_prompt = past_prompt
                for marker in ["=== PREVIOUS SESSION ACCOMPLISHMENTS", "=== CONVERSATION CHAT HISTORY ==="]:
                    if marker in past_prompt:
                        parts = past_prompt.split("Current follow-up request to execute:\n")
                        if len(parts) > 1:
                            clean_prompt = parts[-1]
                            break
                history_blocks.append(f"Turn {idx}: {clean_prompt.strip()}")
            history_text = "\n".join(history_blocks)
            if len(history_text) > 4000:
                history_text = history_text[-4000:] + "\n[Older prompt history windowed for token optimization]"

    summary_blocks = []
    if not is_fresh_run:
        from utils import get_session_summary
        session_summary = get_session_summary(workspace_dir)

        # Check for walkthrough_agent.md in workspace
        walkthrough_path = os.path.join(workspace_dir, "walkthrough_agent.md")
        if os.path.exists(walkthrough_path):
            try:
                with open(walkthrough_path, "r", encoding="utf-8") as f:
                    wt_content = f.read().strip()
                    if wt_content:
                        summary_blocks.append(f"Recent Handoff & Accomplishments Summary:\n{wt_content[:1500]}")
            except Exception:
                pass

        if session_summary.get("requirements"):
            req_text = session_summary["requirements"].strip()
            summary_blocks.append(f"Established System Requirements & Specifications:\n{req_text[:1200]}")

        if session_summary.get("files_modified"):
            files_list = session_summary["files_modified"]
            summary_blocks.append(f"Previously Built Codebase Files:\n- " + "\n- ".join(files_list[:25]))

    # Combine into rich prompt header
    context_header_parts = []
    if summary_blocks:
        context_header_parts.append("=== PREVIOUS SESSION ACCOMPLISHMENTS & SYSTEM CONTEXT ===")
        context_header_parts.append("\n\n".join(summary_blocks))
        context_header_parts.append("=========================================================")

    if history_text:
        context_header_parts.append("=== PRIOR PROMPT HISTORY ===")
        context_header_parts.append(history_text)
        context_header_parts.append("============================")

    if context_header_parts and not is_fresh_run:
        prompt_to_run = "\n\n".join(context_header_parts) + f"\n\nCurrent follow-up request to execute:\n{req.prompt}"
        print(f"[Session Context 🧠] Injected Session Accomplishments & Prompt History into execution prompt.")
    else:
        prompt_to_run = req.prompt
        if is_fresh_run:
            print(f"[Start Fresh 🚀] Executing fresh requirement prompt with clean state.")


    # Write history entry with 'running' status and parent link
    history_id = database.add_history_record(
        prompt=req.prompt,
        provider=req.provider,
        model=req.model,
        max_iterations=req.max_iterations,
        status="running",
        parent_id=parent_id_to_use
    )
    
    # Reset last execution error
    global last_execution_error
    last_execution_error = ""

    # Start thread
    agent_thread = threading.Thread(
        target=run_agent_in_thread,
        args=(prompt_to_run, req.max_iterations, req.provider, req.model, req.api_key, req.base_url, history_id)
    )
    agent_thread.daemon = True
    agent_thread.start()
    
    return {"status": "started", "history_id": history_id}

@app.get("/api/status")
def get_status():
    workspace_dir = database.get_active_workspace()
    files_list = list(scan_workspace(workspace_dir).keys())
    
    logs = log_stream.get_logs()
    from utils import detect_preview_url
    logs_block = "\n".join(logs[-100:]) if logs else ""
    preview_url = detect_preview_url(logs_block)
    
    return {
        "running": agent_running,
        "paused": not agents.pause_event.is_set(),
        "active_agent": agents.active_agent_name if agent_running else "idle",
        "logs": logs,
        "awaiting_approval": agents.pending_approval_stage != "",
        "approval_stage": agents.pending_approval_stage,
        "approval_text": agents.pending_approval_text,
        "files": files_list,
        "active_workspace": workspace_dir,
        "preview_url": preview_url,
        "last_error": last_execution_error,
        "iterations": (lambda: (
            int(json.load(open(os.path.join(workspace_dir, ".studio", "state.json"), "r", encoding="utf-8")).get("iterations", 0))
            if os.path.exists(os.path.join(workspace_dir, ".studio", "state.json")) else 0
        ))(),
        "max_iterations": (lambda: (
            int(json.load(open(os.path.join(workspace_dir, ".studio", "state.json"), "r", encoding="utf-8")).get("max_iterations", 0))
            if os.path.exists(os.path.join(workspace_dir, ".studio", "state.json")) else 0
        ))()
    }

@app.get("/api/checkpoint")
def get_checkpoint():
    """
    Returns active session checkpoint data for the current workspace.
    """
    workspace_dir = database.get_active_workspace()
    checkpoint_file = os.path.join(workspace_dir, ".studio", "checkpoint.json")
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to load checkpoint: {e}"}
    return {"status": "No active checkpoint file"}

@app.get("/api/transcript")
def get_transcript():
    """
    Returns step-by-step agent trajectory log entries (.studio/transcript.jsonl).
    """
    workspace_dir = database.get_active_workspace()
    transcript_file = os.path.join(workspace_dir, ".studio", "transcript.jsonl")
    entries = []
    if os.path.exists(transcript_file):
        try:
            with open(transcript_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line.strip()))
            return {"transcript": entries[-50:]}  # Return last 50 trajectory steps
        except Exception as e:
            return {"error": f"Failed to read transcript: {e}"}
    return {"transcript": []}


@app.post("/api/pause")
def pause_agent():
    agents.pause_event.clear()
    print("\n⏸️ [Web Signal] Pausing agent orchestration flow...")
    return {"status": "paused"}

@app.post("/api/resume")
def resume_agent():
    agents.pause_event.set()
    print("\n▶️ [Web Signal] Resuming agent orchestration flow...")
    return {"status": "resumed"}

def terminate_thread(thread: threading.Thread):
    import ctypes
    if not thread.is_alive():
        return
    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread.ident),
        exc
    )
    if res == 0:
        raise ValueError("nonexistent thread id")
    elif res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

@app.post("/api/terminate")
def terminate_agent():
    global agent_thread, agent_running
    
    # 1. Set global stop event in agents module
    agents.stop_event.set()
    
    # 2. Unblock execution locks so waiting thread breaks immediately
    agents.pause_event.set()
    agents.approval_event.set()
    agents.active_agent_name = "idle"
    agent_running = False
    
    # 3. Raise async exception on thread if alive
    if agent_thread and agent_thread.is_alive():
        try:
            terminate_thread(agent_thread)
        except Exception as e:
            print(f"[Terminate note]: {e}")
            
    print("\n🛑 [Web Signal] Terminated agent simulation flow successfully.")
    return {"status": "terminated"}


@app.post("/api/approve")
def approve_stage():
    if not agents.pending_approval_stage:
        raise HTTPException(status_code=400, detail="No stage is currently awaiting approval.")
        
    agents.web_feedback = ""
    # Release the lock
    agents.approval_event.set()
    return {"status": "approved"}

@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    if not agents.pending_approval_stage:
        raise HTTPException(status_code=400, detail="No stage is currently awaiting approval.")
        
    agents.web_feedback = req.feedback
    # Release the lock
    agents.approval_event.set()
    return {"status": "feedback_submitted"}

@app.get("/api/file")
def get_file(path: str):
    workspace_dir = database.get_active_workspace()
    try:
        content = read_workspace_file(workspace_dir, path)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class CreateFileRequest(BaseModel):
    path: str

class DeleteFileRequest(BaseModel):
    path: str

@app.post("/api/file/create")
def create_file(req: CreateFileRequest):
    workspace_dir = database.get_active_workspace()
    target_path = os.path.abspath(os.path.join(workspace_dir, req.path))
    
    if not target_path.startswith(os.path.abspath(workspace_dir)):
        raise HTTPException(status_code=400, detail="Invalid path (out of workspace scope)")
        
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    if not os.path.exists(target_path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("")
    return {"status": "created"}

@app.post("/api/folder/create")
def create_folder(req: CreateFileRequest):
    workspace_dir = database.get_active_workspace()
    target_path = os.path.abspath(os.path.join(workspace_dir, req.path))
    
    if not target_path.startswith(os.path.abspath(workspace_dir)):
        raise HTTPException(status_code=400, detail="Invalid path (out of workspace scope)")
        
    os.makedirs(target_path, exist_ok=True)
    return {"status": "created"}

@app.post("/api/file/delete")
def delete_file(req: DeleteFileRequest):
    workspace_dir = database.get_active_workspace()
    target_path = os.path.abspath(os.path.join(workspace_dir, req.path))
    
    if not target_path.startswith(os.path.abspath(workspace_dir)):
        raise HTTPException(status_code=400, detail="Invalid path (out of workspace scope)")
        
    if os.path.isdir(target_path):
        import shutil
        shutil.rmtree(target_path)
    elif os.path.exists(target_path):
        os.remove(target_path)
    return {"status": "deleted"}

@app.post("/api/file/reveal")
def reveal_in_explorer():
    import subprocess
    workspace_dir = database.get_active_workspace()
    os.makedirs(workspace_dir, exist_ok=True)
    try:
        subprocess.Popen(f'explorer "{workspace_dir}"')
        return {"status": "revealed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SaveFileRequest(BaseModel):
    path: str
    content: str

@app.post("/api/file/save")
def save_file(req: SaveFileRequest):
    workspace_dir = database.get_active_workspace()
    target_path = os.path.abspath(os.path.join(workspace_dir, req.path))
    
    if not target_path.startswith(os.path.abspath(workspace_dir)):
        raise HTTPException(status_code=400, detail="Invalid path (out of workspace scope)")
        
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class OpenWorkspaceRequest(BaseModel):
    path: str

@app.post("/api/workspace/select")
def select_workspace_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        selected_path = filedialog.askdirectory(title="Select Repository Folder")
        root.destroy()
        
        if not selected_path:
            return {"status": "cancelled"}
            
        return {"status": "selected", "path": os.path.abspath(selected_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder picker: {str(e)}")

@app.post("/api/workspace/open")
def open_workspace(req: OpenWorkspaceRequest):
    target_path = os.path.abspath(req.path)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=400, detail="The specified folder path does not exist on disk.")
    if not os.path.isdir(target_path):
        raise HTTPException(status_code=400, detail="The specified path is a file, not a directory.")
        
    database.update_db_settings({"active_workspace": target_path})
    
    # Restart the interactive terminal session inside the new folder location
    try:
        terminal_manager.start(target_path)
    except Exception as e:
        print(f"[Terminal] Failed to restart terminal in new workspace: {str(e)}")
        
    return {
        "status": "opened",
        "active_workspace": target_path,
        "files": list(scan_workspace(target_path).keys())
    }

@app.get("/api/workspace/active")
def get_active_workspace_route():
    return {"active_workspace": database.get_active_workspace()}

@app.get("/api/git/status")
def get_git_status_route():
    from utils import git_get_status
    workspace_dir = database.get_active_workspace()
    return git_get_status(workspace_dir)

@app.get("/api/git/diff")
def get_git_diff_route():
    from utils import git_get_diff
    workspace_dir = database.get_active_workspace()
    return {"diff": git_get_diff(workspace_dir)}
@app.get("/api/symbols")
def get_symbols_endpoint():
    from ast_engine import EnterpriseASTEngine
    workspace_dir = database.get_active_workspace()
    return EnterpriseASTEngine.get_workspace_symbol_index(workspace_dir)

@app.get("/api/symbols/search")
def search_symbols_endpoint(q: str = "", type: str = "all"):
    from ast_engine import EnterpriseASTEngine
    workspace_dir = database.get_active_workspace()
    return {"query": q, "type": type, "results": EnterpriseASTEngine.search_symbols(workspace_dir, q, type)}

@app.get("/api/symbols/references")
def get_symbol_references_endpoint(name: str = ""):
    from ast_engine import EnterpriseASTEngine
    workspace_dir = database.get_active_workspace()
    return {"symbol": name, "references": EnterpriseASTEngine.find_symbol_references(workspace_dir, name)}

@app.get("/api/dependencies")
def get_dependencies_endpoint():
    from ast_engine import EnterpriseASTEngine
    workspace_dir = database.get_active_workspace()
    return EnterpriseASTEngine.get_full_dependency_graph(workspace_dir)

@app.get("/api/dependencies/circular")
def get_circular_dependencies_endpoint():
    from ast_engine import EnterpriseASTEngine
    workspace_dir = database.get_active_workspace()
    return {"circular_cycles": EnterpriseASTEngine.detect_circular_dependencies(workspace_dir)}

@app.get("/api/dependencies/impact-radius")
def get_impact_radius_endpoint(files: str = ""):
    from ast_engine import EnterpriseASTEngine
    workspace_dir = database.get_active_workspace()
    target_files = [f.strip() for f in files.split(",") if f.strip()]
    return EnterpriseASTEngine.calculate_impact_radius(workspace_dir, target_files)

@app.get("/api/react-trace")
def get_react_trace_endpoint():
    from react_engine import EnterpriseReActEngine
    return {"trace": EnterpriseReActEngine.get_trace_history()}

@app.delete("/api/react-trace")
def clear_react_trace_endpoint():
    from react_engine import EnterpriseReActEngine
    EnterpriseReActEngine.clear_trace_history()
    return {"status": "cleared"}

@app.get("/api/rag/search")
def search_rag_endpoint(q: str = "", top_k: int = 4):
    from rag_engine import CodebaseRAGEngine
    workspace_dir = database.get_active_workspace()
    provider = database.get_setting("llm_provider", "google")
    results = CodebaseRAGEngine.search_codebase_rag(workspace_dir, q, top_k=top_k, provider=provider)
    return {"query": q, "results": results}

@app.post("/api/rag/index")
def index_rag_endpoint():
    from rag_engine import CodebaseRAGEngine
    workspace_dir = database.get_active_workspace()
    provider = database.get_setting("llm_provider", "google")
    count = CodebaseRAGEngine.index_workspace(workspace_dir, provider=provider)
    return {"status": "indexed", "chunks": count}

@app.get("/api/memory/all")
def get_all_memories_endpoint():
    from episodic_memory import EpisodicMemoryEngine
    return {"memories": EpisodicMemoryEngine.get_all_memories()}

@app.delete("/api/memory/{memory_id}")
def delete_memory_endpoint(memory_id: int):
    from episodic_memory import EpisodicMemoryEngine
    EpisodicMemoryEngine.delete_memory(memory_id)
    return {"status": "deleted", "id": memory_id}

@app.get("/api/memory/recall")
def recall_memory_endpoint(q: str = ""):
    from episodic_memory import EpisodicMemoryEngine
    provider = database.get_setting("llm_provider", "google")
    memories = EpisodicMemoryEngine.recall_relevant_memories(q, top_k=5, provider=provider)
    return {"query": q, "memories": memories}

@app.post("/api/memory/store")
def store_memory_endpoint(category: str, concept: str, value: str):
    from episodic_memory import EpisodicMemoryEngine
    provider = database.get_setting("llm_provider", "google")
    EpisodicMemoryEngine.store_memory(category, concept, value, provider=provider)
    return {"status": "saved"}

@app.get("/api/visual-audit")
def visual_audit_endpoint():
    from visual_auditor import VisualUIAuditorEngine
    workspace_dir = database.get_active_workspace()
    return {"audits": VisualUIAuditorEngine.audit_workspace_ui(workspace_dir)}

@app.post("/api/mutation-test")
def mutation_test_endpoint(target_file: str, test_file: str):
    from mutation_testing import MutationTestingEngine
    workspace_dir = database.get_active_workspace()
    return MutationTestingEngine.run_mutation_test_suite(workspace_dir, target_file, test_file)

@app.get("/api/history")
def get_history():
    return database.get_all_history()

@app.delete("/api/history/{record_id}")
def delete_history_item(record_id: int):
    database.delete_history_record(record_id)
    return {"status": "deleted"}

@app.delete("/api/history")
def clear_history():
    database.clear_all_history()
    return {"status": "cleared"}

@app.get("/api/settings")
def get_settings():
    return database.get_all_settings()

class UpdateSettingsRequest(BaseModel):
    provider: str
    max_iterations: int
    gemini_model: Optional[str] = None
    openai_model: Optional[str] = None
    ollama_model: Optional[str] = None
    claude_model: Optional[str] = None
    openrouter_model: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    openrouter_base_url: Optional[str] = None
    
    groq_model: Optional[str] = None
    deepseek_model: Optional[str] = None
    together_model: Optional[str] = None
    mistral_model: Optional[str] = None
    cohere_model: Optional[str] = None
    xai_model: Optional[str] = None
    azure_model: Optional[str] = None
    bedrock_model: Optional[str] = None
    zai_model: Optional[str] = None
    omnirouter_model: Optional[str] = None
    nvidia_model: Optional[str] = None
    
    groq_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    together_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    azure_api_key: Optional[str] = None
    zai_api_key: Optional[str] = None
    omnirouter_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    azure_endpoint: Optional[str] = None
    azure_api_version: Optional[str] = None
    omnirouter_base_url: Optional[str] = None
    bedrock_region: Optional[str] = None
    approval_mode: Optional[str] = None
    coder_provider: Optional[str] = None
    coder_cli_command: Optional[str] = None
    semantic_cache: Optional[str] = None
    # Network settings
    network_port: Optional[int] = None
    network_host: Optional[str] = None
    network_cors_origins: Optional[str] = None
    # Free Tier Quota Pacing settings
    enable_free_limit: Optional[str] = None
    free_limit_rpm: Optional[int] = None

@app.post("/api/settings")
def update_settings(req: UpdateSettingsRequest):
    payload = {
        "provider": req.provider,
        "max_iterations": req.max_iterations
    }
    if req.gemini_model is not None: payload["gemini_model"] = req.gemini_model
    if req.openai_model is not None: payload["openai_model"] = req.openai_model
    if req.ollama_model is not None: payload["ollama_model"] = req.ollama_model
    if req.claude_model is not None: payload["claude_model"] = req.claude_model
    if req.openrouter_model is not None: payload["openrouter_model"] = req.openrouter_model
    if req.gemini_api_key is not None: payload["gemini_api_key"] = req.gemini_api_key
    if req.openai_api_key is not None: payload["openai_api_key"] = req.openai_api_key
    if req.anthropic_api_key is not None: payload["anthropic_api_key"] = req.anthropic_api_key
    if req.openrouter_api_key is not None: payload["openrouter_api_key"] = req.openrouter_api_key
    if req.ollama_base_url is not None: payload["ollama_base_url"] = req.ollama_base_url
    if req.openrouter_base_url is not None: payload["openrouter_base_url"] = req.openrouter_base_url
    
    if req.groq_model is not None: payload["groq_model"] = req.groq_model
    if req.deepseek_model is not None: payload["deepseek_model"] = req.deepseek_model
    if req.together_model is not None: payload["together_model"] = req.together_model
    if req.mistral_model is not None: payload["mistral_model"] = req.mistral_model
    if req.cohere_model is not None: payload["cohere_model"] = req.cohere_model
    if req.xai_model is not None: payload["xai_model"] = req.xai_model
    if req.azure_model is not None: payload["azure_model"] = req.azure_model
    if req.bedrock_model is not None: payload["bedrock_model"] = req.bedrock_model
    if req.zai_model is not None: payload["zai_model"] = req.zai_model
    if req.omnirouter_model is not None: payload["omnirouter_model"] = req.omnirouter_model
    if req.nvidia_model is not None: payload["nvidia_model"] = req.nvidia_model
    if req.groq_api_key is not None: payload["groq_api_key"] = req.groq_api_key
    if req.deepseek_api_key is not None: payload["deepseek_api_key"] = req.deepseek_api_key
    if req.together_api_key is not None: payload["together_api_key"] = req.together_api_key
    if req.mistral_api_key is not None: payload["mistral_api_key"] = req.mistral_api_key
    if req.cohere_api_key is not None: payload["cohere_api_key"] = req.cohere_api_key
    if req.xai_api_key is not None: payload["xai_api_key"] = req.xai_api_key
    if req.azure_api_key is not None: payload["azure_api_key"] = req.azure_api_key
    if req.zai_api_key is not None: payload["zai_api_key"] = req.zai_api_key
    if req.omnirouter_api_key is not None: payload["omnirouter_api_key"] = req.omnirouter_api_key
    if req.nvidia_api_key is not None: payload["nvidia_api_key"] = req.nvidia_api_key
    if req.azure_endpoint is not None: payload["azure_endpoint"] = req.azure_endpoint
    if req.azure_api_version is not None: payload["azure_api_version"] = req.azure_api_version
    if req.omnirouter_base_url is not None: payload["omnirouter_base_url"] = req.omnirouter_base_url
    if req.bedrock_region is not None: payload["bedrock_region"] = req.bedrock_region
    if req.approval_mode is not None: payload["approval_mode"] = req.approval_mode
    if req.coder_provider is not None: payload["coder_provider"] = req.coder_provider
    if req.coder_cli_command is not None: payload["coder_cli_command"] = req.coder_cli_command
    if req.semantic_cache is not None: payload["semantic_cache"] = req.semantic_cache
    # Network settings
    if req.network_port is not None: payload["network_port"] = req.network_port
    if req.network_host is not None: payload["network_host"] = req.network_host
    if req.network_cors_origins is not None: payload["network_cors_origins"] = req.network_cors_origins
    # Free Tier Quota Pacing settings
    if req.enable_free_limit is not None: payload["enable_free_limit"] = req.enable_free_limit
    if req.free_limit_rpm is not None: payload["free_limit_rpm"] = req.free_limit_rpm
    
    database.update_db_settings(payload)
    return {"status": "updated"}

# --- PREMIUM UPGRADE ENDPOINTS ---

DEFAULT_PERSONA_PROMPTS = {
    "orchestrator": "You are the central Orchestrator Supervisor. Your task is to coordinate a team of developer agents.",
    "analyst": "You are an expert Business Analyst.\nAnalyze the following request and detail the user requirements, criteria, and edge cases.",
    "impact": "You are a Software Architect and Impact Analyzer.\nCompare the new requirements against the existing codebase files. Determine which files are affected, what new files must be created, and any risks or dependency issues.",
    "programmer": "You are a senior Software Implementation Engineer.\nYour task is to write clean, operational, and well-commented code files according to the requirements and impact plan.\nWrite the complete code for each target file. Do not use placeholders or skip details.",
    "deployer": "You are a DevOps and Deployment Engineer.\nFor the application built under these requirements, write:\n1. A local deployment script:\n   - On Windows systems, write a `deploy.bat` file.\n   - For other platforms, write a `deploy.sh` script or a python script `deploy.py`.\n2. A CI/CD Pipeline configuration file:\n   - Generate an Azure DevOps pipeline config (`azure-pipelines.yml`) to support Azure DevOps/TFS.\n   - Also generate a GitHub Actions workflow (`.github/workflows/ci.yml`) to support GitHub repository pipelines.\n   - Both pipelines should be configured to install dependencies, run linting/compilation checks, execute your unit tests, and trigger static security/vulnerability scans (e.g. Bandit for Python)."
}

class UpdatePromptsRequest(BaseModel):
    orchestrator: Optional[str] = ""
    analyst: Optional[str] = ""
    impact: Optional[str] = ""
    programmer: Optional[str] = ""
    deployer: Optional[str] = ""

@app.get("/api/settings/prompts")
def get_prompts_endpoint():
    res = dict(DEFAULT_PERSONA_PROMPTS)
    workspace = database.get_active_workspace()
    config_path = os.path.join(workspace, ".studio", "prompts.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for k, v in saved.items():
                    if v and str(v).strip():
                        res[k] = v
        except Exception:
            pass
    return res

@app.post("/api/settings/prompts")
def update_prompts_endpoint(req: UpdatePromptsRequest):
    workspace = database.get_active_workspace()
    studio_dir = os.path.join(workspace, ".studio")
    if not os.path.exists(studio_dir):
        os.makedirs(studio_dir)
    config_path = os.path.join(studio_dir, "prompts.json")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({
                "orchestrator": req.orchestrator,
                "analyst": req.analyst,
                "impact": req.impact,
                "programmer": req.programmer,
                "deployer": req.deployer
            }, f, indent=4)
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save custom prompts: {str(e)}")

@app.get("/api/cache/list")
def list_cache_endpoint():
    return database.get_all_semantic_cache()

@app.delete("/api/cache/delete/{item_id}")
def delete_cache_item_endpoint(item_id: int):
    try:
        database.delete_semantic_cache_item(item_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/clear")
def clear_cache_endpoint():
    try:
        database.clear_semantic_cache()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telemetry")
def get_telemetry_endpoint():
    try:
        return database.get_telemetry_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telemetry/reset")
def reset_telemetry_endpoint():
    try:
        database.reset_telemetry_logs()
        return {"status": "reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telemetry/export")
def export_telemetry_endpoint():
    try:
        logs = database.get_all_telemetry_logs()
        return {"count": len(logs), "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/git/branches")
def list_git_branches():
    workspace = database.get_active_workspace()
    if not os.path.exists(os.path.join(workspace, ".git")):
        return {"branches": [], "active": ""}
    try:
        import subprocess
        res = subprocess.run(
            ["git", "branch", "--no-color"],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        branches = []
        active = ""
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("*"):
                active = line.replace("*", "").strip()
                branches.append(active)
            else:
                branches.append(line)
        return {"branches": branches, "active": active}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git Error: {str(e)}")

class CreateBranchRequest(BaseModel):
    name: str

@app.post("/api/git/branch/create")
def create_git_branch(req: CreateBranchRequest):
    workspace = database.get_active_workspace()
    if not os.path.exists(os.path.join(workspace, ".git")):
        raise HTTPException(status_code=400, detail="Not a git repository.")
    try:
        import subprocess
        subprocess.run(
            ["git", "checkout", "-b", req.name],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return {"status": "created", "branch": req.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git Checkout Error: {str(e)}")

class SwitchBranchRequest(BaseModel):
    name: str

@app.post("/api/git/branch/switch")
def switch_git_branch(req: SwitchBranchRequest):
    workspace = database.get_active_workspace()
    if not os.path.exists(os.path.join(workspace, ".git")):
        raise HTTPException(status_code=400, detail="Not a git repository.")
    try:
        import subprocess
        subprocess.run(
            ["git", "checkout", req.name],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return {"status": "switched", "branch": req.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git Switch Error: {str(e)}")

class RollbackRequest(BaseModel):
    commit: str

@app.post("/api/git/rollback")
def git_rollback(req: RollbackRequest):
    workspace = database.get_active_workspace()
    if not os.path.exists(os.path.join(workspace, ".git")):
        raise HTTPException(status_code=400, detail="Not a git repository.")
    try:
        import subprocess
        subprocess.run(
            ["git", "reset", "--hard", req.commit],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return {"status": "rolled_back", "commit": req.commit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Git Rollback Error: {str(e)}")

# Pure Python Background PowerShell PTY Emulation for Xterm.js
import queue
import subprocess

class TerminalManager:
    def __init__(self):
        self.proc = None
        self.output_queue = queue.Queue()
        self.thread = None
        self.active = False
        
    def start(self, initial_cwd: str = None):
        if self.active:
            self.stop()
        try:
            cwd = initial_cwd or os.getcwd()
            self.proc = subprocess.Popen(
                ["powershell.exe", "-NoLogo", "-NoExit"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                text=True,
                bufsize=0
            )
            self.active = True
            self.thread = threading.Thread(target=self._read_output, daemon=True)
            self.thread.start()
            print(f"[Terminal] Persistent PowerShell session started in: {cwd}")
        except Exception as e:
            print(f"[Terminal] Failed to start PowerShell: {str(e)}")

    def _read_output(self):
        while self.active and self.proc:
            try:
                char = self.proc.stdout.read(1)
                if not char:
                    break
                self.output_queue.put(char)
            except Exception:
                break
            
    def write(self, data: str):
        if self.active and self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(data)
                self.proc.stdin.flush()
            except Exception as e:
                print(f"[Terminal] Write failed: {str(e)}")
                
    def read_all(self) -> str:
        data = []
        while not self.output_queue.empty():
            try:
                data.append(self.output_queue.get_nowait())
            except queue.Empty:
                break
        return "".join(data)

    def stop(self):
        self.active = False
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except Exception:
                pass
            self.proc = None
        print("[Terminal] PowerShell session stopped.")

terminal_manager = TerminalManager()

class TerminalWriteRequest(BaseModel):
    data: str

@app.post("/api/terminal/write")
def write_terminal(req: TerminalWriteRequest):
    terminal_manager.write(req.data)
    return {"status": "ok"}

@app.get("/api/terminal/read")
def read_terminal():
    return {"data": terminal_manager.read_all()}

# Pure Python Background PowerShell PTY Emulation for Xterm.js
import queue
import subprocess
import logging
from contextlib import asynccontextmanager

# Configure logging filter to prevent high-frequency terminal polling log spam
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/terminal/read" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

class TerminalManager:
    def __init__(self):
        self.proc = None
        self.output_queue = queue.Queue()
        self.thread = None
        self.active = False
        
    def start(self, initial_cwd: str = None):
        if self.active:
            self.stop()
        try:
            cwd = initial_cwd or os.getcwd()
            self.proc = subprocess.Popen(
                ["powershell.exe", "-NoLogo", "-NoExit"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                text=True,
                bufsize=0
            )
            self.active = True
            self.thread = threading.Thread(target=self._read_output, daemon=True)
            self.thread.start()
            print(f"[Terminal] Persistent PowerShell session started in: {cwd}")
        except Exception as e:
            print(f"[Terminal] Failed to start PowerShell: {str(e)}")

    def _read_output(self):
        while self.active and self.proc:
            try:
                char = self.proc.stdout.read(1)
                if not char:
                    break
                self.output_queue.put(char)
            except Exception:
                break
            
    def write(self, data: str):
        if self.active and self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(data)
                self.proc.stdin.flush()
            except Exception as e:
                print(f"[Terminal] Write failed: {str(e)}")
                
    def read_all(self) -> str:
        data = []
        while not self.output_queue.empty():
            try:
                data.append(self.output_queue.get_nowait())
            except queue.Empty:
                break
        return "".join(data)

    def stop(self):
        self.active = False
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except Exception:
                pass
            self.proc = None
        print("[Terminal] PowerShell session stopped.")

terminal_manager = TerminalManager()

class TerminalWriteRequest(BaseModel):
    data: str

@app.post("/api/terminal/write")
def write_terminal(req: TerminalWriteRequest):
    terminal_manager.write(req.data)
    return {"status": "ok"}

@app.get("/api/terminal/read")
def read_terminal():
    return {"data": terminal_manager.read_all()}

# Register modern lifespan event handlers
@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    import database
    try:
        workspace_dir = database.get_active_workspace()
    except Exception:
        workspace_dir = None
    terminal_manager.start(workspace_dir)
    yield
    terminal_manager.stop()

app.router.lifespan_context = lifespan_handler

# Serve static frontend (index.html at root)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Read network settings from DB (falls back to defaults if not set)
    try:
        import database as _db
        _net = _db.get_all_settings()
        _port = int(_net.get("network_port", 8000))
        _host = _net.get("network_host", "0.0.0.0")
        if not (1024 <= _port <= 65535):
            _port = 8000
        if _host not in ("0.0.0.0", "127.0.0.1"):
            _host = "0.0.0.0"
    except Exception:
        _port = 8000
        _host = "0.0.0.0"
    print(f"Starting Multi-Agent Developer Studio Server on http://localhost:{_port}...")
    uvicorn.run("app:app", host=_host, port=_port, reload=False)
