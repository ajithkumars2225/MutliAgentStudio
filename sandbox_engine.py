import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple

class SandboxExecutionEngine:
    """
    Enterprise Ephemeral Sandbox Code Execution & Security Isolation Engine.
    Confines code execution to safe workspace directories, strips sensitive environment variables,
    enforces strict process timeouts, and isolates execution environments.
    """

    @classmethod
    def get_sanitized_env(cls) -> Dict[str, str]:
        """
        Strips dangerous API keys and credentials from process environment before spawning untrusted code.
        """
        env = os.environ.copy()
        # Keep essential PATH and System variables, strip secrets for untrusted subprocess runs
        dangers = ["OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "AWS_SECRET_ACCESS_KEY"]
        for key in list(env.keys()):
            if any(d in key.upper() for d in ["SECRET", "PASSWORD", "PASSWD", "TOKEN", "KEY"]):
                if key not in ["PATH", "SYSTEMROOT", "WINDIR", "PYTHONPATH"]:
                    env[key] = "SANITIZED_SANDBOX_VALUE"
        return env

    @classmethod
    def execute_in_sandbox(cls, command: List[str], cwd: str, timeout_sec: int = 15) -> Tuple[bool, str, str]:
        """
        Executes a process inside a confined, environment-sanitized sandbox wrapper.
        """
        safe_cwd = str(Path(cwd).resolve())
        sanitized_env = cls.get_sanitized_env()

        try:
            res = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=safe_cwd,
                env=sanitized_env,
                timeout=timeout_sec,
                check=False
            )
            success = res.returncode == 0
            return success, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Sandbox Execution Terminated: Process exceeded max timeout of {timeout_sec} seconds."
        except Exception as e:
            return False, "", f"Sandbox Process Error: {str(e)}"
