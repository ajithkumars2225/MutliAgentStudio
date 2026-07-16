# Implementation Plan: Simulation State Resumption

This plan outlines the design and implementation details to support **Simulation Resumption** when a run fails or encounters model limit/quota issues. Changing settings and running the same prompt again will resume execution from the last successful agent node.

---

## ℹ️ Architectural Design

### 1. State Serialization (`.studio/state.json`)
At the end of each agent node execution (Business Analyst, Impact Analyzer, Coder, Tester, Deployer), we will save a snapshot of the runtime graph state into a local `.studio/state.json` file inside the active workspace directory.
The snapshot will contain:
* `prompt`
* `requirements`
* `impact_analysis`
* `files_to_modify`
* `next_agent`
* `iterations`
* `errors`

### 2. Matching Prompt Verification
When a user clicks "Run Studio":
1. The backend checks if `.studio/state.json` exists in the workspace.
2. If it exists, and the `prompt` matches the new run request, we load the stored requirements, impact plans, and target file lists into the initial LangGraph state.
3. The `next_agent` flag is loaded dynamically. If BA and Impact Planner had already completed, the run starts directly at `ImplementEngineer` (or whichever node failed).
4. If the prompt is different (new requirement), the `.studio` state is ignored and cleared to start a fresh run.

---

## Proposed Changes

### 1. State Persistence Helpers
#### [MODIFY] [utils.py](file:///C:/PERSONAL%20DATA/2.POC/AGENTS/utils.py)
* Add `save_studio_state(workspace_dir: str, state: dict)`:
  * Creates `.studio` folder if missing.
  * Serializes runtime keys to `.studio/state.json`.
* Add `clear_studio_state(workspace_dir: str)`:
  * Removes `.studio/state.json` file.

### 2. Agent Nodes Updates
#### [MODIFY] [agents.py](file:///C:/PERSONAL%20DATA/2.POC/AGENTS/agents.py)
* Call `save_studio_state` at the end of each node function:
  * `business_analyst_node()`
  * `impact_analyzer_node()`
  * `implement_engineer_node()`
  * `tester_node()`
  * `deployment_node()`
* In `orchestrator_node()`, if the decision is `FINISH`, trigger `clear_studio_state()`.

### 3. Graph Startup Initialization
#### [MODIFY] [app.py](file:///C:/PERSONAL%20DATA/2.POC/AGENTS/app.py)
* Before initializing the `initial_state` in `run_agent_in_thread`:
  * Check if `.studio/state.json` exists and matches the prompt.
  * If matched, load it to restore state variables and set `"next_agent"` dynamically.
  * If not matched, start fresh and clear any existing state file.

---

## Verification Plan

### Automated Tests
* Verify python backend compilation:
  ```powershell
  python -c "import app, database, agents, utils; print('Compilation OK')"
  ```

### Manual Verification
1. Open a workspace and configure a model.
2. Run a requirements prompt. Wait for the Business Analyst and Impact Analyzer to complete.
3. Pause or terminate the run during the Coder step.
4. Modify the LLM model in Settings.
5. Click **Run Studio** on the same prompt history entry.
6. Verify in the Agent Console that it **skips the Business Analyst and Impact Analyzer** nodes, resuming directly at the **Implement Engineer** node.
