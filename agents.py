import os
import json
import re
import threading
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Global variables for Web-based Human-in-the-Loop event synchronization
web_mode = False
approval_event = threading.Event()
pause_event = threading.Event()
pause_event.set() # Default to running (not paused)
is_thread_paused = False
pending_approval_stage = ""
pending_approval_text = ""
web_feedback = ""
active_agent_name = "idle"
active_history_id = None

def check_pause():
    global pause_event, is_thread_paused
    if not pause_event.is_set():
        is_thread_paused = True
        print("\n⏸️ [Execution Paused] Waiting for Play/Resume trigger...")
        pause_event.wait()
        is_thread_paused = False


# Load environment variables
load_dotenv()

def get_llm():
    """
    Initializes and returns the appropriate LLM client based on environment configuration.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise ValueError(
                "GEMINI_API_KEY is not set in environment or .env file.\n"
                "Please configure your API keys in C:\\PERSONAL DATA\\2.POC\\AGENTS\\.env"
            )
        from langchain_google_genai import ChatGoogleGenerativeAI
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=gemini_key,
            temperature=0.2
        )
    elif provider == "openai":
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError(
                "OPENAI_API_KEY is not set in environment or .env file.\n"
                "Please configure your API keys in C:\\PERSONAL DATA\\2.POC\\AGENTS\\.env"
            )
        from langchain_openai import ChatOpenAI
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return ChatOpenAI(
            model=model_name,
            api_key=openai_key,
            temperature=0.2
        )
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        model_name = os.getenv("OLLAMA_MODEL", "llama3")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=0.2
        )
    elif provider == "claude" or provider == "anthropic":
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set in environment or .env file.\n"
                "Please configure your API keys in C:\\PERSONAL DATA\\2.POC\\AGENTS\\.env"
            )
        from langchain_anthropic import ChatAnthropic
        model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        return ChatAnthropic(
            model=model_name,
            api_key=anthropic_key,
            temperature=0.2
        )
    elif provider == "openrouter":
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set in environment.\n"
                "Please configure your OpenRouter API key in settings."
            )
        from langchain_openai import ChatOpenAI
        model_name = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=openrouter_key,
            openai_api_base=base_url,
            max_tokens=4096,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Multi-Agent Developer Studio",
            },
            temperature=0.2
        )
    elif provider == "groq":
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("GROQ_API_KEY is not set in environment or settings.")
        from langchain_groq import ChatGroq
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-specdec")
        return ChatGroq(
            model=model_name,
            api_key=groq_key,
            temperature=0.2
        )
    elif provider == "deepseek":
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_key:
            raise ValueError("DEEPSEEK_API_KEY is not set in environment or settings.")
        from langchain_openai import ChatOpenAI
        model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=deepseek_key,
            openai_api_base="https://api.deepseek.com/v1",
            temperature=0.2
        )
    elif provider == "together":
        together_key = os.getenv("TOGETHER_API_KEY")
        if not together_key:
            raise ValueError("TOGETHER_API_KEY is not set in environment or settings.")
        from langchain_openai import ChatOpenAI
        model_name = os.getenv("TOGETHER_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=together_key,
            openai_api_base="https://api.together.xyz/v1",
            temperature=0.2
        )
    elif provider == "mistral":
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if not mistral_key:
            raise ValueError("MISTRAL_API_KEY is not set in environment or settings.")
        from langchain_mistralai import ChatMistralAI
        model_name = os.getenv("MISTRAL_MODEL", "codestral-latest")
        return ChatMistralAI(
            model=model_name,
            api_key=mistral_key,
            temperature=0.2
        )
    elif provider == "cohere":
        cohere_key = os.getenv("COHERE_API_KEY")
        if not cohere_key:
            raise ValueError("COHERE_API_KEY is not set in environment or settings.")
        from langchain_cohere import ChatCohere
        model_name = os.getenv("COHERE_MODEL", "command-r-plus")
        return ChatCohere(
            model=model_name,
            api_key=cohere_key,
            temperature=0.2
        )
    elif provider == "xai":
        xai_key = os.getenv("XAI_API_KEY")
        if not xai_key:
            raise ValueError("XAI_API_KEY is not set in environment or settings.")
        from langchain_openai import ChatOpenAI
        model_name = os.getenv("XAI_MODEL", "grok-2")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=xai_key,
            openai_api_base="https://api.x.ai/v1",
            temperature=0.2
        )
    elif provider == "azure":
        azure_key = os.getenv("AZURE_API_KEY")
        azure_endpoint = os.getenv("AZURE_ENDPOINT")
        azure_api_version = os.getenv("AZURE_API_VERSION", "2024-08-01-preview")
        if not azure_key or not azure_endpoint:
            raise ValueError("AZURE_API_KEY and AZURE_ENDPOINT must be set in settings.")
        from langchain_openai import AzureChatOpenAI
        model_name = os.getenv("AZURE_MODEL", "gpt-4o")
        return AzureChatOpenAI(
            deployment_name=model_name,
            openai_api_key=azure_key,
            azure_endpoint=azure_endpoint,
            api_version=azure_api_version,
            temperature=0.2
        )
    elif provider == "bedrock":
        from langchain_aws import ChatBedrock
        model_name = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20240620-v1:0")
        region_name = os.getenv("BEDROCK_REGION", "us-east-1")
        return ChatBedrock(
            model_id=model_name,
            region_name=region_name,
            temperature=0.2
        )
    elif provider == "zai":
        zai_key = os.getenv("ZAI_API_KEY")
        if not zai_key:
            raise ValueError("ZAI_API_KEY is not set in settings.")
        from langchain_openai import ChatOpenAI
        model_name = os.getenv("ZAI_MODEL", "glm-4-flash")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=zai_key,
            openai_api_base="https://api.z.ai/api/paas/v4/",
            temperature=0.2
        )
    elif provider == "omnirouter":
        omnirouter_key = os.getenv("OMNIROUTER_API_KEY")
        from langchain_openai import ChatOpenAI
        model_name = os.getenv("OMNIROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
        base_url = os.getenv("OMNIROUTER_BASE_URL", "http://localhost:20128/v1")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=omnirouter_key or "no-key",
            openai_api_base=base_url,
            temperature=0.2
        )
    elif provider == "nvidia":
        nvidia_key = os.getenv("NVIDIA_API_KEY")
        if not nvidia_key:
            raise ValueError("NVIDIA_API_KEY is not set in settings.")
        from langchain_openai import ChatOpenAI
        model_name = os.getenv("NVIDIA_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")
        return ChatOpenAI(
            model=model_name,
            openai_api_key=nvidia_key,
            openai_api_base="https://integrate.api.nvidia.com/v1",
            temperature=0.2
        )
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'."
        )

class CachedResponse:
    def __init__(self, content: str):
        self.content = content
    def __str__(self):
        return self.content

def get_model_name_for_provider(provider: str) -> str:
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    elif provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    elif provider == "ollama":
        return os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    elif provider == "claude" or provider == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    elif provider == "openrouter":
        return os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    elif provider == "groq":
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-specdec")
    elif provider == "deepseek":
        return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    elif provider == "together":
        return os.getenv("TOGETHER_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")
    elif provider == "mistral":
        return os.getenv("MISTRAL_MODEL", "codestral-latest")
    elif provider == "cohere":
        return os.getenv("COHERE_MODEL", "command-r-plus")
    elif provider == "xai":
        return os.getenv("XAI_MODEL", "grok-2")
    elif provider == "azure":
        return os.getenv("AZURE_MODEL", "gpt-4o")
    elif provider == "bedrock":
        return os.getenv("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    elif provider == "zai":
        return os.getenv("ZAI_MODEL", "glm-4-flash")
    elif provider == "omnirouter":
        return os.getenv("OMNIROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
    elif provider == "nvidia":
        return os.getenv("NVIDIA_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")
    return "unknown"

import threading

_last_llm_call_timestamp = 0.0
_llm_call_lock = threading.Lock()

def invoke_llm(llm, prompt: str, bypass_cache: bool = False) -> str:
    """
    Invokes the LLM with semantic caching if enabled, and records telemetry.
    Supports Free Tier Quota Pacing (RPM rate limiter) if enabled in settings.
    """
    import database
    import semantic_cache_engine
    import time
    global _last_llm_call_timestamp, _llm_call_lock
    
    global active_agent_name, active_history_id
    current_agent = active_agent_name or "idle"
    
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    model_name = get_model_name_for_provider(provider)
    
    settings = database.get_all_settings()
    is_cache_enabled = settings.get("semantic_cache", "true") == "true" and not bypass_cache
    
    if is_cache_enabled:
        cached_res = semantic_cache_engine.check_cache_hit(prompt, provider, model_name)
        if cached_res:
            try:
                database.insert_telemetry_log(
                    agent_name=current_agent,
                    provider=f"{provider} (cached)",
                    model=model_name,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_sec=0.01,
                    cost_usd=0.0,
                    prompt_text=prompt,
                    response_text=cached_res,
                    history_id=active_history_id
                )
            except Exception as e:
                print(f"[Telemetry Warning] Failed to log cached hit: {e}")
            return CachedResponse(cached_res)
            
    # Free Tier Quota Pacing & Rate Limiting
    is_free_limit = settings.get("enable_free_limit", "false") == "true"
    if is_free_limit:
        try:
            rpm = int(settings.get("free_limit_rpm", "15"))
        except Exception:
            rpm = 15
        rpm = max(rpm, 1)
        min_interval = 60.0 / rpm
        with _llm_call_lock:
            now = time.time()
            elapsed = now - _last_llm_call_timestamp
            if elapsed < min_interval:
                wait_sec = min_interval - elapsed
                print(f"[Free Tier Rate Limiter ⏳] Enforcing {rpm} RPM limit for {provider}. Pacing request with {wait_sec:.2f}s delay...")
                time.sleep(wait_sec)
            _last_llm_call_timestamp = time.time()
            
    max_attempts = 4 if is_free_limit else 1
    response = None
    start_time = time.time()
    
    for attempt in range(max_attempts):
        try:
            response = llm.invoke(prompt)
            latency = time.time() - start_time
            if is_free_limit:
                with _llm_call_lock:
                    _last_llm_call_timestamp = time.time()
            break
        except Exception as err:
            err_msg = str(err)
            is_rate_limit = any(term in err_msg.lower() for term in ["429", "resourceexhausted", "rate limit", "quota", "too many requests"])
            if is_rate_limit and attempt < max_attempts - 1:
                backoff_sec = (attempt + 1) * 6.0 + 4.0  # 10s, 16s, 22s
                print(f"[Free Tier Rate Limiter ⚠️] Quota / Rate limit (429) hit: {err_msg[:100]}...\n[Free Tier Rate Limiter ⏳] Retrying attempt {attempt+2}/{max_attempts} after {backoff_sec:.1f}s backoff...")
                time.sleep(backoff_sec)
                with _llm_call_lock:
                    _last_llm_call_timestamp = time.time()
            else:
                raise err

    
    response_content = ""
    if hasattr(response, "content"):
        response_content = response.content
    else:
        response_content = str(response)
        
    if is_cache_enabled and response_content:
        semantic_cache_engine.save_cache_entry(prompt, provider, model_name, response_content)
        
    # Telemetry data extraction
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    
    try:
        if hasattr(response, "response_metadata") and response.response_metadata:
            meta = response.response_metadata
            if "usage_metadata" in meta:
                usage = meta["usage_metadata"]
                prompt_tokens = usage.get("prompt_token_count", 0)
                completion_tokens = usage.get("candidates_token_count", 0)
                total_tokens = usage.get("total_token_count", 0)
            elif "token_usage" in meta:
                usage = meta["token_usage"]
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
            elif "usage" in meta:
                usage = meta["usage"]
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
    except Exception as e:
        print(f"[Telemetry Warning] Failed to parse LangChain token usage: {e}")
        
    if total_tokens == 0:
        # Fallback character estimation (1 token approx 4 chars)
        prompt_tokens = max(1, len(prompt) // 4)
        completion_tokens = max(1, len(response_content) // 4)
        total_tokens = prompt_tokens + completion_tokens
        
    cost = 0.0
    model_lower = model_name.lower()
    
    if "gemini-2.5" in model_lower:
        cost = (prompt_tokens * 0.075 / 1000000.0) + (completion_tokens * 0.30 / 1000000.0)
    elif "gpt-4o-mini" in model_lower:
        cost = (prompt_tokens * 0.150 / 1000000.0) + (completion_tokens * 0.60 / 1000000.0)
    elif "gpt-4o" in model_lower:
        cost = (prompt_tokens * 2.50 / 1000000.0) + (completion_tokens * 10.00 / 1000000.0)
    elif "claude-3-5" in model_lower:
        cost = (prompt_tokens * 3.00 / 1000000.0) + (completion_tokens * 15.00 / 1000000.0)
    elif "llama-3.3" in model_lower or "llama3.3" in model_lower:
        cost = (prompt_tokens * 0.20 / 1000000.0) + (completion_tokens * 0.40 / 1000000.0)
    elif "deepseek" in model_lower:
        cost = (prompt_tokens * 0.14 / 1000000.0) + (completion_tokens * 0.28 / 1000000.0)
    elif provider == "ollama":
        cost = 0.0
    else:
        cost = (prompt_tokens * 0.15 / 1000000.0) + (completion_tokens * 0.60 / 1000000.0)
        
    try:
        database.insert_telemetry_log(
            agent_name=current_agent,
            provider=provider,
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_sec=round(latency, 2),
            cost_usd=round(cost, 6),
            prompt_text=prompt,
            response_text=response_content,
            history_id=active_history_id
        )
    except Exception as e:
        print(f"[Telemetry Error] Failed to write SQL log: {e}")
        
    return response

# ----------------- PARSING HELPERS -----------------

def parse_orchestrator_decision(text: str) -> Tuple[str, str]:
    """
    Parses the Orchestrator's ReAct decision (Thought + Next Agent Action).
    """
    thought = ""
    match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            thought = data.get("thought", "").strip()
            decision = data.get("next_agent", "").strip()
            if decision in ["BusinessAnalyst", "ImpactAnalyzer", "ImplementEngineer", "Tester", "Deployer", "FINISH"]:
                return decision, thought
        except Exception:
            pass
            
    for agent in ["BusinessAnalyst", "ImpactAnalyzer", "ImplementEngineer", "Tester", "Deployer", "FINISH"]:
        if re.search(rf"\b{agent}\b", text, re.IGNORECASE):
            return agent, thought
            
    return "BusinessAnalyst", thought

def parse_impact_files(text: str) -> List[str]:
    """
    Parses the JSON list of files to modify returned by the Impact Analyzer.
    """
    match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return data.get("files", [])
        except Exception:
            pass
    files = re.findall(r'"([a-zA-Z0-9_\-\./]+)"', text)
    if files:
        files = [f for f in files if f != "files" and "." in f]
        return list(set(files))
    return []

# ----------------- DYNAMIC CONTEXT HELPERS -----------------

def truncate_context(text: str, max_chars: int = 8000) -> str:
    """
    Context Engineering Helper: Truncates oversized text blocks to fit LLM context limits.
    Preserves top and bottom windows of the file/log content.
    """
    if not text or len(text) <= max_chars:
        return text
    half = max_chars // 2
    return f"{text[:half]}\n\n... [Middle content truncated for Context Window Optimization (Original Size: {len(text)} chars)] ...\n\n{text[-half:]}"

def get_relevant_contents(codebase_metadata: dict, prompt: str) -> str:
    """
    Queries and reads the contents of workspace files that are relevant to the user prompt.
    Prevents loading the entire codebase into the LLM context window.
    """
    from utils import read_workspace_file
    from database import get_active_workspace
    workspace_dir = get_active_workspace()
    
    relevant_files = []
    # Extract alpha-numeric words as potential keywords
    keywords = re.findall(r'[a-zA-Z0-9_\-\.]+', prompt.lower())
    
    for filepath in codebase_metadata.keys():
        basename = os.path.basename(filepath).lower()
        # Check if file matches query terms (longer than 3 chars)
        if any(kw in filepath.lower() or kw in basename for kw in keywords if len(kw) > 3):
            relevant_files.append(filepath)

    # Symbol Index Resolution (Function & Class symbol matching)
    try:
        from ast_engine import EnterpriseASTEngine
        sym_index = EnterpriseASTEngine.get_workspace_symbol_index(workspace_dir)
        for kw in keywords:
            if len(kw) > 3:
                for fn_name, fn_info in sym_index.get("functions", {}).items():
                    if kw in fn_name.lower() and fn_info.get("file") in codebase_metadata:
                        relevant_files.append(fn_info["file"])
                for cls_name, cls_info in sym_index.get("classes", {}).items():
                    if kw in cls_name.lower() and cls_info.get("file") in codebase_metadata:
                        relevant_files.append(cls_info["file"])
    except Exception:
        pass

    # Enterprise Codebase RAG Vector Semantic Search
    try:
        from rag_engine import CodebaseRAGEngine
        from database import get_setting
        provider = get_setting("llm_provider", "google")
        rag_matches = CodebaseRAGEngine.search_codebase_rag(workspace_dir, prompt, top_k=4, provider=provider)
        for match in rag_matches:
            if match.get("filepath") in codebase_metadata:
                relevant_files.append(match["filepath"])
    except Exception as e:
        print(f"[RAG Retrieval Warning] {e}")
            
    # Deduplicate while preserving order & cap to max 6 files
    seen = set()
    relevant_files = [f for f in relevant_files if not (f in seen or seen.add(f))][:6]
            
    # Fallback: if no files match but codebase has files, fetch up to 4 files to provide context
    if not relevant_files and codebase_metadata:
        relevant_files = list(codebase_metadata.keys())[:4]
        
    result = ""
    for filename in relevant_files:
        content = read_workspace_file(workspace_dir, filename)
        truncated = truncate_context(content, max_chars=8000)
        result += f"\n---FILE: {filename}---\n{truncated}\n"
        
    return result

def get_target_files_contents(files_to_modify: List[str]) -> str:
    """
    Retrieves the actual contents of the target files slated for modification.
    Includes AST Symbol Outline and applies context window truncation if files are large.
    """
    from utils import read_workspace_file
    from database import get_active_workspace
    from ast_engine import EnterpriseASTEngine
    workspace_dir = get_active_workspace()
    
    result = ""
    for filename in files_to_modify:
        content = read_workspace_file(workspace_dir, filename)
        outline = EnterpriseASTEngine.generate_file_symbol_outline(filename, content)
        truncated = truncate_context(content, max_chars=12000)
        outline_str = f"[{outline}]\n" if outline else ""
        result += f"\n---FILE: {filename}---\n{outline_str}```python\n{truncated}\n```\n"
    return result

def ask_user_approval(stage: str, plan_text: str) -> str:
    """
    Interactive checkpoint for Human-in-the-Loop approvals.
    Supports console inputs, automated testing bypass, and FastAPI web event locks.
    """
    import database
    settings = database.get_all_settings()
    approval_mode = settings.get("approval_mode", "strict")
    
    # Auto-approve mode bypasses all checkpoints
    if approval_mode == "auto":
        print(f"[Approval Gate] Mode 'auto': Automatically approving stage '{stage}'.")
        return ""
        
    # Limited mode only asks for Business Analyst & Deployment stages
    if approval_mode == "limited" and stage not in ["Business Analyst Specifications", "Deployment Plan & Approval"]:
        print(f"[Approval Gate] Mode 'limited': Auto-approving stage '{stage}'.")
        return ""

    if os.getenv("STUDIO_AUTO_APPROVE", "false").lower() == "true":
        print(f"[Approval Gate] Automated mode active. Auto-approving stage '{stage}'.")
        return ""

    print(f"\n==================== [HUMAN-IN-THE-LOOP APPROVAL REQUIRED] ====================")
    print(f"Stage: {stage}")
    print("--------------------------------------------------------------------------------")
    print(plan_text)
    print("================================================================================")
    
    # Web Event Lock for FastAPI UI
    global pending_approval_event, pending_approval_data
    with approval_lock:
        pending_approval_data = {
            "stage": stage,
            "plan_text": plan_text,
            "user_response": None
        }
        pending_approval_event.clear()
        
    print("[Approval Gate] Waiting for user approval via Web UI or Terminal...")
    pending_approval_event.wait()
    
    with approval_lock:
        user_input = pending_approval_data["user_response"]
        pending_approval_data = None
        
    if not user_input or user_input.strip().lower() in ["y", "yes", "approve", "ok", ""]:
        print("[Approval Gate] Stage Approved! Continuing execution...\n")
        return ""
    else:
        print(f"[Approval Gate] Rejection/Feedback received: '{user_input}'\n")
        return user_input.strip()

# ----------------- PROMPT CONFIGURATION OVERRIDES -----------------

def load_custom_prompts() -> dict:
    """
    Loads custom agent persona prompts from .studio/prompts.json if it exists.
    """
    from database import get_active_workspace
    workspace = get_active_workspace()
    config_path = os.path.join(workspace, ".studio", "prompts.json")
    if os.path.exists(config_path):
        try:
            if os.path.getsize(config_path) == 0:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write("{}")
                return {}
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Prompts Config Warning] Failed to parse custom prompts: {e}")
    return {}

# ----------------- AGENT NODES -----------------

def orchestrator_node(state: dict) -> dict:
    """
    Orchestrator Agent Node.
    """
    global active_agent_name
    active_agent_name = "orchestrator"
    check_pause()
    print("\n[Orchestrator] Analyzing system state and selecting next step...")
    llm = get_llm()
    
    codebase_files = list(state.get("codebase", {}).keys())
    files_str = ", ".join(codebase_files) if codebase_files else "None (Empty Repository)"
    
    custom_prompts = load_custom_prompts()
    default_orchestrator = "You are the central Orchestrator Supervisor. Your task is to coordinate a team of developer agents."
    orchestrator_header = (custom_prompts.get("orchestrator") or "").strip() or default_orchestrator
    
    prompt = f"""{orchestrator_header}
Analyze the current state below and decide which agent should be invoked next.

Available Agents:
* 'BusinessAnalyst': Analyzes requirement prompt and writes detailed specifications.
* 'ImpactAnalyzer': Inspects the codebase, identifies which files are affected, and makes a plan.
* 'ImplementEngineer': Writes/updates files on disk based on the plan, or fixes syntax/testing bugs.
* 'Tester': Runs local compilation check, unit tests, security audits, and reports results.
* 'Deployer': Executes docker-compose or custom deploy scripts.
* 'FINISH': Call this when the task is fully completed.

Routing Guidelines (Prioritize Explicit User Command Overrides):
1. If the user prompt explicitly requests to ONLY write specifications, analyze requirements, or do business analysis (e.g. 'write requirements for X', 'do business analysis', 'write specifications only'), route to 'BusinessAnalyst'. Once the BA outputs the specification, route to 'FINISH'.
2. If the user prompt explicitly requests to ONLY perform impact analysis, assess risks, or plan file modifications (e.g. 'do impact analysis only', 'analyze impact of X'), route to 'ImpactAnalyzer'. Once completed, route to 'FINISH'.
3. If the user prompt explicitly requests to ONLY write code, execute direct coding, or implement (e.g. 'directly implement X', 'write code for Y', 'coder only'), route to 'ImplementEngineer' (bypassing BA/Impact steps). Once completed, route to 'Tester' to verify syntax/security, then to 'FINISH'.
4. If the user prompt explicitly requests to ONLY test or audit the codebase (e.g. 'test this project', 'run security check'), route to 'Tester'. Once completed, route to 'FINISH'.
5. If the user prompt explicitly requests to ONLY deploy the application (e.g. 'deploy this project', 'run deployment'), route to 'Tester' to verify code integrity, then to 'Deployer', then to 'FINISH'.
6. Otherwise, if it is a general new feature request or general requirement, follow the standard workflow step-by-step:
   - If 'Requirements Spec' is missing, route to 'BusinessAnalyst'.
   - If 'Requirements Spec' is established but 'Impact Spec' is missing, route to 'ImpactAnalyzer'.
   - If both specs are established but code has not been written (or Coder Iterations is 0), route to 'ImplementEngineer'.
   - If 'Errors' is not empty (contains compile, test, or security errors), route to 'ImplementEngineer' to fix them.
   - If code has been written and there are no active errors, route to 'Tester' to check.
   - If 'Tester' has run successfully (Validation Success is True or logs confirm tests passed) and there are no new errors on disk, DO NOT run 'Tester' or any previous steps. Route to 'Deployer'.
   - If 'Deployer' has successfully run, route to 'FINISH'.
7. Max Iterations Safeguard: If Coder Iterations is equal to or greater than Max Iterations, DO NOT route to 'ImplementEngineer'. Route to 'FINISH'.

Current Execution Logs / Context:
- If 'Errors' is not empty (contains compile, test, or security errors), ALWAYS route to 'ImplementEngineer' to fix the bugs (unless Max Iterations is reached).
- If 'Test Logs' show successful validation and 'Errors' is empty, progress to 'Deployer' (do not loop on 'Tester').

--- CURRENT STATE ---
User Prompt: {state.get('prompt')}
Requirements Spec: {"Established (Not Empty)" if state.get('requirements') else "Missing"}
Impact Spec: {"Established (Not Empty)" if state.get('impact_analysis') else "Missing"}
Codebase Files: {files_str}
Errors: {state.get('errors') or 'None'}
Test Logs: {state.get('test_results') or 'None'}
Deployment Logs: {state.get('deployment_logs') or 'None'}
Coder Iterations: {state.get('iterations', 0)}/{state.get('max_iterations', 3)}
---------------------

Based on this state, decide the next agent. Output your decision in this exact JSON format:
```json
{{
  "thought": "Reasoning explaining why this next agent is selected based on state and observations...",
  "next_agent": "BusinessAnalyst"
}}
```

Reasoning and Decision:"""
    
    check_pause()
    response = invoke_llm(llm, prompt, bypass_cache=True)
    check_pause()
    output = response.content if hasattr(response, 'content') else str(response)
    
    next_agent, thought = parse_orchestrator_decision(output)
    if thought:
        print(f"[ReAct Loop 🧠] Thought: {thought}")
    
    # Deterministic safeguard overrides to prevent loops
    if next_agent == "ImplementEngineer" and state.get("iterations", 0) >= int(state.get("max_iterations", 3)):
        print("[Orchestrator Safeguard] Max iterations reached. Overriding decision to 'FINISH' to prevent infinite coding loops.")
        next_agent = "FINISH"
        
    if next_agent == "BusinessAnalyst" and state.get("requirements"):
        prompt_lower = state.get("prompt", "").lower()
        if "spec" not in prompt_lower and "requirement" not in prompt_lower:
            if not state.get("impact_analysis"):
                print("[Orchestrator Safeguard] Requirements already established. Progressing to 'ImpactAnalyzer'.")
                next_agent = "ImpactAnalyzer"
            else:
                print("[Orchestrator Safeguard] Requirements already established. Progressing to 'ImplementEngineer'.")
                next_agent = "ImplementEngineer"
                
    print(f"[ReAct Loop ⚙️] Action -> {next_agent}")

    # Enterprise ReAct Trace Recorder
    try:
        from react_engine import EnterpriseReActEngine
        EnterpriseReActEngine.record_step(
            agent_name="orchestrator",
            thought=thought,
            action=next_agent,
            observation=f"Reqs: {'Yes' if state.get('requirements') else 'No'} | Impact: {'Yes' if state.get('impact_analysis') else 'No'} | Errors: {bool(state.get('errors'))}"
        )
    except Exception:
        pass
    
    if next_agent == "FINISH":
        from utils import clear_studio_state
        from database import get_active_workspace
        clear_studio_state(get_active_workspace())
        
    return {"next_agent": next_agent}

def business_analyst_node(state: dict) -> dict:
    """
    Business Analyst Agent Node.
    """
    global active_agent_name
    active_agent_name = "analyst"
    check_pause()
    print("\n[Business Analyst] Detailing specifications and criteria...")
    llm = get_llm()
    
    codebase_desc = ""
    if state.get("codebase"):
        codebase_desc = "Existing codebase contains these files:\n" + "\n".join([f"- {f}" for f in state["codebase"].keys()])
        
    custom_prompts = load_custom_prompts()
    default_analyst = "You are an expert Business Analyst.\nAnalyze the following request and detail the user requirements, criteria, and edge cases."
    analyst_header = (custom_prompts.get("analyst") or "").strip() or default_analyst
    
    prompt = f"""{analyst_header}
If there are existing files, consider how the request interacts with them.
Produce a clean Markdown requirements document including:
1. Functional Requirements
2. Acceptance Criteria
3. Test Scenarios (what QA needs to check)

Request:
{state['prompt']}

{codebase_desc}

Requirements Document:"""
    
    check_pause()
    response = invoke_llm(llm, prompt)
    check_pause()
    reqs = response.content if hasattr(response, 'content') else str(response)
    
    check_pause()
    feedback = ask_user_approval("Business Analyst Specifications", reqs)
    if feedback:
        print("[BA Gate] User rejected specifications. Re-routing back to Business Analyst...")
        return {
            "requirements": "",
            "prompt": f"{state.get('prompt')}\n\n[BA Revision Feedback]: {feedback}"
        }
    res = {"requirements": reqs}
    from utils import save_studio_state
    from database import get_active_workspace
    save_studio_state(get_active_workspace(), {**state, **res, "next_agent": "ImpactAnalyzer"})
    return res

def impact_analyzer_node(state: dict) -> dict:
    """
    Impact Analyzer Agent Node.
    """
    global active_agent_name
    active_agent_name = "impact"
    check_pause()
    print("\n[Impact Analyzer] Performing codebase impact and risk analysis...")
    llm = get_llm()
    
    # Smart Indexing: Read contents of only files relevant to the prompt
    relevant_contents = get_relevant_contents(state.get("codebase", {}), state.get("prompt", ""))
    
    codebase_desc = "The repository is currently empty."
    if state.get("codebase"):
        codebase_desc = f"Indexed Files in Workspace:\n"
        for name, meta in state["codebase"].items():
            codebase_desc += f"  - {name} ({meta['size']} bytes, {meta['lines']} lines)\n"
        codebase_desc += f"\nRelevant File Contents loaded dynamically:\n{relevant_contents}"

        # Enterprise AST Call Graph Engine
        try:
            from ast_engine import EnterpriseASTEngine
            from database import get_active_workspace
            call_graph = EnterpriseASTEngine.build_workspace_call_graph(get_active_workspace())
            if call_graph:
                graph_lines = [f"  - {src} depends on: {', '.join(deps)}" for src, deps in call_graph.items() if deps]
                if graph_lines:
                    codebase_desc += "\n\nAST Dependency Call Graph:\n" + "\n".join(graph_lines)
        except Exception:
            pass
            
    custom_prompts = load_custom_prompts()
    default_impact = "You are a Software Architect and Impact Analyzer.\nCompare the new requirements against the existing codebase files. Determine which files are affected, what new files must be created, and any risks or dependency issues."
    impact_header = (custom_prompts.get("impact") or "").strip() or default_impact
    
    prompt = f"""{impact_header}

Requirements:
{state['requirements']}

Existing Codebase:
{codebase_desc}

Provide:
1. Impact Analysis: What modules must be edited or created.
2. Risk Tolerance: Potential integration bugs or side effects.
3. List of files: Provide a list of relative file paths that the Implementer must write or edit.

At the very end of your response, you MUST output a JSON block listing the file paths:
```json
{{
  "files": ["file1.py", "subfolder/file2.js"]
}}
```

Impact Assessment:"""
    
    check_pause()
    response = invoke_llm(llm, prompt)
    check_pause()
    output = response.content if hasattr(response, 'content') else str(response)
    
    files_to_modify = parse_impact_files(output)
    print(f"[Impact Analyzer] Identified files to create/edit: {files_to_modify}")
    
    file_list_str = "\n".join([f"- {f}" for f in files_to_modify])
    plan_desc = f"{output}\n\nProposed Files to Create/Modify:\n{file_list_str}"
    
    # Enterprise Transitive Impact Radius Calculation
    try:
        from ast_engine import EnterpriseASTEngine
        from database import get_active_workspace
        impact_radius = EnterpriseASTEngine.calculate_impact_radius(get_active_workspace(), files_to_modify)
        if impact_radius.get("total_affected_files"):
            affected_str = ", ".join(impact_radius["total_affected_files"])
            print(f"[Impact Analyzer 🌐] Calculated Transitive Impact Radius ({impact_radius['impact_score']} downstream files affected): {affected_str}")
            plan_desc += f"\n\n🌐 Transitive Impact Blast Radius ({impact_radius['impact_score']} affected files):\n- Direct dependants: {', '.join(impact_radius['direct_dependants']) or 'None'}\n- Indirect dependants: {', '.join(impact_radius['indirect_dependants']) or 'None'}"
    except Exception as e:
        print(f"[Impact Radius Warning] {e}")
    
    check_pause()
    feedback = ask_user_approval("Impact & Code Modification Plan", plan_desc)
    if feedback:
        print("[Impact Gate] User rejected files plan. Re-routing back to Impact Analyzer...")
        return {
            "impact_analysis": "",
            "requirements": f"{state.get('requirements')}\n\n[Impact Revision Feedback]: {feedback}"
        }
        
    res = {
        "impact_analysis": output,
        "files_to_modify": files_to_modify
    }
    from utils import save_studio_state
    from database import get_active_workspace
    save_studio_state(get_active_workspace(), {**state, **res, "next_agent": "ImplementEngineer"})
    return res

def implement_engineer_node(state: dict) -> dict:
    """
    Implement Engineer (Coder) Agent Node.
    """
    global active_agent_name
    active_agent_name = "programmer"
    check_pause()
    print(f"\n[Implement Engineer] Writing/Updating code (Iteration {state['iterations'] + 1})...")
    
    import database
    settings = database.get_all_settings()
    coder_provider = settings.get("coder_provider", "llm")
    files_list = state.get("files_to_modify") or []
    
    if coder_provider == "cli":
        print("\n[Implement Engineer] Provider configured to CLI. Invoking custom coding agent CLI...")
        import subprocess
        workspace_dir = database.get_active_workspace()
        
        # Ensure .studio folder exists in workspace
        os.makedirs(os.path.join(workspace_dir, ".studio"), exist_ok=True)
        prompt_txt_path = os.path.join(workspace_dir, ".studio", "prompt.txt")
        
        reqs = state.get("requirements", "")
        cli_prompt = f"Implement these requirements: {reqs}\nFiles to modify: {', '.join(files_list)}"
        if state.get("errors"):
            cli_prompt += f"\nFix these errors/bugs from the previous test run:\n{state.get('errors')}"
            
        # Write prompt to file to support {prompt_file} safely
        with open(prompt_txt_path, "w", encoding="utf-8") as f:
            f.write(cli_prompt)
            
        # Get custom command template
        cli_cmd_template = settings.get("coder_cli_command") or 'agy run "{prompt}"'
        
        # Replace placeholders
        relative_prompt_file = os.path.join(".studio", "prompt.txt")
        cmd_str = cli_cmd_template.replace("{prompt_file}", relative_prompt_file)
        
        # Replace {prompt} with simple escaping
        escaped_prompt = cli_prompt.replace('"', '\\"')
        cmd_str = cmd_str.replace("{prompt}", escaped_prompt)
        
        print(f"[CLI Coder] Executing command in workspace: {cmd_str}")
        try:
            result = subprocess.run(
                cmd_str,
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                shell=True
            )
            success = (result.returncode == 0)
            cli_errors = "" if success else result.stderr or result.stdout
            if not success:
                print(f"[CLI Coder Warning] Coder CLI exited with code {result.returncode}. Output:\n{cli_errors}")
        except Exception as e:
            print(f"[CLI Coder Error] Failed to launch custom CLI command: {e}")
            success = False
            cli_errors = f"Failed to execute CLI: {str(e)}"
            
        from utils import scan_workspace
        updated_metadata = scan_workspace(workspace_dir)
        res = {
            "codebase": updated_metadata,
            "iterations": state["iterations"] + 1,
            "errors": "" if success else f"CLI Coder failed:\n{cli_errors}"
        }
        from utils import save_studio_state
        save_studio_state(workspace_dir, {**state, **res, "next_agent": "Tester"})
        return res

    llm = get_llm()
    files_str = "\n".join([f"- {f}" for f in files_list])
    
    # Retrieve contents of the target files only
    target_files_contents = get_target_files_contents(files_list)
    
    existing_files_desc = ""
    if state.get("codebase"):
        existing_files_desc = "Here is the indexed workspace structure:\n"
        for name, meta in state["codebase"].items():
            existing_files_desc += f"  - {name} ({meta['size']} bytes)\n"
        existing_files_desc += f"\nTarget File Contents to modify:\n{target_files_contents}"

    error_feedback = ""
    if state.get("errors"):
        raw_errors = state["errors"]
        pruned_errors = raw_errors[-4000:] if len(raw_errors) > 4000 else raw_errors
        error_feedback = f"""
IMPORTANT: The previous execution or test validation failed with the following errors. You MUST fix these bugs:
--- ERROR LOGS ---
{pruned_errors}
------------------
"""
        # Enterprise ReAct v2 Retrospective Self-Reflection
        if state.get("iterations", 0) >= 2:
            try:
                from react_engine import EnterpriseReActEngine
                reflection = EnterpriseReActEngine.generate_reflection_prompt(pruned_errors, state.get("iterations", 0))
                error_feedback = f"{reflection}\n\n{error_feedback}"
                print(f"[ReAct v2 🪞] Retrospective Self-Reflection Mode active for Coder Iteration {state.get('iterations', 0)}")
            except Exception:
                pass

    custom_prompts = load_custom_prompts()
    default_programmer = "You are a senior Software Implementation Engineer.\nYour task is to write clean, operational, and well-commented code files according to the requirements and impact plan.\nWrite the complete code for each target file. Do not use placeholders or skip details."
    programmer_header = (custom_prompts.get("programmer") or "").strip() or default_programmer
    
    prompt = f"""{programmer_header}

Requirements:
{state['requirements']}

Impact Plan:
{state['impact_analysis']}

Target files to implement/edit:
{files_str}

{existing_files_desc}
{error_feedback}

For EACH file to implement or update, output it in this exact format:
---FILE: relative/path/to/file.ext---
```language
... code contents here ...
```

Write all necessary code now:"""
    
    check_pause()
    # Always bypass cache for ImplementEngineer:
    # - When errors exist: stale cached code would reproduce the same bugs
    # - On any iteration > 0: the codebase has changed so the same prompt
    #   would produce a different correct answer; a cache hit returns stale code
    has_errors = bool(state.get("errors"))
    is_subsequent_iteration = state.get("iterations", 0) > 0
    should_bypass = has_errors or is_subsequent_iteration
    response = invoke_llm(llm, prompt, bypass_cache=should_bypass)
    check_pause()
    coder_output = response.content if hasattr(response, 'content') else str(response)
    
    from utils import parse_code_files, save_codebase, scan_workspace
    from database import get_active_workspace
    new_files = parse_code_files(coder_output)
    
    workspace_dir = get_active_workspace()
    
    # Enterprise AST Refactoring Diff Engine
    try:
        from ast_engine import EnterpriseASTEngine
        from utils import read_workspace_file
        ast_warnings = []
        for fname, new_code in new_files.items():
            old_code = read_workspace_file(workspace_dir, fname)
            if old_code and not old_code.startswith("[File"):
                diff_warns = EnterpriseASTEngine.analyze_ast_refactoring_diff(old_code, new_code)
                if diff_warns:
                    ast_warnings.extend([f"{fname}: {w}" for w in diff_warns])
        if ast_warnings:
            print("[AST Refactoring Engine ⚠️] AST structural diff warnings detected:")
            for w in ast_warnings:
                print(f"  - {w}")
    except Exception as e:
        print(f"[AST Refactoring Warning] {e}")

    # Save new/modified files directly to workspace
    save_codebase(new_files, workspace_dir)
    
    # Re-scan codebase to update metadata in state
    updated_metadata = scan_workspace(workspace_dir)
    
    if not new_files:
        print("[Implement Engineer Warning] No files parsed from LLM output. Verify format.")
        
    res = {
        "codebase": updated_metadata,
        "iterations": state["iterations"] + 1,
        "errors": ""
    }
    from utils import save_studio_state
    save_studio_state(workspace_dir, {**state, **res, "next_agent": "Tester"})
    return res

def tester_node(state: dict) -> dict:
    """
    QA Tester Agent Node.
    """
    global active_agent_name
    active_agent_name = "tester"
    check_pause()
    print("\n[QA Tester] Running test checks...")
    from utils import run_tests, run_security_scan, generate_test_report, scan_workspace
    from database import get_active_workspace
    
    workspace_dir = get_active_workspace()
    
    # Run tests directly from disk
    check_pause()
    success, test_logs = run_tests(workspace_dir)
    check_pause()
    
    print("--- Test Logs ---")
    print(test_logs)
    print(f"Validation Success: {success}")
    
    # Run security scans
    print("\n[QA Tester] Running Security and Vulnerability Audit...")
    security_results = run_security_scan(workspace_dir)
    
    # Audit for high-severity security vulnerabilities
    high_severity_vulns = [v for v in security_results.get("vulnerabilities", []) if v.get("severity") == "HIGH"]
    if high_severity_vulns:
        success = False
        security_error_msg = "\n\n--- SECURITY AUDIT FAILURE ---\n"
        security_error_msg += f"Found {len(high_severity_vulns)} high-severity security vulnerabilities. You MUST rewrite the code to fix these issues:\n"
        for v in high_severity_vulns:
            security_error_msg += f"- File: {v['file']}, Line: {v['line']}\n  Vulnerability: {v['issue_text']}\n  Code in question: {v['code']}\n"
        security_error_msg += "------------------------------\n"
        
        test_logs += security_error_msg
        print(security_error_msg)
        print("Forced test validation failure due to high-severity security vulnerabilities.")
    
    # Track incidents
    state.setdefault("incidents", [])
    if not success:
        state["incidents"].append({
            "iteration": state.get("iterations", 0) + 1,
            "error": test_logs
        })
        
    # Generate Markdown and HTML reports in the workspace
    print("\n[QA Tester] Generating comprehensive QA and Security Reports...")
    generate_test_report(workspace_dir, state, security_results, test_logs, success)
    
    # Re-scan workspace so that the reports are indexed in the state's codebase list
    updated_metadata = scan_workspace(workspace_dir)
    
    # Auto-commit on validation success
    if success:
        from utils import git_commit
        iteration = state.get("iterations", 0) + 1
        commit_msg = f"QA Validation Success - Iteration {iteration}: All test suites and security scans passed."
        git_commit(workspace_dir, commit_msg)
        print(f"[Git Hook] Auto-committed successful changes for iteration {iteration}")
    
    res = {
        "test_results": test_logs,
        "errors": "" if success else test_logs,
        "codebase": updated_metadata,
        "incidents": state["incidents"]
    }
    from utils import save_studio_state
    next_node = "Deployer" if success else "ImplementEngineer"
    save_studio_state(workspace_dir, {**state, **res, "next_agent": next_node})
    return res

def deployment_node(state: dict) -> dict:
    """
    Deployment Agent Node.
    """
    global active_agent_name
    active_agent_name = "deployer"
    check_pause()
    print("\n[Deployment Agent] Preparing and executing deployment...")
    llm = get_llm()
    
    custom_prompts = load_custom_prompts()
    default_deployer = "You are a DevOps and Deployment Engineer.\nFor the application built under these requirements, write:\n1. A local deployment script:\n   - On Windows systems, write a `deploy.bat` file.\n   - For other platforms, write a `deploy.sh` script or a python script `deploy.py`.\n2. A CI/CD Pipeline configuration file:\n   - Generate an Azure DevOps pipeline config (`azure-pipelines.yml`) to support Azure DevOps/TFS.\n   - Also generate a GitHub Actions workflow (`.github/workflows/ci.yml`) to support GitHub repository pipelines.\n   - Both pipelines should be configured to install dependencies, run linting/compilation checks, execute your unit tests, and trigger static security/vulnerability scans (e.g. Bandit for Python)."
    deployer_header = (custom_prompts.get("deployer") or "").strip() or default_deployer
    
    prompt = f"""{deployer_header}

Requirements:
{state['requirements']}

File list:
{", ".join(state['codebase'].keys())}

Generate each file in this exact format:
---FILE: deploy.bat--- (or deploy.sh, deploy.py)
```bat
... script content ...
```

---FILE: azure-pipelines.yml---
```yaml
... Azure DevOps YAML config ...
```

---FILE: .github/workflows/ci.yml---
```yaml
... GitHub Actions YAML config ...
```

Write the deployment scripts:"""
    
    check_pause()
    # Always bypass cache: deployment scripts reference the current file list
    # which changes every run; a cached script would deploy stale/wrong files.
    response = invoke_llm(llm, prompt, bypass_cache=True)
    check_pause()
    deploy_output = response.content if hasattr(response, 'content') else str(response)
    
    from utils import parse_code_files, save_codebase, run_deployment, scan_workspace
    from database import get_active_workspace
    deploy_files = parse_code_files(deploy_output)
    
    workspace_dir = get_active_workspace()
    
    # Save deploy script to workspace
    save_codebase(deploy_files, workspace_dir)
    
    # Interactive Gate: Check if user approves running deployment script
    check_pause()
    deployment_spec = ""
    for path, code in deploy_files.items():
        deployment_spec += f"--- {path} ---\n{code}\n\n"
    feedback = ask_user_approval("Deployment Execution", f"The application code has been written and successfully validated. Review the generated deployment scripts below and approve to execute the deployment:\n\n{deployment_spec}")
    if feedback:
        print("[Deployment Gate] User rejected deployment or requested changes. Re-routing back to ImplementEngineer...")
        return {
            "errors": f"Deployment execution was rejected by user. Feedback: {feedback}"
        }
    
    # Execute deployment script
    check_pause()
    success, deploy_logs = run_deployment(workspace_dir)
    check_pause()
    
    # Re-scan to capture deploy script in codebase metadata
    updated_metadata = scan_workspace(workspace_dir)
    
    # Auto-commit on successful deployment
    if success:
        # Generate walkthrough_agent.md handoff documentation
        print("\n[Deployment Agent] Generating walkthrough_agent.md handoff documentation...")
        walkthrough_prompt = f"""You are a Lead Software Engineer and Technical Writer.
Produce a clean, professional, and comprehensive handoff document `walkthrough_agent.md` for the changes just completed.

Initial Requirements Prompt:
{state.get('prompt', '')}

Requirements Specifications:
{state.get('requirements', '')}

Final Codebase Files:
{", ".join(updated_metadata.keys())}

Agent Execution History:
- Coder Iterations: {state.get('iterations', 0)}
- Test Incidents/Bugs recorded: {state.get('incidents', [])}

Write a detailed Markdown report containing:
1. Summary of Accomplishments: High-level overview of what was successfully built and why.
2. Agent Execution telemetry:
   - A detailed breakdown or table describing what each agent (BusinessAnalyst, ImpactAnalyzer, ImplementEngineer, Tester, and Deployer) did to fulfill the requirement.
   - Specify how many times each agent was executed.
   - Detail the success/fail outcome of each agent (e.g. if the Coder had to run multiple iterations to resolve test failures or bugs reported by the Tester).
3. Detailed File Changes: A clean table listing each file created or modified and its purpose.
4. Local Verification & Running Instructions: Simple, step-by-step commands to run the application and execute tests.
5. Future Recommendations: Next steps or suggestions for enhancements.

Output ONLY the raw markdown content. Do not include markdown code block formatting wrap around the entire report, just raw markdown content."""

        try:
            walkthrough_response = invoke_llm(llm, walkthrough_prompt)
            walkthrough_content = walkthrough_response.content if hasattr(walkthrough_response, 'content') else str(walkthrough_response)
            
            walkthrough_path = os.path.join(workspace_dir, "walkthrough_agent.md")
            with open(walkthrough_path, "w", encoding="utf-8") as f:
                f.write(walkthrough_content)
            print(f"[Walkthrough Generator] Successfully wrote handoff summary to {walkthrough_path}")
        except Exception as e:
            print(f"[Walkthrough Generator Warning] Failed to write walkthrough: {e}")

        # Re-scan to capture walkthrough_agent.md in codebase metadata
        updated_metadata = scan_workspace(workspace_dir)

        from utils import git_commit
        git_commit(workspace_dir, "Deployment script and walkthrough_agent.md handoff documentation generated.")
        print("[Git Hook] Auto-committed successful deployment script and handoff documentation.")
    
    print("--- Deployment Logs ---")
    print(deploy_logs)
    print(f"Deployment Success: {success}")
    
    res = {
        "codebase": updated_metadata,
        "deployment_logs": deploy_logs,
        "errors": "" if success else f"Deployment step failed:\n{deploy_logs}"
    }
    from utils import save_studio_state
    next_node = "FINISH" if success else "ImplementEngineer"
    save_studio_state(workspace_dir, {**state, **res, "next_agent": next_node})
    return res
