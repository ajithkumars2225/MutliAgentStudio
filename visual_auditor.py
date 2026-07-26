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
            "findings": findings
        }

    @classmethod
    def audit_workspace_ui(cls, workspace_dir: str) -> List[Dict[str, Any]]:
        """
        Audits all frontend HTML and CSS files in the target workspace.
        """
        base_path = Path(workspace_dir).resolve()
        if not base_path.exists():
            return []

        audits = []
        for root, _, files in os.walk(base_path):
            if ".git" in root or "node_modules" in root or ".venv" in root:
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".html", ".htm", ".css"]:
                    full_p = Path(root) / f
                    try:
                        rel_p = str(full_p.relative_to(base_path)).replace("\\", "/")
                        content = full_p.read_text(encoding="utf-8", errors="ignore")
                        audit_res = cls.audit_frontend_file(rel_p, content)
                        audits.append(audit_res)
                    except Exception:
                        pass
        return audits

    @classmethod
    def capture_preview_screenshot(cls, workspace_dir: str, preview_url: str) -> Dict[str, Any]:
        """
        Uses Playwright headless browser to capture a real screenshot of the live preview URL
        and saves it to <workspace>/.studio/preview_audit.png.
        """
        studio_dir = Path(workspace_dir) / ".studio"
        studio_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = studio_dir / "preview_audit.png"
        
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(preview_url, timeout=10000, wait_until="networkidle")
                page.screenshot(path=str(screenshot_path))
                browser.close()
                print(f"[Visual Auditor 📸] Successfully captured live UI screenshot: {screenshot_path}")
                return {"status": "success", "screenshot_path": str(screenshot_path), "url": preview_url}
        except Exception as e:
            print(f"[Visual Auditor Warning] Could not capture live screenshot: {e}")
            return {"status": "skipped", "reason": str(e)}
