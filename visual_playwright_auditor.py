"""
v2 Visual Playwright Screenshot Auditor.
Captures live full-page browser screenshots during Playwright E2E UI testing
and embeds visual DOM snapshots into the test report HTML.
"""
import os
import subprocess
from pathlib import Path
from typing import Tuple, List, Dict

class VisualPlaywrightAuditor:
    @staticmethod
    def capture_live_screenshots(workspace_dir: str, target_url: str = "http://localhost:5000") -> List[Dict[str, str]]:
        """
        Launches a headless Playwright script to capture full-page screenshots of key routes.
        Returns a list of captured screenshot file information.
        """
        base_path = Path(workspace_dir).resolve()
        screenshots_dir = base_path / "TestResults" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        target_clean = target_url.rstrip("/")
        script_code = f"""
const {{ chromium }} = require('playwright');
const path = require('path');

(async () => {{
  try {{
    const browser = await chromium.launch({{ headless: true }});
    const page = await browser.newPage();
    
    const screenshotsDir = '{str(screenshots_dir).replace("\\\\", "/")}';
    
    // 1. Capture Index / Home page
    await page.goto('{target_clean}', {{ waitUntil: 'networkidle', timeout: 5000 }}).catch(() => {{}});
    await page.screenshot({{ path: path.join(screenshotsDir, '01_homepage.png'), fullPage: true }});
    
    // 2. Capture Employees Index
    await page.goto('{target_clean}/Employees', {{ waitUntil: 'networkidle', timeout: 5000 }}).catch(() => {{}});
    await page.screenshot({{ path: path.join(screenshotsDir, '02_employee_list.png'), fullPage: true }});
    
    // 3. Capture Create Form
    await page.goto('{target_clean}/Employees/Create', {{ waitUntil: 'networkidle', timeout: 5000 }}).catch(() => {{}});
    await page.screenshot({{ path: path.join(screenshotsDir, '03_create_form.png'), fullPage: true }});
    
    await browser.close();
    console.log("Playwright visual screenshots captured successfully.");
  }} catch (err) {{
    console.error("Screenshot capture warning:", err);
  }}
}})();
"""
        script_path = screenshots_dir / "capture.js"
        script_path.write_text(script_code, encoding="utf-8")
        
        captured = []
        try:
            res = subprocess.run(["node", str(script_path)], capture_output=True, text=True, cwd=str(base_path), timeout=30)
            print(f"[Visual Auditor 📸] Playwright screenshot runner output: {res.stdout.strip()}")
        except Exception as e:
            print(f"[Visual Auditor Warning] Could not run Node Playwright screenshot script: {e}")
            
        for img_name in ["01_homepage.png", "02_employee_list.png", "03_create_form.png"]:
            img_file = screenshots_dir / img_name
            if img_file.exists():
                captured.append({
                    "name": img_name,
                    "filepath": str(img_file),
                    "relative_path": f"TestResults/screenshots/{img_name}"
                })
                
        return captured
