import os
from typing import Dict, Any, Tuple

class ModelRouterEngine:
    """
    Enterprise Dynamic Model Router & Token Cost Optimizer Engine.
    Dynamically selects optimal LLM models based on task complexity,
    enforces token budgets, and minimizes API costs.
    """

    # Complexity tiers
    TASK_TIERS = {
        "orchestrator": "light",
        "business_analyst": "medium",
        "impact_analyzer": "medium",
        "programmer": "heavy",
        "tester": "light",
        "deployer": "light"
    }

    MODEL_COSTS = {
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4o": {"input": 0.0025, "output": 0.01}
    }

    @classmethod
    def select_model_for_task(cls, agent_name: str, current_provider: str, current_model: str) -> str:
        """
        Selects light vs heavy model based on agent role complexity.
        """
        tier = cls.TASK_TIERS.get(agent_name.lower(), "medium")

        if current_provider == "google":
            if tier == "light":
                return "gemini-1.5-flash"
            return current_model or "gemini-1.5-pro"
        elif current_provider == "openai":
            if tier == "light":
                return "gpt-4o-mini"
            return current_model or "gpt-4o"
        
        return current_model

    @classmethod
    def calculate_cost(cls, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculates exact USD cost for a call.
        """
        rates = cls.MODEL_COSTS.get(model_name, {"input": 0.0001, "output": 0.0004})
        cost = (input_tokens * rates["input"] / 1000.0) + (output_tokens * rates["output"] / 1000.0)
        return round(cost, 6)

    @classmethod
    def verify_budget_limit(cls, total_cost: float, max_budget_usd: float = 2.0) -> Tuple[bool, str]:
        """
        Budget Guardrail: Verifies execution total spend has not exceeded budget.
        """
        if total_cost >= max_budget_usd:
            return False, f"Execution halted: Token cost budget limit reached (${total_cost:.4f} >= ${max_budget_usd:.2f})"
        return True, "Budget OK"
