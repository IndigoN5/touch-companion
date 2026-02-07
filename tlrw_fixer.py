#!/usr/bin/env python3
"""
TLRW REDUNDANCY CASCADE FIXER v2.0
Portable single-file code repair system using Think-Learn-Reflect-Write methodology
with Triple Redundancy validation, Agent Discovery, and Self-Healing capability.

Author: NUVABASE Professional Consulting Associate
Version: 2.0.0
"""

import ast
import sys
import os
import hashlib
import difflib
import re
import json
import logging
import argparse
import subprocess
import shutil
import textwrap
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "tlrw_fixer.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("tlrw")

# ---------------------------------------------------------------------------
# Version & Constants
# ---------------------------------------------------------------------------

__version__ = "2.0.0"
DIVERGENCE_THRESHOLD = 50
SELF_HEAL_INTERVAL = 100  # trigger self-heal every N external runs

# ---------------------------------------------------------------------------
# Core Fixer
# ---------------------------------------------------------------------------

class TLRWFixer:
    """
    Core TLRW Redundancy Cascade Fixer.

    Phases:
        Think  -> Atomic issue detection (surface, structural, systemic)
        Learn  -> Convention extraction and pattern analysis
        Reflect -> Triple redundancy fix generation with divergence scoring
        Agent  -> Cross-validation and golden fix selection
        Write  -> Synthesis, reporting, and output
    """

    def __init__(self, source_code: str):
        self.original = source_code
        self.primer = source_code
        self.signature = self._generate_signature()
        self.atomic_issues: List[Dict] = []
        self.redundant_fixes: Dict[str, str] = {}
        self.run_count = 0

    # ------------------------------------------------------------------
    # Signature
    # ------------------------------------------------------------------

    def _generate_signature(self) -> str:
        return hashlib.sha256(self.original.encode()).hexdigest()[:12]

    # ==================================================================
    # PHASE 1 — THINK
    # ==================================================================

    def think(self) -> Dict:
        """LEVEL T: Atomic deconstruction — detect all issue types."""
        issues: List[Dict] = []

        # --- Gate 1: Syntax parse ---
        tree = None
        try:
            tree = ast.parse(self.original)
        except SyntaxError as e:
            issues.append({
                "type": "syntax",
                "line": e.lineno,
                "text": str(e.text),
                "fix_type": "surface",
                "detail": f"SyntaxError: {e.msg}",
            })

        # --- Gate 2: Heuristic line-level detection ---
        lines = self.original.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Bare excepts
            if re.match(r"^\s*except\s*:", line):
                issues.append({"type": "structural", "line": i,
                               "text": "Bare except clause", "fix_type": "structural"})

            # Mutable default arguments
            if re.match(r"^\s*def\s+\w+\(.*=\s*(\[\]|\{\})", line):
                issues.append({"type": "systemic", "line": i,
                               "text": "Mutable default argument", "fix_type": "systemic"})

            # Python 2 print statements
            if re.match(r"^\s*print\s+[^(]", line):
                issues.append({"type": "syntax", "line": i,
                               "text": "Python 2 print statement", "fix_type": "surface"})

            # == None / != None comparisons
            if "== None" in line or "!= None" in line:
                issues.append({"type": "surface", "line": i,
                               "text": "Identity comparison with None", "fix_type": "surface"})

            # == True / == False comparisons
            if "== True" in line or "== False" in line:
                issues.append({"type": "surface", "line": i,
                               "text": "Equality comparison with boolean", "fix_type": "surface"})

            # Wildcard imports
            if re.match(r"^\s*from\s+\w+\s+import\s+\*", line):
                issues.append({"type": "structural", "line": i,
                               "text": "Wildcard import", "fix_type": "structural"})

            # Global statement usage
            if re.match(r"^\s*global\s+", line):
                issues.append({"type": "systemic", "line": i,
                               "text": "Global variable usage", "fix_type": "systemic"})

            # Semicolon-separated statements
            if ";" in stripped and not stripped.startswith("#") and not stripped.startswith(("'", '"')):
                parts = stripped.split(";")
                if len(parts) > 1 and parts[1].strip():
                    issues.append({"type": "surface", "line": i,
                                   "text": "Semicolon-separated statements", "fix_type": "surface"})

            # Trailing whitespace
            if line != line.rstrip() and line.strip():
                issues.append({"type": "surface", "line": i,
                               "text": "Trailing whitespace", "fix_type": "surface"})

            # Magic numbers in comparisons / assignments (outside index)
            if re.search(r"[=<>!]=?\s+\d{2,}", stripped) and "range" not in stripped:
                if not stripped.startswith("#") and "import" not in stripped:
                    issues.append({"type": "systemic", "line": i,
                                   "text": "Magic number", "fix_type": "systemic"})

        # --- Gate 3: AST-level detection (only if parseable) ---
        if tree is not None:
            issues.extend(self._ast_detect(tree))

        self.atomic_issues = issues
        return {
            "primer_id": self.signature,
            "issue_count": len(issues),
            "complexity": len(lines),
            "issues": issues,
        }

    def _ast_detect(self, tree: ast.AST) -> List[Dict]:
        """Deep AST-based issue detection — Gate 3 of Think."""
        issues: List[Dict] = []

        for node in ast.walk(tree):

            # Unused variables in assignments (simple heuristic)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.startswith("_") and target.id != "_":
                        issues.append({"type": "surface", "line": node.lineno,
                                       "text": f"Underscore-prefixed assignment: {target.id}",
                                       "fix_type": "surface"})

            # Nested function depth > 2
            if isinstance(node, ast.FunctionDef):
                depth = self._nesting_depth(node)
                if depth > 2:
                    issues.append({"type": "systemic", "line": node.lineno,
                                   "text": f"Excessive nesting depth ({depth}) in {node.name}",
                                   "fix_type": "systemic"})

                # Function too long (> 50 lines)
                if hasattr(node, "end_lineno") and node.end_lineno:
                    length = node.end_lineno - node.lineno
                    if length > 50:
                        issues.append({"type": "systemic", "line": node.lineno,
                                       "text": f"Function {node.name} is {length} lines long",
                                       "fix_type": "systemic"})

                # Missing docstring
                if not (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    if not node.name.startswith("_"):
                        issues.append({"type": "surface", "line": node.lineno,
                                       "text": f"Missing docstring: {node.name}",
                                       "fix_type": "surface"})

            # Class without docstring
            if isinstance(node, ast.ClassDef):
                if not (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    issues.append({"type": "surface", "line": node.lineno,
                                   "text": f"Missing class docstring: {node.name}",
                                   "fix_type": "surface"})

            # raise without exception type
            if isinstance(node, ast.Raise) and node.exc is None:
                issues.append({"type": "structural", "line": node.lineno,
                               "text": "Bare raise without exception", "fix_type": "structural"})

            # assert used in production code
            if isinstance(node, ast.Assert):
                issues.append({"type": "structural", "line": node.lineno,
                               "text": "Assert statement (disabled with -O flag)",
                               "fix_type": "structural"})

            # Return in __init__
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value is not None:
                        issues.append({"type": "structural", "line": child.lineno,
                                       "text": "Return with value in __init__",
                                       "fix_type": "structural"})

            # String concatenation in loop
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                        if isinstance(child.target, ast.Name):
                            issues.append({"type": "systemic", "line": child.lineno,
                                           "text": "String concatenation in loop (use join)",
                                           "fix_type": "systemic"})

            # Empty exception body (just pass)
            if isinstance(node, ast.ExceptHandler):
                if (len(node.body) == 1 and isinstance(node.body[0], ast.Pass)):
                    issues.append({"type": "structural", "line": node.lineno,
                                   "text": "Silent exception swallowing (except + pass)",
                                   "fix_type": "structural"})

            # Comparison to True/False using is
            if isinstance(node, ast.Compare):
                for op, comparator in zip(node.ops, node.comparators):
                    if isinstance(op, ast.Is) and isinstance(comparator, ast.Constant):
                        if comparator.value is True or comparator.value is False:
                            issues.append({"type": "surface", "line": node.lineno,
                                           "text": "Use 'if x:' instead of 'if x is True:'",
                                           "fix_type": "surface"})

            # Duplicate keys in dict literal
            if isinstance(node, ast.Dict):
                keys = []
                for k in node.keys:
                    if isinstance(k, ast.Constant):
                        if k.value in keys:
                            issues.append({"type": "structural", "line": node.lineno,
                                           "text": f"Duplicate dict key: {k.value}",
                                           "fix_type": "structural"})
                        keys.append(k.value)

            # f-string with no placeholders
            if isinstance(node, ast.JoinedStr) and len(node.values) == 1:
                if isinstance(node.values[0], ast.Constant):
                    issues.append({"type": "surface", "line": node.lineno,
                                   "text": "f-string with no placeholders",
                                   "fix_type": "surface"})

        return issues

    def _nesting_depth(self, node: ast.AST, depth: int = 0) -> int:
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While, ast.If, ast.With, ast.Try)):
                child_depth = self._nesting_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth

    # ==================================================================
    # PHASE 2 — LEARN
    # ==================================================================

    def learn(self, think_data: Dict) -> Dict:
        """LEVEL L: Self-referential pattern extraction from primer."""
        conventions = {
            "indentation": self._detect_indentation(),
            "quote_style": self._detect_quotes(),
            "naming": self._extract_naming_patterns(),
            "imports": self._extract_imports(),
            "avg_line_length": self._avg_line_length(),
            "has_type_hints": self._has_type_hints(),
        }

        return {
            **think_data,
            "conventions": conventions,
            "patterns": self._build_failure_signatures(),
        }

    def _detect_indentation(self) -> str:
        for line in self.original.split("\n"):
            if line.startswith("    "):
                return "    "
            elif line.startswith("\t"):
                return "\t"
        return "    "

    def _detect_quotes(self) -> str:
        single = self.original.count("'")
        double = self.original.count('"')
        return '"' if double > single else "'"

    def _extract_naming_patterns(self) -> List[str]:
        try:
            tree = ast.parse(self.original)
            names = [node.id for node in ast.walk(tree) if isinstance(node, ast.Name)]
            return list(set(names))
        except Exception:
            return []

    def _extract_imports(self) -> List[str]:
        try:
            tree = ast.parse(self.original)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            return imports
        except Exception:
            return []

    def _avg_line_length(self) -> float:
        lines = [l for l in self.original.split("\n") if l.strip()]
        if not lines:
            return 0.0
        return sum(len(l) for l in lines) / len(lines)

    def _has_type_hints(self) -> bool:
        try:
            tree = ast.parse(self.original)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.returns:
                    return True
                if isinstance(node, ast.AnnAssign):
                    return True
            return False
        except Exception:
            return False

    def _build_failure_signatures(self) -> List[str]:
        return [f"{issue['type']}:{issue.get('line', 0)}" for issue in self.atomic_issues]

    # ==================================================================
    # PHASE 3 — REFLECT (Triple Redundancy Cascade)
    # ==================================================================

    def reflect(self, learn_data: Dict) -> Dict:
        """LEVEL R: Triple Redundancy Cascade — three independent fix layers."""
        fix_a = self._redundancy_surface(learn_data)
        fix_b = self._redundancy_structural(learn_data)
        fix_c = self._redundancy_systemic(learn_data)

        self.redundant_fixes = {
            "surface": fix_a,
            "structural": fix_b,
            "systemic": fix_c,
        }

        return {
            **learn_data,
            "fixes": self.redundant_fixes,
            "divergence_score": self._calculate_divergence(fix_a, fix_b, fix_c),
        }

    def _redundancy_surface(self, data: Dict) -> str:
        """R1: Literal text transformation — syntax and style only."""
        lines = self.original.split("\n")
        fixed = []

        for line in lines:
            new_line = line

            # Fix Python 2 prints
            match = re.match(r"^(\s*)print\s+([^(].*)$", line)
            if match and not line.strip().startswith("print("):
                indent = match.group(1)
                content = match.group(2).strip()
                comment = ""
                if "#" in content:
                    parts = content.split("#", 1)
                    content = parts[0].strip()
                    comment = "  # " + parts[1].strip()
                new_line = f"{indent}print({content}){comment}"

            # Fix None comparisons
            new_line = new_line.replace("== None", "is None")
            new_line = new_line.replace("!= None", "is not None")

            # Fix boolean comparisons
            new_line = new_line.replace("== True", "")
            new_line = new_line.replace("== False", "")
            # Only apply if it doesn't break the line structure
            if "== True" in line:
                new_line = line.replace("== True", "")
            if "== False" in line:
                new_line = line.replace("== False", "")

            # Fix trailing whitespace
            new_line = new_line.rstrip()
            fixed.append(new_line)

        return "\n".join(fixed)

    def _redundancy_structural(self, data: Dict) -> str:
        """R2: Pattern and relationship fixes."""
        code = self._redundancy_surface(data)
        lines = code.split("\n")
        fixed = []
        indent = data["conventions"]["indentation"]

        for i, line in enumerate(lines):
            # Fix bare excepts
            match = re.match(r"^(\s*)except\s*:(.*)$", line)
            if match:
                line = match.group(1) + "except Exception:" + match.group(2)

            # Add pass to empty blocks
            if line.strip().endswith(":") and i + 1 < len(lines):
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                if not next_line.strip() or next_line.strip().startswith("#"):
                    fixed.append(line)
                    current_indent = len(line) - len(line.lstrip())
                    fixed.append(" " * (current_indent + len(indent)) + "pass")
                    continue

            fixed.append(line)

        return "\n".join(fixed)

    def _redundancy_systemic(self, data: Dict) -> str:
        """R3: Architectural and logic fixes."""
        code = self._redundancy_structural(data)

        # Fix mutable defaults — handles both "= []" and "=[]" spacing
        if re.search(r"=\s*\[\]", code) or re.search(r"=\s*\{\}", code):
            lines = code.split("\n")
            fixed_lines = []
            for line in lines:
                if re.match(r"^\s*def\s+\w+\(", line):
                    line = re.sub(r"=\s*\[\]", "=None", line)
                    line = re.sub(r"=\s*\{\}", "=None", line)
                fixed_lines.append(line)
            code = "\n".join(fixed_lines)

        return code

    def _calculate_divergence(self, a: str, b: str, c: str) -> float:
        diff_ab = len(list(difflib.ndiff(a.splitlines(), b.splitlines())))
        diff_bc = len(list(difflib.ndiff(b.splitlines(), c.splitlines())))
        return (diff_ab + diff_bc) / 2

    # ==================================================================
    # AGENT DISCOVERY PHASE
    # ==================================================================

    def agent_discovery(self, reflect_data: Dict) -> Dict:
        """AGENT PHASE: Cross-validation and secondary issue detection."""
        fixes = reflect_data["fixes"]
        discoveries = []

        # Validate each fix for syntax
        valid_fixes = {}
        for name, code in fixes.items():
            try:
                ast.parse(code)
                valid_fixes[name] = code
            except SyntaxError as e:
                discoveries.append(f"{name} fix introduces syntax error at line {e.lineno}: {e.msg}")

        # Check for introduced issues
        if "systemic" in valid_fixes:
            code = valid_fixes["systemic"]
            if "try:" in code and "except" in code:
                if "finally:" not in code and "with" not in self.original:
                    discoveries.append("Exception handling without resource cleanup detected")

        # Check that fixes didn't grow the code excessively
        orig_lines = len(self.original.splitlines())
        for name, code in valid_fixes.items():
            fix_lines = len(code.splitlines())
            if fix_lines > orig_lines * 1.5:
                discoveries.append(f"{name} fix increased code size by {fix_lines - orig_lines} lines")

        # Select golden fix
        if reflect_data["divergence_score"] < DIVERGENCE_THRESHOLD and "systemic" in valid_fixes:
            golden = valid_fixes["systemic"]
            level = "systemic"
        elif "structural" in valid_fixes:
            golden = valid_fixes["structural"]
            level = "structural"
        else:
            golden = valid_fixes.get("surface", self.original)
            level = "surface"

        return {
            **reflect_data,
            "golden_fix": golden,
            "selected_level": level,
            "discoveries": discoveries,
            "fix_confidence": len(valid_fixes) / 3 * 100,
            "valid_fix_count": len(valid_fixes),
        }

    # ==================================================================
    # PHASE 4 — WRITE
    # ==================================================================

    def write(self, agent_data: Dict) -> str:
        """LEVEL W: Synthesis and output."""
        output = [
            f"# TLRW FIXED CODE (v{__version__})",
            f"# Primer ID: {agent_data['primer_id']}",
            f"# Fix Level: {agent_data['selected_level']}",
            f"# Confidence: {agent_data['fix_confidence']:.0f}%",
            f"# Issues Found: {agent_data['issue_count']}",
            f"# Secondary Discoveries: {len(agent_data['discoveries'])}",
        ]
        if agent_data["discoveries"]:
            for d in agent_data["discoveries"]:
                output.append(f"# WARNING: {d}")
        output.append("")
        output.append(agent_data["golden_fix"])
        return "\n".join(output)

    # ==================================================================
    # CASCADE — Full Pipeline
    # ==================================================================

    def cascade(self) -> str:
        """Execute full TLRW Redundancy Cascade."""
        logger.info("Initializing TLRW Cascade for Primer %s", self.signature)

        think_result = self.think()
        logger.info("THINK: %d atomic issues detected", think_result["issue_count"])

        learn_result = self.learn(think_result)
        logger.info("LEARN: Extracted %d naming patterns, %d imports",
                     len(learn_result["conventions"]["naming"]),
                     len(learn_result["conventions"]["imports"]))

        reflect_result = self.reflect(learn_result)
        logger.info("REFLECT: Triple redundancy generated (divergence: %.1f)",
                     reflect_result["divergence_score"])

        agent_result = self.agent_discovery(reflect_result)
        logger.info("AGENT: %d secondary discoveries, %d valid fixes",
                     len(agent_result["discoveries"]),
                     agent_result["valid_fix_count"])
        logger.info("VALIDATION: %.0f%% confidence — selected level: %s",
                     agent_result["fix_confidence"],
                     agent_result["selected_level"])

        self.run_count += 1
        return self.write(agent_result)

    # ==================================================================
    # REPORTING
    # ==================================================================

    def generate_report(self, agent_data: Optional[Dict] = None) -> str:
        """Generate a human-readable report of the cascade results."""
        if agent_data is None:
            # Run the cascade first to get data
            think_result = self.think()
            learn_result = self.learn(think_result)
            reflect_result = self.reflect(learn_result)
            agent_data = self.agent_discovery(reflect_result)

        report = []
        report.append("=" * 60)
        report.append("  TLRW REDUNDANCY CASCADE FIXER — ANALYSIS REPORT")
        report.append(f"  Version: {__version__}")
        report.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        report.append("")

        report.append(f"Primer ID:        {agent_data['primer_id']}")
        report.append(f"Code Complexity:   {agent_data['complexity']} lines")
        report.append(f"Issues Detected:   {agent_data['issue_count']}")
        report.append(f"Fix Level:         {agent_data['selected_level']}")
        report.append(f"Confidence:        {agent_data['fix_confidence']:.0f}%")
        report.append(f"Divergence Score:  {agent_data['divergence_score']:.1f}")
        report.append("")

        # Issue breakdown
        report.append("-" * 60)
        report.append("  ISSUE BREAKDOWN")
        report.append("-" * 60)

        by_type = {}
        for issue in agent_data.get("issues", []):
            t = issue["type"]
            by_type.setdefault(t, []).append(issue)

        for issue_type, items in sorted(by_type.items()):
            report.append(f"\n  [{issue_type.upper()}] ({len(items)} issues)")
            for item in items:
                report.append(f"    Line {item.get('line', '?'):>4}: {item['text']}")

        # Discoveries
        if agent_data["discoveries"]:
            report.append("")
            report.append("-" * 60)
            report.append("  SECONDARY DISCOVERIES (Agent Phase)")
            report.append("-" * 60)
            for d in agent_data["discoveries"]:
                report.append(f"    ! {d}")

        # Conventions
        conventions = agent_data.get("conventions", {})
        if conventions:
            report.append("")
            report.append("-" * 60)
            report.append("  LEARNED CONVENTIONS")
            report.append("-" * 60)
            report.append(f"    Indentation:    {'spaces' if conventions.get('indentation') == '    ' else 'tabs'}")
            report.append(f"    Quote Style:    {conventions.get('quote_style', 'unknown')}")
            report.append(f"    Type Hints:     {'yes' if conventions.get('has_type_hints') else 'no'}")
            report.append(f"    Avg Line Length: {conventions.get('avg_line_length', 0):.0f} chars")
            report.append(f"    Named Symbols:  {len(conventions.get('naming', []))}")
            report.append(f"    Import Count:   {len(conventions.get('imports', []))}")

        report.append("")
        report.append("=" * 60)
        report.append("  END REPORT")
        report.append("=" * 60)
        return "\n".join(report)


# ======================================================================
# SELF-HEALING AGENT
# ======================================================================

class SelfHealingAgent:
    """
    Internal self-healing module.

    Reads the fixer's own source code, runs the cascade on it,
    and delegates validation to the MetaSupervisor.
    """

    def __init__(self, fixer_path: Optional[str] = None):
        self.fixer_path = Path(fixer_path or __file__).resolve()
        self.patch_path = self.fixer_path.parent / "tlrw_fixer_patch.py"
        self.supervisor_path = self.fixer_path.parent / "meta_supervisor.py"

    def run(self) -> Dict:
        """Execute the self-healing cycle."""
        logger.info("SELF-HEAL: Starting self-analysis of %s", self.fixer_path)

        # Step 1 — Read own source
        source = self.fixer_path.read_text(encoding="utf-8")
        original_hash = hashlib.sha256(source.encode()).hexdigest()

        # Step 2 — Run cascade on self
        fixer = TLRWFixer(source)
        think_result = fixer.think()
        learn_result = fixer.learn(think_result)
        reflect_result = fixer.reflect(learn_result)
        agent_result = fixer.agent_discovery(reflect_result)

        golden = agent_result["golden_fix"]
        patched_hash = hashlib.sha256(golden.encode()).hexdigest()

        result = {
            "original_hash": original_hash,
            "patched_hash": patched_hash,
            "issues_found": agent_result["issue_count"],
            "fix_level": agent_result["selected_level"],
            "confidence": agent_result["fix_confidence"],
            "divergence": agent_result["divergence_score"],
            "discoveries": agent_result["discoveries"],
            "changed": original_hash != patched_hash,
            "timestamp": datetime.now().isoformat(),
        }

        if not result["changed"]:
            logger.info("SELF-HEAL: No changes needed — fixer is clean")
            return result

        # Step 3 — Write patch file
        # Strip the TLRW header comments from golden fix
        patch_lines = golden.split("\n")
        clean_lines = []
        header_done = False
        for line in patch_lines:
            if not header_done and line.startswith("# TLRW"):
                continue
            if not header_done and line.startswith("# Primer"):
                continue
            if not header_done and line.startswith("# Fix Level"):
                continue
            if not header_done and line.startswith("# Confidence"):
                continue
            if not header_done and line.startswith("# Issues"):
                continue
            if not header_done and line.startswith("# Secondary"):
                continue
            if not header_done and line.startswith("# WARNING"):
                continue
            header_done = True
            clean_lines.append(line)

        clean_patch = "\n".join(clean_lines).lstrip("\n")
        self.patch_path.write_text(clean_patch, encoding="utf-8")
        logger.info("SELF-HEAL: Patch written to %s", self.patch_path)

        # Step 4 — Request validation from MetaSupervisor
        if self.supervisor_path.exists():
            logger.info("SELF-HEAL: Requesting MetaSupervisor validation")
            try:
                proc = subprocess.run(
                    [sys.executable, str(self.supervisor_path), "validate",
                     str(self.patch_path), str(self.fixer_path)],
                    capture_output=True, text=True, timeout=120,
                )
                result["supervisor_exit"] = proc.returncode
                result["supervisor_stdout"] = proc.stdout.strip()
                result["supervisor_stderr"] = proc.stderr.strip()

                if proc.returncode == 0:
                    logger.info("SELF-HEAL: Patch APPROVED by MetaSupervisor")
                    result["approved"] = True
                else:
                    logger.warning("SELF-HEAL: Patch REJECTED by MetaSupervisor")
                    result["approved"] = False
                    # Clean up rejected patch
                    if self.patch_path.exists():
                        self.patch_path.unlink()
            except subprocess.TimeoutExpired:
                logger.error("SELF-HEAL: MetaSupervisor timed out")
                result["approved"] = False
                result["supervisor_error"] = "timeout"
            except Exception as e:
                logger.error("SELF-HEAL: MetaSupervisor error: %s", e)
                result["approved"] = False
                result["supervisor_error"] = str(e)
        else:
            logger.warning("SELF-HEAL: MetaSupervisor not found at %s — patch saved but not validated",
                           self.supervisor_path)
            result["approved"] = None

        # Log the result
        log_file = LOG_DIR / "self_heal.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, indent=2) + "\n---\n")

        return result


# ======================================================================
# CLI
# ======================================================================

def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tlrw_fixer",
        description="TLRW Redundancy Cascade Fixer v" + __version__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python tlrw_fixer.py fix target.py
              python tlrw_fixer.py fix target.py -o fixed.py
              python tlrw_fixer.py fix --string "print 'hello'"
              python tlrw_fixer.py report target.py
              python tlrw_fixer.py self-heal
              python tlrw_fixer.py version
        """),
    )
    sub = parser.add_subparsers(dest="command")

    # --- fix ---
    fix_p = sub.add_parser("fix", help="Run the full cascade on a target file")
    fix_p.add_argument("target", nargs="?", help="Path to target .py file")
    fix_p.add_argument("--string", "-s", help="Fix an inline code string")
    fix_p.add_argument("--output", "-o", help="Output file path (default: <target>_TLRW_FIXED.py)")
    fix_p.add_argument("--quiet", "-q", action="store_true", help="Suppress console output")

    # --- report ---
    rep_p = sub.add_parser("report", help="Generate analysis report without fixing")
    rep_p.add_argument("target", help="Path to target .py file")
    rep_p.add_argument("--output", "-o", help="Save report to file")

    # --- self-heal ---
    sub.add_parser("self-heal", help="Run self-healing cycle on the fixer itself")

    # --- version ---
    sub.add_parser("version", help="Show version info")

    return parser


def main():
    parser = build_cli()
    args = parser.parse_args()

    if args.command is None:
        # Legacy compatibility: python tlrw_fixer.py <file>
        if len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
            target = sys.argv[1]
            if target == "--string" and len(sys.argv) >= 3:
                source = sys.argv[2]
                output_name = "fixed_code.py"
            else:
                with open(target, "r", encoding="utf-8") as f:
                    source = f.read()
                output_name = target.replace(".py", "_TLRW_FIXED.py")

            fixer = TLRWFixer(source)
            result = fixer.cascade()
            with open(output_name, "w", encoding="utf-8") as f:
                f.write(result)
            logger.info("Cascade complete. Output: %s", output_name)
            return
        parser.print_help()
        sys.exit(1)

    if args.command == "version":
        print(f"TLRW Redundancy Cascade Fixer v{__version__}")
        print(f"Python {sys.version}")
        return

    if args.command == "self-heal":
        agent = SelfHealingAgent()
        result = agent.run()
        print(json.dumps(result, indent=2))
        return

    if args.command == "report":
        with open(args.target, "r", encoding="utf-8") as f:
            source = f.read()
        fixer = TLRWFixer(source)
        think_result = fixer.think()
        learn_result = fixer.learn(think_result)
        reflect_result = fixer.reflect(learn_result)
        agent_result = fixer.agent_discovery(reflect_result)
        report = fixer.generate_report(agent_result)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info("Report saved to %s", args.output)
        else:
            print(report)
        return

    if args.command == "fix":
        if args.quiet:
            logging.getLogger("tlrw").setLevel(logging.WARNING)

        if args.string:
            source = args.string
            output_name = args.output or "fixed_code.py"
        elif args.target:
            with open(args.target, "r", encoding="utf-8") as f:
                source = f.read()
            output_name = args.output or args.target.replace(".py", "_TLRW_FIXED.py")
        else:
            parser.error("Provide a target file or --string")
            return

        fixer = TLRWFixer(source)
        result = fixer.cascade()

        with open(output_name, "w", encoding="utf-8") as f:
            f.write(result)

        logger.info("Cascade complete. Output: %s", output_name)
        logger.info("Issues: %d | Fix level: %s",
                     len(fixer.atomic_issues),
                     list(fixer.redundant_fixes.keys()))
        return


if __name__ == "__main__":
    main()
