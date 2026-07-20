import time
import json
from typing import Dict, List, Any

class EnterpriseReActEngine:
    """
    Enterprise ReAct Engine (v2)
    Provides ReAct Trace Auditing, Retrospective Self-Reflection,
    and Sub-Goal Progress Tracking across Multi-Agent trajectories.
    """
    _traces: List[Dict[str, Any]] = []

    @classmethod
    def record_step(cls, agent_name: str, thought: str, action: str, observation: str = "", tokens: int = 0):
        """
        Records a step in the ReAct execution trajectory.
        """
        step = {
            "step_id": len(cls._traces) + 1,
            "agent": agent_name,
            "thought": thought,
            "action": action,
            "observation": observation,
            "tokens": tokens,
            "timestamp": time.time()
        }
        cls._traces.append(step)

    @classmethod
    def get_trace_history(cls) -> List[Dict[str, Any]]:
        """
        Returns full ReAct trace trajectory.
        """
        return cls._traces

    @classmethod
    def clear_trace_history(cls):
        """
        Resets ReAct trace trajectory.
        """
        cls._traces = []

    @classmethod
    def generate_reflection_prompt(cls, errors: str, attempts: int) -> str:
        """
        Retrospective Self-Reflection Engine (v2).
        Triggers root-cause analysis when coding retries reach 2 or more iterations.
        """
        return f"""
[RETROSPECTIVE SELF-REFLECTION MODE (Attempt #{attempts})]
Your previous implementation attempts failed test or syntax verification. 
Do NOT repeat naive trial-and-error fixes. Perform a root-cause retrospective:

1. Root-Cause Diagnosis: Why did the previous attempts fail?
2. Architectural Assumption: What assumption in the code structure was incorrect?
3. Definite Fix Strategy: Describe the fundamental architectural correction required before writing code.

Recent Failure Stack Trace / Error Log:
{errors[-3000:]}
"""
