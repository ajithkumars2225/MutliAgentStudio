import sys
import os
import json
import re

os.environ["AUTOPROCEED"] = "true"


# Set Python path to search local directory first
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import agents
import agents

class MockResponse:
    def __init__(self, content: str):
        self.content = content

class MockLLM:
    def __init__(self):
        self.orchestration_count = 0
        self.coder_count = 0

    def invoke(self, prompt: str) -> MockResponse:
        prompt_lower = prompt.lower()
        
        # 1. ORCHESTRATOR DECISION MOCKING
        if "orchestrator supervisor" in prompt_lower:
            self.orchestration_count += 1
            
            has_requirements = "requirements spec: established" in prompt_lower
            has_impact = "impact spec: established" in prompt_lower
            has_code = "codebase files: calculator.py" in prompt_lower
            has_errors = "errors: none" not in prompt_lower
            has_test_logs = "test logs: none" not in prompt_lower
            has_deploy_logs = "deployment logs: none" not in prompt_lower
            
            if not has_requirements:
                decision = "BusinessAnalyst"
            elif not has_impact:
                decision = "ImpactAnalyzer"
            elif not has_code or (has_errors and not has_deploy_logs):
                decision = "ImplementEngineer"
            elif not has_test_logs:
                decision = "Tester"
            elif not has_deploy_logs:
                decision = "Deployer"
            else:
                decision = "FINISH"
                
            return MockResponse(f"""
```json
{{
  "next_agent": "{decision}"
}}
```
""")

        # 2. BUSINESS ANALYST MOCKING
        elif "business analyst" in prompt_lower:
            return MockResponse("# Requirements\n- Build a calculator.py\n- Build test_calculator.py")

        # 3. IMPACT ANALYZER MOCKING
        elif "impact analyzer" in prompt_lower:
            return MockResponse("""# Impact Plan
We need to implement the base calculator.py and test_calculator.py.

```json
{
  "files": ["calculator.py", "test_calculator.py"]
}
```
""")

        # 4. IMPLEMENT ENGINEER (CODER) MOCKING
        elif "implementation engineer" in prompt_lower:
            self.coder_count += 1
            
            if "error logs" in prompt_lower or "unresolved errors" in prompt_lower or "failed" in prompt_lower:
                print(f"[MockLLM] Implementer fixing code (Count: {self.coder_count})...")
                return MockResponse("""
---FILE: calculator.py---
```python
def add(a, b):
    return a + b
```

---FILE: test_calculator.py---
```python
import unittest
from calculator import add

class TestCalculator(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

if __name__ == '__main__':
    unittest.main()
```
""")
            else:
                print(f"[MockLLM] Implementer writing initial buggy code (Count: {self.coder_count})...")
                return MockResponse("""
---FILE: calculator.py---
```python
def add(a, b):
    return a - b  # Bug here!
```

---FILE: test_calculator.py---
```python
import unittest
from calculator import add

class TestCalculator(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)  # Will fail because 2 - 3 is -1

if __name__ == '__main__':
    unittest.main()
```
""")

        # 5. DEPLOYMENT AGENT MOCKING
        elif "devops and deployment engineer" in prompt_lower:
            print("[MockLLM] Deployer generating deployment script...")
            return MockResponse("""
---FILE: deploy.py---
```python
print("Deploying enterprise calculator app to mock server...")
print("Deployment completed successfully!")
```
""")

        return MockResponse("Mock Response")

# Override get_llm in agents
mock_llm_instance = MockLLM()
agents.get_llm = lambda: mock_llm_instance

# Run main graph execution
from main import build_graph

def test_run():
    print("=" * 60)
    print("RUNNING ENTERPRISE MOCK TEST FOR 6-AGENT ROUTING...")
    print("=" * 60)
    
    import shutil
    workspace_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
    if os.path.exists(workspace_dir):
        print(f"Cleaning workspace folder: {workspace_dir}")
        shutil.rmtree(workspace_dir)
        
    initial_state = {
        "prompt": "Build a calculator with add function.",
        "requirements": "",
        "impact_analysis": "",
        "files_to_modify": [],
        "codebase": {},
        "test_plan": "",
        "test_results": "",
        "deployment_plan": "",
        "deployment_logs": "",
        "errors": "",
        "iterations": 0,
        "max_iterations": 3,
        "next_agent": "BusinessAnalyst"
    }
    
    app = build_graph()
    final_state = app.invoke(initial_state)
    
    print("\n" + "=" * 60)
    print("ENTERPRISE MOCK TEST COMPLETED")
    print("=" * 60)
    print(f"Total Coding Iterations: {final_state['iterations']}")
    print(f"Final State Errors: '{final_state.get('errors')}'")
    print(f"Deployment Logs:\n{final_state.get('deployment_logs')}")
    print("\nFiles in final codebase:")
    for name, content in final_state["codebase"].items():
        print(f"  - {name} ({len(content)} bytes)")
        
    assert final_state['iterations'] == 2, f"Expected 2 iterations, got {final_state['iterations']}"
    assert final_state['errors'] == "", "Expected errors to be resolved"
    assert "deploy.py" in final_state["codebase"], "Expected deploy.py to be created"
    assert "Deployment completed successfully!" in final_state["deployment_logs"], "Expected deployment to succeed"
    print("\n[SUCCESS] Enterprise multi-agent orchestration validated successfully!")

if __name__ == "__main__":
    test_run()
