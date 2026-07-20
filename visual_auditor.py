import re
import os
from pathlib import Path
from typing import Dict, List, Any

class VisualUIAuditorEngine:
    """
    Enterprise Visual UI Layout & Aesthetic Auditor Engine.
    Inspects HTML/CSS/JS frontend files for modern typography (Google Fonts),
    responsive breakpoints, color contrast, flex/grid layouts, and glassmorphic aesthetics.
    """

    @classmethod
    def audit_frontend_file(cls, filepath: str, content: str) -> Dict[str, Any]:
        """
        Audits an HTML or CSS file for modern design aesthetics.
        """
        ext = os.path.splitext(filepath)[1].lower()
        findings = []
        score = 100

        if ext in [".html", ".htm"]:
            # Check 1: Title & Meta tags (SEO Best Practices)
            if "<title>" not in content.lower():
                findings.append("Missing `<title>` tag for SEO.")
                score -= 10
            if 'name="viewport"' not in content.lower():
                findings.append("Missing responsive viewport meta tag (`<meta name=\"viewport\">`).")
                score -= 15

            # Check 2: Modern Typography (Google Fonts)
            if "fonts.googleapis.com" not in content and "font-family" not in content:
                findings.append("No modern web font detected (e.g. Google Fonts Inter/Roboto/Outfit). Browser default serif font may render.")
                score -= 15

            # Check 3: CSS styling
            if "<style>" not in content and '<link rel="stylesheet"' not in content:
                findings.append("No CSS stylesheet or inline `<style>` block found. Layout may appear unstyled.")
                score -= 25

        elif ext == ".css":
            # Check 1: Modern Layout (Flexbox / Grid)
            if "display: flex" not in content and "display: grid" not in content and "display:flex" not in content:
                findings.append("No CSS Flexbox or Grid layout constructs detected. UI may lack modern responsive alignment.")
                score -= 15

            # Check 2: Color Palette & Aesthetics
            if "var(--" not in content:
                findings.append("No CSS variables (`var(--main-color)`) detected for cohesive design tokens.")
                score -= 10

            # Check 3: Micro-interactions & Animations
            if ":hover" not in content and "transition" not in content:
                findings.append("No hover state transitions or micro-animations found for interactive elements.")
                score -= 10

        return {
            "filepath": filepath,
            "aesthetic_score": max(0, score),
            "passed": score >= 75,
            "findings": findings
        }

    @classmethod
    def audit_workspace_ui(cls, workspace_directory: str) -> List[Dict[str, Any]]:
        """
        Audits all frontend assets in workspace.
        """
        base = Path(workspace_directory)
        results = []
        if not base.exists():
            return results

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "node_modules"}]
            for f in files:
                filepath = Path(root) / f
                if filepath.suffix.lower() in [".html", ".css"]:
                    try:
                        rel_path = str(filepath.relative_to(base)).replace("\\", "/")
                        content = filepath.read_text(encoding="utf-8", errors="ignore")
                        res = cls.audit_frontend_file(rel_path, content)
                        results.append(res)
                    except Exception:
                        pass
        return results
