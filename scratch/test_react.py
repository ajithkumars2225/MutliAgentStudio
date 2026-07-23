import sys
sys.path.append(".")
import agents

raw_text = """```json
{
  "thought": "No requirements found. Routing to BusinessAnalyst to generate specification.",
  "next_agent": "BusinessAnalyst"
}
```"""

dec, thought = agents.parse_orchestrator_decision(raw_text)
print("SUCCESS: ReAct decision parsed cleanly!")
print("Action:", dec)
print("Thought:", thought)
