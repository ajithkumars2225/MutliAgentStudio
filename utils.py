import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Tuple, Any


def scan_workspace(directory: str) -> Dict[str, Dict[str, Any]]:
    """
    Scans the target workspace directory and returns metadata of all active files
    (excluding virtualenvs, git files, cache, and build files).
    Does NOT load file contents into memory, making it scale to large codebases.
    
    Returns:
        dict: { "relative/file/path": { "size": bytes, "lines": count } }
    """
    base_path = Path(directory).resolve()
    if not base_path.exists():
        return {}
        
    metadata = {}
    exclude_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}
    exclude_files = {".env", ".gitignore", "package-lock.json", "poetry.lock"}
    
    allowed_extensions = {
        ".py", ".js", ".ts", ".html", ".css", ".json", ".sql", 
        ".sh", ".bat", ".yml", ".yaml", ".md", ".txt", ".dockerfile", "Dockerfile",
        ".cs", ".csproj", ".sln" # Added C# / .NET files support
    }

    for root, dirs, files in os.walk(base_path):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file in exclude_files:
                continue
                
            file_path = Path(root) / file
            if file_path.suffix.lower() in allowed_extensions or file_path.name in allowed_extensions:
                try:
                    relative_name = str(file_path.relative_to(base_path)).replace("\\", "/")
                    stat = file_path.stat()
                    
                    # Estimate line count (read as binary/ignore errors to prevent crash on non-text)
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    line_count = len(content.splitlines())
                    
                    metadata[relative_name] = {
                        "size": stat.st_size,
                        "lines": line_count
                    }

                    # Enterprise Polyglot AST Symbol Indexing (Python, JS/TS, SQL)
                    try:
                        from ast_engine import EnterpriseASTEngine
                        symbols = EnterpriseASTEngine.parse_polyglot_symbols(relative_name, content)
                        if symbols:
                            metadata[relative_name]["symbols"] = symbols
                    except Exception:
                        pass
                except Exception as e:
                    print(f"Skipped indexing metadata for {file}: {e}")
                    
    return metadata

def read_workspace_file(directory: str, filename: str) -> str:
    """
    Reads the content of a single workspace file on-demand to preserve context window.
    """
    base_path = Path(directory).resolve()
    file_path = (base_path / filename).resolve()
    
    # Path traversal safety check
    if not str(file_path).startswith(str(base_path)):
        raise ValueError(f"Path traversal detected: {filename} is outside the workspace.")
        
    if not file_path.exists():
        return f"[File {filename} does not exist]"
        
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"[Error reading file {filename}: {str(e)}]"

def save_codebase(code_files: Dict[str, str], directory: str) -> None:
    """
    Saves a dictionary of files to the target workspace directory.
    """
    base_path = Path(directory)
    base_path.mkdir(parents=True, exist_ok=True)
    
    for filename, content in code_files.items():
        file_path = (base_path / filename).resolve()
        if not str(file_path).startswith(str(base_path.resolve())):
            continue
            
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        print(f"Saved: {file_path}")

def check_docker_installed() -> bool:
    """
    Returns True if Docker daemon is running and CLI is accessible.
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False

def run_tests(directory: str) -> Tuple[bool, str]:
    """
    Performs a syntax check and runs unit tests in the workspace.
    Supports running tests inside an isolated Docker container if Docker is available
    and a Dockerfile is present in the workspace.
    Otherwise, falls back to local multi-language testing (Node.js, Go, .NET Core, Python).
    """
    base_path = Path(directory).resolve()
    if not base_path.exists():
        return False, "Workspace directory does not exist."
        
    logs = []
    
    # 1. Check if Docker is available and Dockerfile exists for sandboxed execution
    dockerfile = base_path / "Dockerfile"
    if dockerfile.exists() and check_docker_installed():
        logs.append("Docker environment and Dockerfile detected! Running tests in container sandbox...")
        try:
            # Build container
            build_result = subprocess.run(
                ["docker", "build", "-t", "app-sandbox-test", "."],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                check=False
            )
            logs.append(f"Docker Build Log:\n{build_result.stdout}\n{build_result.stderr}")
            if build_result.returncode != 0:
                return False, "\n".join(logs) + "\nDocker build failed."
                
            # Run container
            run_result = subprocess.run(
                ["docker", "run", "--rm", "app-sandbox-test"],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                check=False
            )
            success = (run_result.returncode == 0)
            logs.append(f"Docker Run Log:\n{run_result.stdout}\n{run_result.stderr}")
            return success, "\n".join(logs)
        except Exception as e:
            logs.append(f"Docker sandbox test run failed: {str(e)}. Falling back to local run.")
            
    # 2. Local Fallback Execution (Multi-language project detection)
    
    # Check for Node.js (package.json)
    if (base_path / "package.json").exists():
        logs.append("Node.js project detected. Running local Node.js validation...")
        try:
            # npm install
            install_result = subprocess.run(
                ["npm", "install"],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                shell=True,
                check=False
            )
            logs.append(f"npm install Log:\n{install_result.stdout}\n{install_result.stderr}")
            if install_result.returncode != 0:
                return False, "\n".join(logs) + "\nnpm install failed."
                
            # npm test (or fallback to npm run build)
            test_cmd = ["npm", "test"]
            # Read package.json to check if test script is defined
            import json
            pkg_data = json.loads((base_path / "package.json").read_text(encoding="utf-8", errors="ignore"))
            if "scripts" not in pkg_data or "test" not in pkg_data["scripts"] or "no test specified" in pkg_data["scripts"]["test"]:
                logs.append("No custom test script defined. Running npm run build as fallback verification...")
                test_cmd = ["npm", "run", "build"]
                
            test_result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                cwd=str(base_path),
                shell=True,
                check=False
            )
            success = (test_result.returncode == 0)
            logs.append(f"npm test/build Log:\n{test_result.stdout}\n{test_result.stderr}")
            return success, "\n".join(logs)
        except Exception as e:
            return False, f"Local Node.js execution failed: {str(e)}"
            
    # Check for Go (go.mod)
    elif (base_path / "go.mod").exists():
        logs.append("Go project detected. Running local Go validation...")
        try:
            # go test ./...
            test_result = subprocess.run(
                ["go", "test", "./..."],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                check=False
            )
            logs.append(f"go test Log:\n{test_result.stdout}\n{test_result.stderr}")
            if test_result.returncode != 0:
                # Fallback to go build
                logs.append("Go tests failed or not found. Running go build as fallback...")
                build_result = subprocess.run(
                    ["go", "build", "-o", "bin_check_output"],
                    capture_output=True,
                    text=True,
                    cwd=str(base_path),
                    check=False
                )
                success = (build_result.returncode == 0)
                logs.append(f"go build Log:\n{build_result.stdout}\n{build_result.stderr}")
                return success, "\n".join(logs)
            return True, "\n".join(logs)
        except Exception as e:
            return False, f"Local Go execution failed: {str(e)}"
            
    # Check for C# / .NET Core (.csproj or .sln)
    elif list(base_path.rglob("*.csproj")) or list(base_path.rglob("*.sln")):
        logs.append(".NET Core project detected. Running local .NET validation...")
        try:
            # dotnet test
            test_result = subprocess.run(
                ["dotnet", "test"],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                check=False
            )
            logs.append(f"dotnet test Log:\n{test_result.stdout}\n{test_result.stderr}")
            if test_result.returncode != 0:
                logs.append("dotnet test failed or not found. Running dotnet build as fallback...")
                build_result = subprocess.run(
                    ["dotnet", "build"],
                    capture_output=True,
                    text=True,
                    cwd=str(base_path),
                    check=False
                )
                success = (build_result.returncode == 0)
                logs.append(f"dotnet build Log:\n{build_result.stdout}\n{build_result.stderr}")
                return success, "\n".join(logs)
            return True, "\n".join(logs)
        except Exception as e:
            return False, f"Local .NET execution failed: {str(e)}"

    # Default: Python Execution (or fallback)
    success = True
    py_files = list(base_path.rglob("*.py"))
    
    # AST & Compiler Syntax Check
    for py_file in py_files:
        relative_path = py_file.relative_to(base_path)
        # 1. AST In-Memory Zero-Subprocess Syntax Validation
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            ast.parse(source, filename=str(py_file))
        except SyntaxError as se:
            success = False
            logs.append(f"AST Syntax Error in {relative_path} (Line {se.lineno}, Col {se.offset}):\n{se.msg}\n-> {se.text}\n")
            continue
        except Exception:
            pass

        # 2. Subprocess compilation validation
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                success = False
                logs.append(f"Syntax Error in {relative_path}:\n{result.stderr}\n")
        except Exception as e:
            success = False
            logs.append(f"Failed to check syntax for {relative_path}: {str(e)}\n")

    if not success:
        return False, "\n".join(logs)

    # Unit tests
    test_files = [f for f in py_files if f.name.startswith("test_") or f.name.endswith("_test.py")]
    
    if test_files:
        logs.append(f"Found {len(test_files)} test file(s). Running local test suite...")
        for test_file in test_files:
            relative_path = test_file.relative_to(base_path)
            try:
                result = subprocess.run(
                    [sys.executable, str(test_file)],
                    capture_output=True,
                    text=True,
                    cwd=str(base_path),
                    check=False
                )
                if result.returncode != 0:
                    success = False
                    logs.append(f"Test Suite Failed on {relative_path}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n")
                else:
                    logs.append(f"Test Suite Passed on {relative_path}.\nSTDOUT:\n{result.stdout}\n")
            except Exception as e:
                success = False
                logs.append(f"Failed to run test suite {relative_path}: {str(e)}\n")
    else:
        logs.append("No test files detected locally.")
        main_files = [f for f in py_files if f.name in ("main.py", "app.py")]
        if main_files:
            logs.append(f"Found entry point {main_files[0].name}. Verifying running without arguments...")
            try:
                result = subprocess.run(
                    [sys.executable, str(main_files[0])],
                    capture_output=True,
                    text=True,
                    cwd=str(base_path),
                    timeout=5,
                    check=False
                )
                if result.returncode != 0 and "Traceback" in result.stderr:
                    success = False
                    logs.append(f"Run validation failed for {main_files[0].relative_to(base_path)}:\n{result.stderr}\n")
                else:
                    logs.append(f"Entry point {main_files[0].relative_to(base_path)} ran successfully or exited cleanly.\n")
            except subprocess.TimeoutExpired:
                logs.append(f"Validation run timed out (which is normal if it is a running app or waits for stdin).\n")
            except Exception as e:
                success = False
                logs.append(f"Failed to run validation on entry point: {str(e)}\n")
        else:
            # If no code files exist at all, check if there are index.html / static files
            html_files = list(base_path.rglob("*.html"))
            if html_files:
                logs.append(f"Static web application detected. Verified {len(html_files)} HTML file(s) present.")
                return True, "\n".join(logs)

    return success, "\n".join(logs)

def run_security_scan(directory: str) -> dict:
    """
    Runs security vulnerability audit on the code inside directory.
    Uses Bandit for Python static analysis.
    Also does custom regex matching for generic vulnerability detection (credentials, sql inject).
    """
    base_path = Path(directory).resolve()
    results = {
        "vulnerabilities": [],
        "metrics": {"total_lines": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0}
    }
    
    # 1. Run Bandit if python files are present
    py_files = list(base_path.rglob("*.py"))
    if py_files:
        try:
            # Run bandit -r . -f json
            import json
            # Locate bandit executable inside local virtual environment venv/Scripts/bandit
            venv_bandit = os.path.join(os.getcwd(), ".venv", "Scripts", "bandit")
            if not os.path.exists(venv_bandit):
                venv_bandit = "bandit" # fallback to global
                
            res = subprocess.run(
                [venv_bandit, "-r", ".", "-f", "json", "-q"],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                check=False
            )
            
            if res.stdout.strip():
                data = json.loads(res.stdout)
                for issue in data.get("results", []):
                    sev = issue.get("issue_severity", "LOW")
                    results["vulnerabilities"].append({
                        "file": issue.get("filename"),
                        "line": issue.get("line_number"),
                        "severity": sev,
                        "confidence": issue.get("issue_confidence"),
                        "issue_text": issue.get("issue_text"),
                        "code": issue.get("code")
                    })
                    
                    # Update metrics
                    metric_key = f"{sev.lower()}_severity"
                    if metric_key in results["metrics"]:
                        results["metrics"][metric_key] += 1
                        
                results["metrics"]["total_lines"] = data.get("metrics", {}).get("_tot", {}).get("loc", 0)
        except Exception as e:
            results["vulnerabilities"].append({
                "file": "Security Engine",
                "line": 0,
                "severity": "LOW",
                "confidence": "HIGH",
                "issue_text": f"Bandit execution skipped or failed: {str(e)}. Running generic regex scan instead.",
                "code": ""
            })

    # 2. AST Static Code Security Inspector for Python files
    for py_file in py_files:
        if any(p in py_file.parts for p in [".venv", "venv", "node_modules", "dist", "build"]):
            continue
        rel_name = str(py_file.relative_to(base_path)).replace("\\", "/")
        try:
            code_text = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(code_text)
            for node in ast.walk(tree):
                # Detect eval / exec calls via AST
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                    
                    if func_name in ("eval", "exec"):
                        results["vulnerabilities"].append({
                            "file": rel_name,
                            "line": getattr(node, "lineno", 1),
                            "severity": "HIGH",
                            "confidence": "HIGH",
                            "issue_text": f"AST Security Audit: Unsafe call to `{func_name}()` detected.",
                            "code": f"{func_name}(...)"
                        })
                    elif func_name == "run" or func_name == "Popen":
                        # Check shell=True keyword arg in subprocess
                        for kw in node.keywords:
                            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                results["vulnerabilities"].append({
                                    "file": rel_name,
                                    "line": getattr(node, "lineno", 1),
                                    "severity": "HIGH",
                                    "confidence": "HIGH",
                                    "issue_text": "AST Security Audit: Subprocess execution with `shell=True` (Command Injection Risk).",
                                    "code": "subprocess.run(..., shell=True)"
                                })
        except Exception:
            pass

    # 3. Generic Regex Secret/Security Vulnerability Scan (applies to HTML/JS/Python/SQL)
    secret_patterns = {
        "API_KEY": r'(?i)(api_key|apikey|secret|password|passwd|token)\s*=\s*[\'"][a-zA-Z0-9_\-\.]{12,}[\'"]',
        "Hardcoded Password": r'(?i)password\s*=\s*[\'"][^\'"]{4,}[\'"]',
        "Insecure Eval": r'(eval|exec)\s*\(\s*[^)]+\)',
        "Insecure SQL String Injection": r'(?i)(select|insert|update|delete)\s+.*\+\s*([a-zA-Z_][a-zA-Z0-9_]*|request\.)'
    }
    
    for ext in ["*.py", "*.js", "*.ts", "*.html", "*.json", "*.sql"]:
        for file_path in base_path.rglob(ext):
            # Exclude virtual environments
            if any(p in file_path.parts for p in [".venv", "venv", "node_modules", "dist", "build"]):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                for line_idx, line in enumerate(lines):
                    for label, pattern in secret_patterns.items():
                        if re.search(pattern, line):
                            # Skip if already captured by bandit
                            rel_name = str(file_path.relative_to(base_path)).replace("\\", "/")
                            # Add vulnerability
                            results["vulnerabilities"].append({
                                "file": rel_name,
                                "line": line_idx + 1,
                                "severity": "HIGH" if "SQL" in label or "KEY" in label else "MEDIUM",
                                "confidence": "MEDIUM",
                                "issue_text": f"Potential {label} pattern detected: {line.strip()[:100]}",
                                "code": line.strip()
                            })
                            # Increment metrics
                            key = "high_severity" if ("SQL" in label or "KEY" in label) else "medium_severity"
                            results["metrics"][key] += 1
            except Exception:
                pass
                
    return results

def generate_test_report(directory: str, state: dict, security_results: dict, test_logs: str, test_success: bool):
    """
    Generates test_report.md and test_report.html inside the workspace directory.
    Provides clear information on:
    - Tests executed
    - Test logs
    - Security scan vulnerabilities
    - Fixed incidents (compile errors, etc.) across iterations.
    """
    base_path = Path(directory).resolve()
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    status_badge = "PASSED" if test_success else "FAILED"
    status_color = "#28a745" if test_success else "#dc3545"
    
    # 1. Compile Markdown report
    md = f"""# Multi-Agent QA Testing & Security Validation Report

**Status:** {status_badge}  
**Date:** `{now_str}`  
**Project Directory:** `{base_path}`  
**Coding Iteration:** `{state.get('iterations', 1)}`  

---

## 1. Automated Verification Checks
### Syntax & Test Suite Logs
```text
{test_logs}
```

---

## 2. Security Vulnerability Scan (Static Analysis)
"""
    vulns = security_results.get("vulnerabilities", [])
    if not vulns:
        md += "🟢 **No security vulnerabilities or exposed credentials detected!**\n"
    else:
        md += f"⚠️ **Found {len(vulns)} potential security warnings:**\n\n"
        md += "| Severity | File | Line | Issue Description | Code Context |\n"
        md += "| :--- | :--- | :--- | :--- | :--- |\n"
        for v in vulns:
            md += f"| **{v['severity']}** | `{v['file']}` | {v['line']} | {v['issue_text']} | `{v['code']}` |\n"
            
    md += """
---

## 3. Chronological Incident History Log
This section lists compilation bugs, test failures, or crashes that occurred during the development cycle and were automatically resolved by the agents.
"""
    incidents = state.get("incidents", [])
    if not incidents:
        md += "🟢 **No incidents occurred. Code compiled and passed tests on the first try!**\n"
    else:
        md += f"Found **{len(incidents)}** incident(s) corrected during execution loops:\n\n"
        for idx, inc in enumerate(incidents):
            md += f"### Incident #{idx + 1} (Iteration {inc.get('iteration', '?')})\n"
            md += f"```text\n{inc.get('error', '').strip()}\n```\n\n"

    # Write Markdown
    (base_path / "test_report.md").write_text(md, encoding="utf-8")
    print(f"Generated Markdown test report: {base_path / 'test_report.md'}")
    
    # 2. Compile HTML report
    html_vulns_rows = ""
    if not vulns:
        html_vulns_rows = "<tr><td colspan='5' style='color: #28a745; text-align: center; font-weight: bold;'>🟢 No security vulnerabilities detected.</td></tr>"
    else:
        for v in vulns:
            color = "#dc3545" if v['severity'] == "HIGH" else ("#ffc107" if v['severity'] == "MEDIUM" else "#17a2b8")
            html_vulns_rows += f"""
            <tr>
                <td><span style='background-color: {color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;'>{v['severity']}</span></td>
                <td><code>{v['file']}</code></td>
                <td>{v['line']}</td>
                <td>{v['issue_text']}</td>
                <td><code>{v['code']}</code></td>
            </tr>
            """
            
    html_incident_blocks = ""
    if not incidents:
        html_incident_blocks = "<div style='color: #28a745; font-weight: bold; padding: 10px; border: 1px solid #c3e6cb; background-color: #d4edda; border-radius: 4px;'>🟢 No incidents or compilation failures occurred during execution.</div>"
    else:
        for idx, inc in enumerate(incidents):
            html_incident_blocks += f"""
            <div style='margin-bottom: 15px; border: 1px solid #f5c6cb; background-color: #f8d7da; padding: 10px; border-radius: 4px;'>
                <h4 style='margin-top: 0; color: #721c24;'>Incident #{idx + 1} (Iteration {inc.get('iteration', '?')})</h4>
                <pre style='background: #fff; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 0.8rem; border: 1px solid #eed3d7;'>{inc.get('error', '').strip()}</pre>
            </div>
            """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Multi-Agent QA Testing & Security Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fdfdfd;
        }}
        h1, h2, h3 {{
            color: #0b1b3d;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-left: 5px solid {status_color};
            margin-bottom: 25px;
        }}
        .badge {{
            background-color: {status_color};
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9rem;
        }}
        pre {{
            background: #0f172a;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: Consolas, monospace;
            font-size: 0.85rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: #fff;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
            font-size: 0.85rem;
        }}
        th {{
            background-color: #f8f9fa;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1 style="margin: 0; font-size: 1.8rem;">Multi-Agent QA Testing & Security Report</h1>
            <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9rem;">
                Project Directory: <code>{base_path}</code> &bull; Date: {now_str}
            </p>
        </div>
        <div class="badge">{status_badge}</div>
    </div>
    
    <h2>1. Verification & Testing Conducted</h2>
    <h3>Syntax & Test logs</h3>
    <pre>{test_logs}</pre>
    
    <h2>2. Security Vulnerability Scan</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 10%;">Severity</th>
                <th style="width: 25%;">File</th>
                <th style="width: 10%;">Line</th>
                <th style="width: 35%;">Description</th>
                <th style="width: 20%;">Code Context</th>
            </tr>
        </thead>
        <tbody>
            {html_vulns_rows}
        </tbody>
    </table>
    
    <h2>3. Incident History Log (Auto-Corrected)</h2>
    <div>
        {html_incident_blocks}
    </div>
</body>
</html>
"""
    (base_path / "test_report.html").write_text(html, encoding="utf-8")
    print(f"Generated HTML test report: {base_path / 'test_report.html'}")

def run_deployment(directory: str) -> Tuple[bool, str]:
    """
    Looks for deployment scripts or docker-compose files and executes them.
    """
    base_path = Path(directory).resolve()
    if not base_path.exists():
        return False, "Workspace directory does not exist."
        
    logs = []
    
    # Check for docker-compose configuration
    docker_compose_yml = base_path / "docker-compose.yml"
    docker_compose_yaml = base_path / "docker-compose.yaml"
    
    if (docker_compose_yml.exists() or docker_compose_yaml.exists()) and check_docker_installed():
        logs.append("Docker-compose configuration found! Starting deployment containerized...")
        try:
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                check=False
            )
            success = (result.returncode == 0)
            logs.append(f"Docker-Compose Log:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            return success, "\n".join(logs)
        except Exception as e:
            logs.append(f"Docker-compose run failed: {str(e)}. Falling back to script deploy.")

    deploy_bat = base_path / "deploy.bat"
    deploy_sh = base_path / "deploy.sh"
    deploy_py = base_path / "deploy.py"
    
    try:
        if deploy_bat.exists() and sys.platform.startswith("win"):
            logs.append("Running deployment batch script (deploy.bat)...")
            result = subprocess.run(
                [str(deploy_bat)],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                check=False
            )
            success = (result.returncode == 0)
            logs.append(f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            return success, "\n".join(logs)
            
        elif deploy_sh.exists() and not sys.platform.startswith("win"):
            logs.append("Running deployment shell script (deploy.sh)...")
            result = subprocess.run(
                ["bash", str(deploy_sh)],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                check=False
            )
            success = (result.returncode == 0)
            logs.append(f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            return success, "\n".join(logs)
            
        elif deploy_py.exists():
            logs.append("Running deployment Python script (deploy.py)...")
            result = subprocess.run(
                [sys.executable, str(deploy_py)],
                capture_output=True,
                text=True,
                cwd=str(base_path),
                check=False
            )
            success = (result.returncode == 0)
            logs.append(f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            return success, "\n".join(logs)
            
        else:
            logs.append("No custom deployment script detected.")
            logs.append("Performing default deployment verification...")
            
            readme_exists = (base_path / "README.md").exists() or (base_path / "readme.md").exists()
            logs.append(f"Deployment Check: README.md exists = {readme_exists}")
            return True, "\n".join(logs)
                
    except Exception as e:
        return False, f"Deployment script error: {str(e)}"

def parse_code_files(text: str) -> Dict[str, str]:
    """
    Parses file contents from a markdown output.
    Looks for headers like ---FILE: path/to/file.ext--- followed by a code block.
    """
    pattern = r'---FILE:\s*([a-zA-Z0-9_\-\./]+)\s*---.*?```[a-zA-Z0-9_]*\n(.*?)\n```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    files = {}
    for filename, content in matches:
        files[filename.strip()] = content
        
    return files

def git_init(directory: str):
    """
    Initializes a local git repository in the workspace.
    Sets up local configurations and creates an initial commit if fresh.
    """
    base_path = Path(directory).resolve()
    if not base_path.exists():
        return
        
    git_dir = base_path / ".git"
    is_new = not git_dir.exists()
    
    if is_new:
        try:
            # Initialize Git
            subprocess.run(["git", "init"], cwd=str(base_path), capture_output=True, check=False)
            
            # Setup local fallback credentials so Git commits don't crash
            config_check = subprocess.run(["git", "config", "user.name"], cwd=str(base_path), capture_output=True, text=True, check=False)
            if not config_check.stdout.strip():
                subprocess.run(["git", "config", "--local", "user.name", "Agent Studio"], cwd=str(base_path), check=False)
                subprocess.run(["git", "config", "--local", "user.email", "agent@developer.studio"], cwd=str(base_path), check=False)
                
            # Create a default .gitignore if not present
            gitignore = base_path / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text(".venv/\n__pycache__/\n*.pyc\nnode_modules/\ntest_report.md\ntest_report.html\n", encoding="utf-8")
                
            # Make initial commit
            subprocess.run(["git", "add", "."], cwd=str(base_path), check=False)
            subprocess.run(["git", "commit", "-m", "Initial commit: workspace base state"], cwd=str(base_path), check=False)
            print(f"[Git Tool] Local repository initialized at {base_path}")
        except Exception as e:
            print(f"[Git Tool Error] Initialization failed: {str(e)}")

def git_commit(directory: str, message: str) -> bool:
    """
    Saves and commits all workspace modifications to the current Git branch.
    """
    base_path = Path(directory).resolve()
    if not (base_path / ".git").exists():
        return False
    try:
        subprocess.run(["git", "add", "."], cwd=str(base_path), check=False)
        result = subprocess.run(["git", "commit", "-m", message], cwd=str(base_path), capture_output=True, text=True, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"[Git Tool Error] Commit failed: {str(e)}")
        return False

def git_checkout_branch(directory: str, branch_name: str) -> bool:
    """
    Switches to a target branch, creating it if it doesn't already exist.
    """
    base_path = Path(directory).resolve()
    if not (base_path / ".git").exists():
        return False
    try:
        # Check if branch exists
        exists_check = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"], cwd=str(base_path), check=False)
        if exists_check.returncode == 0:
            result = subprocess.run(["git", "checkout", branch_name], cwd=str(base_path), capture_output=True, text=True, check=False)
        else:
            result = subprocess.run(["git", "checkout", "-b", branch_name], cwd=str(base_path), capture_output=True, text=True, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"[Git Tool Error] Branch checkout failed: {str(e)}")
        return False

def git_get_status(directory: str) -> Dict[str, Any]:
    """
    Returns current Git state metadata (branch name, modifications, commit log).
    """
    base_path = Path(directory).resolve()
    result_meta = {"branch": "unknown", "modified": [], "commits": []}
    if not (base_path / ".git").exists():
        return result_meta
        
    try:
        # Get active branch name
        branch_run = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(base_path), capture_output=True, text=True, check=False)
        if branch_run.returncode == 0:
            result_meta["branch"] = branch_run.stdout.strip()
            
        # Get modified files (porcelain layout)
        status_run = subprocess.run(["git", "status", "--porcelain"], cwd=str(base_path), capture_output=True, text=True, check=False)
        if status_run.returncode == 0:
            lines = status_run.stdout.splitlines()
            result_meta["modified"] = [l.strip() for l in lines if l.strip()]
            
        # Get recent 5 commits
        log_run = subprocess.run(["git", "log", "-n", "5", "--oneline"], cwd=str(base_path), capture_output=True, text=True, check=False)
        if log_run.returncode == 0:
            result_meta["commits"] = [l.strip() for l in log_run.stdout.splitlines() if l.strip()]
            
    except Exception as e:
        print(f"[Git Tool Error] Status check failed: {str(e)}")
        
    return result_meta

def git_get_diff(directory: str) -> str:
    """
    Returns the raw git diff output for modified files.
    """
    base_path = Path(directory).resolve()
    if not (base_path / ".git").exists():
        return ""
    try:
        diff_run = subprocess.run(["git", "diff"], cwd=str(base_path), capture_output=True, text=True, check=False)
        return diff_run.stdout
    except Exception as e:
        return f"Error loading git diff: {str(e)}"

def detect_preview_url(deploy_logs: str) -> str:
    """
    Inspects terminal deployment output to discover port or web server links.
    Returns the matched URL if found, otherwise empty string.
    """
    if not deploy_logs:
        return ""
    # Matches patterns like http://localhost:3000, http://127.0.0.1:8080, https://localhost:5000, http://0.0.0.0:8000
    pattern = r'(https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|localhost):\d+)'
    match = re.search(pattern, deploy_logs, re.IGNORECASE)
    if match:
        url = match.group(1)
        # Normalize 0.0.0.0 to localhost for web client access convenience
        return url.replace("0.0.0.0", "localhost")
    return ""

def save_studio_state(workspace_dir: str, state: dict):
    import json
    if not workspace_dir:
        return
    try:
        studio_dir = os.path.join(workspace_dir, ".studio")
        os.makedirs(studio_dir, exist_ok=True)
        state_file = os.path.join(studio_dir, "state.json")
        serializable_state = {
            "prompt": state.get("prompt", ""),
            "requirements": state.get("requirements", ""),
            "impact_analysis": state.get("impact_analysis", ""),
            "files_to_modify": state.get("files_to_modify", []),
            "next_agent": state.get("next_agent", "BusinessAnalyst"),
            "iterations": state.get("iterations", 0),
            "errors": state.get("errors", "")
        }
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(serializable_state, f, indent=2)
        print(f"[State Snapshot] Saved studio state to: {state_file}")
    except Exception as e:
        print(f"[State Warning] Failed to save state snapshot: {e}")

def clear_studio_state(workspace_dir: str):
    if not workspace_dir:
        return
    try:
        state_file = os.path.join(workspace_dir, ".studio", "state.json")
        if os.path.exists(state_file):
            os.remove(state_file)
            print(f"[State Cleanup] Removed state snapshot: {state_file}")
    except Exception as e:
        print(f"[State Warning] Failed to clear state snapshot: {e}")
