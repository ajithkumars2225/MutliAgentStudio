import ast
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple

class EnterpriseASTEngine:
    """
    Enterprise AST Engine (v2)
    Provides Polyglot AST parsing, Symbol Dependency Graphs,
    Call Graph analysis, and Structural AST Refactoring Diffing.
    """
    
    @staticmethod
    def extract_python_symbols(source_code: str) -> Dict[str, Any]:
        """
        Parses Python AST to extract classes, functions, signature parameters, imports, and docstrings.
        """
        result = {
            "classes": [],
            "functions": [],
            "imports": [],
            "has_docstrings": False
        }
        try:
            tree = ast.parse(source_code)
            
            # Module level docstring
            if ast.get_docstring(tree):
                result["has_docstrings"] = True
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    result["classes"].append({
                        "name": node.name,
                        "methods": methods,
                        "line": node.lineno
                    })
                elif isinstance(node, ast.FunctionDef):
                    args = [a.arg for a in node.args.args]
                    result["functions"].append({
                        "name": node.name,
                        "params": args,
                        "line": node.lineno,
                        "returns": ast.unparse(node.returns) if getattr(node, 'returns', None) else None
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        result["imports"].append(node.module)
        except Exception:
            pass
            
        return result

    @staticmethod
    def extract_javascript_symbols(source_code: str) -> Dict[str, Any]:
        """
        Polyglot AST Parser for JavaScript / TypeScript files.
        Extracts functions, classes, exports, and imports using structural regex AST tokens.
        """
        functions = re.findall(r'function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)', source_code)
        arrow_funcs = re.findall(r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*\(([^)]*)\)\s*=>', source_code)
        classes = re.findall(r'class\s+([a-zA-Z0-9_$]+)', source_code)
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', source_code)
        
        all_funcs = []
        for name, params in functions:
            all_funcs.append({"name": name, "params": [p.strip() for p in params.split(',') if p.strip()]})
        for name, params in arrow_funcs:
            all_funcs.append({"name": name, "params": [p.strip() for p in params.split(',') if p.strip()]})

        return {
            "classes": [{"name": c} for c in classes],
            "functions": all_funcs,
            "imports": list(set(imports))
        }

    @staticmethod
    def extract_sql_symbols(source_code: str) -> Dict[str, Any]:
        """
        Polyglot AST Parser for SQL files.
        Extracts tables created/altered and query operations.
        """
        tables = re.findall(r'(?i)(?:CREATE\s+TABLE|ALTER\s+TABLE|INTO|FROM)\s+([a-zA-Z0-9_]+)', source_code)
        ops = re.findall(r'(?i)\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP)\b', source_code)
        return {
            "tables": list(set(tables)),
            "operations": list(set(ops))
        }

    @classmethod
    def parse_polyglot_symbols(cls, filename: str, content: str) -> Dict[str, Any]:
        """
        Universal entrypoint for Polyglot AST analysis (Python, JS/TS, SQL).
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".py":
            return cls.extract_python_symbols(content)
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            return cls.extract_javascript_symbols(content)
        elif ext == ".sql":
            return cls.extract_sql_symbols(content)
        return {}

    @classmethod
    def build_workspace_call_graph(cls, workspace_directory: str) -> Dict[str, List[str]]:
        """
        Enterprise Dependency Call Graph Engine.
        Maps symbol dependencies across workspace files so Impact Analyzer understands cross-file impacts.
        """
        base = Path(workspace_directory)
        if not base.exists():
            return {}

        file_symbols = {}
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}]
            for file in files:
                filepath = Path(root) / file
                rel_path = str(filepath.relative_to(base)).replace("\\", "/")
                ext = filepath.suffix.lower()
                if ext in [".py", ".js", ".ts", ".sql"]:
                    try:
                        content = filepath.read_text(encoding="utf-8", errors="ignore")
                        file_symbols[rel_path] = cls.parse_polyglot_symbols(rel_path, content)
                    except Exception:
                        pass

        # Build cross-file call dependencies
        call_graph = {}
        all_funcs = {}
        for fname, syms in file_symbols.items():
            for f in syms.get("functions", []):
                all_funcs[f["name"]] = fname

        for fname, syms in file_symbols.items():
            call_graph[fname] = []
            imports = syms.get("imports", [])
            for imp in imports:
                for target_file in file_symbols.keys():
                    if imp in target_file or target_file.startswith(imp):
                        if target_file not in call_graph[fname] and target_file != fname:
                            call_graph[fname].append(target_file)

        return call_graph

    @classmethod
    def analyze_ast_refactoring_diff(cls, old_code: str, new_code: str) -> List[str]:
        """
        Structural AST Diff Inspector.
        Detects breaking changes in public function parameters or removed classes between coder iterations.
        """
        warnings = []
        try:
            old_syms = cls.extract_python_symbols(old_code)
            new_syms = cls.extract_python_symbols(new_code)
            
            old_funcs = {f["name"]: f["params"] for f in old_syms["functions"]}
            new_funcs = {f["name"]: f["params"] for f in new_syms["functions"]}
            
            # Removed functions
            for f_name in old_funcs:
                if f_name not in new_funcs:
                    warnings.append(f"Function `{f_name}` was removed in refactoring.")
                else:
                    # Parameter signature mismatch
                    if old_funcs[f_name] != new_funcs[f_name]:
                        warnings.append(f"Function signature changed for `{f_name}`: old params {old_funcs[f_name]} -> new params {new_funcs[f_name]}")
                        
            # Removed classes
            old_classes = {c["name"] for c in old_syms["classes"]}
            new_classes = {c["name"] for c in new_syms["classes"]}
            for c_name in old_classes:
                if c_name not in new_classes:
                    warnings.append(f"Class `{c_name}` was removed in refactoring.")
                    
        except Exception as e:
            warnings.append(f"AST diff analysis warning: {str(e)}")

        return warnings

    @classmethod
    def get_workspace_symbol_index(cls, workspace_directory: str) -> Dict[str, Any]:
        """
        Builds a comprehensive workspace-wide Symbol Index mapping every function,
        class, method, and table back to its defining file and line number.
        """
        base = Path(workspace_directory)
        if not base.exists():
            return {}

        symbol_index = {
            "functions": {},
            "classes": {},
            "tables": {}
        }

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}]
            for file in files:
                filepath = Path(root) / file
                rel_path = str(filepath.relative_to(base)).replace("\\", "/")
                ext = filepath.suffix.lower()
                if ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".sql"]:
                    try:
                        content = filepath.read_text(encoding="utf-8", errors="ignore")
                        syms = cls.parse_polyglot_symbols(rel_path, content)
                        
                        for f in syms.get("functions", []):
                            fname = f["name"]
                            symbol_index["functions"][fname] = {
                                "file": rel_path,
                                "line": f.get("line"),
                                "params": f.get("params", [])
                            }
                        for c in syms.get("classes", []):
                            cname = c["name"]
                            symbol_index["classes"][cname] = {
                                "file": rel_path,
                                "line": c.get("line"),
                                "methods": c.get("methods", [])
                            }
                        for t in syms.get("tables", []):
                            symbol_index["tables"][t] = {
                                "file": rel_path
                            }
                    except Exception:
                        pass

        return symbol_index

