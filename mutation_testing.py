import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any

class CodeMutationOperator(ast.NodeTransformer):
    """
    AST Node Transformer that mutates Python code operators.
    """
    def __init__(self):
        self.mutations_count = 0

    def visit_Compare(self, node):
        self.generic_visit(node)
        new_ops = []
        for op in node.ops:
            if isinstance(op, ast.Eq):
                new_ops.append(ast.NotEq())
                self.mutations_count += 1
            elif isinstance(op, ast.NotEq):
                new_ops.append(ast.Eq())
                self.mutations_count += 1
            elif isinstance(op, ast.Gt):
                new_ops.append(ast.LtE())
                self.mutations_count += 1
            else:
                new_ops.append(op)
        node.ops = new_ops
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Add):
            node.op = ast.Sub()
            self.mutations_count += 1
        elif isinstance(node.op, ast.Sub):
            node.op = ast.Add()
            self.mutations_count += 1
        return node

class MutationTestingEngine:
    """
    Enterprise Mutation Testing & Test Suite Quality Assurance Engine.
    Introduces controlled AST mutations into target code files to verify
    if unit test suites catch injected logic bugs.
    """

    @classmethod
    def mutate_code_ast(cls, source_code: str) -> str:
        """
        Applies operator mutations to Python AST source code.
        """
        try:
            tree = ast.parse(source_code)
            transformer = CodeMutationOperator()
            mutated_tree = transformer.visit(tree)
            ast.fix_missing_locations(mutated_tree)
            return ast.unparse(mutated_tree)
        except Exception:
            return source_code

    @classmethod
    def run_mutation_test_suite(cls, workspace_directory: str, target_file: str, test_file: str) -> Dict[str, Any]:
        """
        Runs mutation testing: mutates target_file, executes test_file, and checks if test suite fails (mutant killed).
        """
        base = Path(workspace_directory).resolve()
        target_path = base / target_file
        test_path = base / test_file

        if not target_path.exists() or not test_path.exists():
            return {"status": "skipped", "reason": "Target or test file missing."}

        original_code = target_path.read_text(encoding="utf-8", errors="ignore")
        mutated_code = cls.mutate_code_ast(original_code)

        if original_code == mutated_code:
            return {"status": "skipped", "reason": "No mutable operators found."}

        try:
            # Write mutant
            target_path.write_text(mutated_code, encoding="utf-8")

            # Run test on mutant with 8s timeout to prevent hanging on infinite loops
            try:
                res = subprocess.run(
                    [sys.executable, str(test_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(base),
                    check=False,
                    timeout=8
                )
                mutant_killed = res.returncode != 0
            except subprocess.TimeoutExpired:
                mutant_killed = True

            return {
                "status": "completed",
                "mutant_killed": mutant_killed,
                "score": 100 if mutant_killed else 0,
                "summary": "Mutant killed! Test suite successfully detected injected code flaw." if mutant_killed else "Mutant survived! Test suite missed injected bug."
            }
        finally:
            # Always restore original code
            target_path.write_text(original_code, encoding="utf-8")
