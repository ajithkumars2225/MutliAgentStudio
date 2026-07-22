"""
v2 Git Feature Branching & Worktree Manager.
Manages isolated git branches for feature development, cleanly committing agent changes
and merging them into main upon QA test approval.
"""
import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional

class GitBranchingManager:
    @staticmethod
    def is_git_repo(workspace_dir: str) -> bool:
        git_dir = Path(workspace_dir) / ".git"
        return git_dir.exists()

    @staticmethod
    def init_or_ensure_git(workspace_dir: str) -> bool:
        if not GitBranchingManager.is_git_repo(workspace_dir):
            try:
                subprocess.run(["git", "init"], cwd=workspace_dir, capture_output=True, check=False)
                subprocess.run(["git", "config", "user.name", "MultiAgentStudio Agent"], cwd=workspace_dir, capture_output=True, check=False)
                subprocess.run(["git", "config", "user.email", "agent@multiagentstudio.local"], cwd=workspace_dir, capture_output=True, check=False)
                return True
            except Exception:
                return False
        return True

    @staticmethod
    def create_feature_branch(workspace_dir: str, feature_name: str) -> Tuple[bool, str]:
        if not GitBranchingManager.init_or_ensure_git(workspace_dir):
            return False, "Not a git repository and could not initialize git."
        
        import re
        import time
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', feature_name[:30].strip().lower())
        branch_name = f"feature/{sanitized}-{int(time.time())}"
        
        try:
            res = subprocess.run(["git", "checkout", "-b", branch_name], cwd=workspace_dir, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                print(f"[Git Branching 🌿] Created isolated feature branch: {branch_name}")
                return True, branch_name
            return False, res.stderr
        except Exception as e:
            return False, str(e)

    @staticmethod
    def commit_agent_changes(workspace_dir: str, commit_message: str) -> Tuple[bool, str]:
        if not GitBranchingManager.is_git_repo(workspace_dir):
            return False, "Not a git repo."
        try:
            subprocess.run(["git", "add", "."], cwd=workspace_dir, capture_output=True, check=False)
            res = subprocess.run(["git", "commit", "-m", commit_message], cwd=workspace_dir, capture_output=True, text=True, check=False)
            if res.returncode == 0 or "nothing to commit" in res.stdout:
                return True, "Committed agent changes cleanly."
            return False, res.stderr
        except Exception as e:
            return False, str(e)

    @staticmethod
    def merge_feature_to_main(workspace_dir: str, branch_name: str) -> Tuple[bool, str]:
        if not GitBranchingManager.is_git_repo(workspace_dir):
            return False, "Not a git repo."
        try:
            GitBranchingManager.commit_agent_changes(workspace_dir, f"Finalize feature in {branch_name}")
            
            res_main = subprocess.run(["git", "checkout", "main"], cwd=workspace_dir, capture_output=True, text=True, check=False)
            if res_main.returncode != 0:
                subprocess.run(["git", "checkout", "master"], cwd=workspace_dir, capture_output=True, text=True, check=False)
                
            res_merge = subprocess.run(["git", "merge", branch_name, "--no-ff", "-m", f"Merge feature {branch_name} after QA validation"], cwd=workspace_dir, capture_output=True, text=True, check=False)
            if res_merge.returncode == 0:
                print(f"[Git Branching 🌿] Merged feature branch {branch_name} into main branch cleanly!")
                return True, f"Successfully merged {branch_name} into main."
            return False, f"Merge conflict or failure: {res_merge.stderr}"
        except Exception as e:
            return False, str(e)
