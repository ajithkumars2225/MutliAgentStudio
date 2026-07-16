from typing import Dict, List, TypedDict

class CompanyState(TypedDict):
    """
    Upgraded state definition for the 6-agent enterprise software agency.
    Tracks state transitions and outputs across all phases of the SDLC.
    """
    prompt: str                 # Original user prompt / requirement / bug description
    requirements: str           # Output from the Business Analyst (detailed specs & criteria)
    impact_analysis: str        # Output from the Impact Analyzer (scope, risks, and files map)
    files_to_modify: List[str]  # Explicit list of relative file paths to write or update
    codebase: Dict[str, str]    # Current active codebase: relative_path -> file content
    test_plan: str              # QA test plan and strategy
    test_results: str           # Output logs from compilation, static checks, or test runs
    deployment_plan: str        # Scripting or configuration instructions for deployment
    deployment_logs: str        # Executed deployment logs/console outputs
    errors: str                 # Unresolved errors or feedback that requires code fixing
    iterations: int             # Coding/correction loop iteration count
    max_iterations: int         # Safety threshold to prevent infinite coding cycles
    next_agent: str             # Destination node computed by the Orchestrator
