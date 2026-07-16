import argparse
import os
import sys
from langgraph.graph import StateGraph, START, END

# Import state and agent nodes
from state import CompanyState
from agents import (
    orchestrator_node,
    business_analyst_node,
    impact_analyzer_node,
    implement_engineer_node,
    tester_node,
    deployment_node
)
from utils import scan_workspace

def route_orchestrator(state: CompanyState) -> str:
    """
    Orchestration router. Translates next_agent decision into graph state transitions.
    """
    decision = state.get("next_agent", "BusinessAnalyst")
    
    if decision == "BusinessAnalyst":
        return "BusinessAnalyst"
    elif decision == "ImpactAnalyzer":
        return "ImpactAnalyzer"
    elif decision == "ImplementEngineer":
        return "ImplementEngineer"
    elif decision == "Tester":
        return "Tester"
    elif decision == "Deployer":
        return "Deployer"
    elif decision == "FINISH":
        return END
    else:
        print(f"[Router Warning] Unknown decision '{decision}'. Stopping workflow.")
        return END

def build_graph() -> StateGraph:
    """
    Compiles the multi-agent orchestration state graph.
    """
    workflow = StateGraph(CompanyState)
    
    # 1. Add agent nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("BusinessAnalyst", business_analyst_node)
    workflow.add_node("ImpactAnalyzer", impact_analyzer_node)
    workflow.add_node("ImplementEngineer", implement_engineer_node)
    workflow.add_node("Tester", tester_node)
    workflow.add_node("Deployer", deployment_node)
    
    # 2. Add connections back to Orchestrator (Hub-and-Spoke)
    workflow.add_edge(START, "orchestrator")
    workflow.add_edge("BusinessAnalyst", "orchestrator")
    workflow.add_edge("ImpactAnalyzer", "orchestrator")
    workflow.add_edge("ImplementEngineer", "orchestrator")
    workflow.add_edge("Tester", "orchestrator")
    workflow.add_edge("Deployer", "orchestrator")
    
    # 3. Add conditional transitions from Orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        route_orchestrator,
        {
            "BusinessAnalyst": "BusinessAnalyst",
            "ImpactAnalyzer": "ImpactAnalyzer",
            "ImplementEngineer": "ImplementEngineer",
            "Tester": "Tester",
            "Deployer": "Deployer",
            END: END
        }
    )
    
    return workflow.compile()

def main():
    parser = argparse.ArgumentParser(description="Enterprise LangGraph Multi-Agent Software Automation")
    parser.add_argument(
        "--prompt", 
        type=str, 
        required=True,
        help="The high-level prompt, new requirement, or issue/bug description."
    )
    parser.add_argument(
        "--max-iterations", 
        type=int, 
        default=3,
        help="Maximum self-correction coding iterations before stopping."
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["gemini", "openai", "ollama"],
        help="Override LLM provider configured in .env."
    )
    
    args = parser.parse_args()
    
    # Override provider if specified in arguments
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
        
    print("=" * 60)
    print("Initializing Enterprise LangGraph Software Automation Agency...")
    print("=" * 60)
    
    # Scan existing codebase in 'workspace' directory
    from database import get_active_workspace
    workspace_dir = get_active_workspace()
    print(f"Scanning workspace folder for existing repository: {workspace_dir}")
    existing_codebase = scan_workspace(workspace_dir)
    
    if existing_codebase:
        print(f"Found existing repository with {len(existing_codebase)} active files:")
        for file in existing_codebase.keys():
            print(f"  - {file}")
    else:
        print("No pre-existing files found in workspace (Starting a new repository).")
        
    # Setup initial state
    initial_state = {
        "prompt": args.prompt,
        "requirements": "",
        "impact_analysis": "",
        "files_to_modify": [],
        "codebase": existing_codebase,
        "test_plan": "",
        "test_results": "",
        "deployment_plan": "",
        "deployment_logs": "",
        "errors": "",
        "iterations": 0,
        "max_iterations": args.max_iterations,
        "next_agent": "BusinessAnalyst",
        "incidents": []
    }
    
    # Compile graph
    app = build_graph()
    
    try:
        # Run graph
        final_state = app.invoke(initial_state)
        
        print("\n" + "=" * 60)
        print("ENTERPRISE SIMULATION COMPLETED")
        print("=" * 60)
        print(f"Total Coding Iterations: {final_state['iterations']}")
        print(f"Output files saved in: {workspace_dir}")
        print("\nFiles in final codebase:")
        for name in final_state["codebase"].keys():
            print(f"- {name}")
            
    except Exception as e:
        print(f"\nError during graph execution: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
