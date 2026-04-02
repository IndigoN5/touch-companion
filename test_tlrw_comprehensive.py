#!/usr/bin/env python3
"""
TLRW COMPREHENSIVE TEST SUITE
Exhaustive validation of the TLRW Redundancy Cascade Fixer.

Coverage:
    - All detected issue types (surface, structural, systemic)
    - Edge cases (empty files, clean files, complex nesting)
    - Cascade pipeline integrity
    - Triple redundancy divergence logic
    - Agent discovery and golden fix selection
    - Self-healing agent mechanics
    - Report generation
    - Output validity (fixed code must parse)
"""

import ast
import sys
import os
import unittest
import tempfile
import shutil
from pathlib import Path

# Ensure the fixer is importable
sys.path.insert(0, str(Path(__file__).parent))
from tlrw_fixer import TLRWFixer, SelfHealingAgent, __version__


# ======================================================================
# HELPER
# ======================================================================

def assert_parses(test_case: unittest.TestCase, code: str, msg: str = ""):
    """Assert that a code string is valid Python."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        test_case.fail(f"Code does not parse: {e} — {msg}\n---\n{code[:500]}")


def extract_golden(cascade_output: str) -> str:
    """Strip TLRW header from cascade output to get the golden fix."""
    lines = cascade_output.split("\n")
    body_lines = []
    past_header = False
    for line in lines:
        if past_header:
            body_lines.append(line)
        elif not line.startswith("#") and line.strip() == "":
            past_header = True
        elif not line.startswith("#"):
            past_header = True
            body_lines.append(line)
    return "\n".join(body_lines)


# ======================================================================
# TEST: Surface-Level Fixes
# ======================================================================

class TestSurfaceFixes(unittest.TestCase):
    """Test all surface-level (syntax/style) issue detection and repair."""

    def test_python2_print_simple(self):
        code = "print 'hello world'"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("print(", golden)
        self.assertNotIn("print '", golden)
        assert_parses(self, golden, "Python 2 print fix")

    def test_python2_print_multiple(self):
        code = "print 'a'\nprint 'b'\nprint 'c'"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertEqual(golden.count("print("), 3)

    def test_python2_print_with_variable(self):
        code = "x = 42\nprint x"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("print(x)", golden)

    def test_none_comparison_equals(self):
        code = "x = None\nif x == None:\n    pass"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("is None", golden)
        self.assertNotIn("== None", golden)

    def test_none_comparison_not_equals(self):
        code = "x = None\nif x != None:\n    pass"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("is not None", golden)
        self.assertNotIn("!= None", golden)

    def test_trailing_whitespace(self):
        code = "x = 1   \ny = 2\n"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        for line in golden.split("\n"):
            self.assertEqual(line, line.rstrip(), f"Trailing whitespace in: '{line}'")

    def test_does_not_break_valid_print(self):
        code = "print('already correct')\n"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("print('already correct')", golden)
        assert_parses(self, golden)


# ======================================================================
# TEST: Structural Fixes
# ======================================================================

class TestStructuralFixes(unittest.TestCase):
    """Test structural-level issue detection and repair."""

    def test_bare_except(self):
        code = "try:\n    x = 1\nexcept:\n    pass"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("except Exception:", golden)
        self.assertNotRegex(golden, r"except\s*:")
        assert_parses(self, golden)

    def test_bare_except_preserves_body(self):
        code = "try:\n    x = 1\nexcept:\n    print('error')"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("except Exception:", golden)
        self.assertIn("print", golden)

    def test_multiple_bare_excepts(self):
        code = ("try:\n    a()\nexcept:\n    pass\n\n"
                "try:\n    b()\nexcept:\n    pass")
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertEqual(golden.count("except Exception:"), 2)


# ======================================================================
# TEST: Systemic Fixes
# ======================================================================

class TestSystemicFixes(unittest.TestCase):
    """Test systemic-level (architectural) issue detection and repair."""

    def test_mutable_default_list(self):
        code = "def foo(items=[]):\n    return items"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("None", golden)
        self.assertNotIn("[]", golden)
        assert_parses(self, golden)

    def test_mutable_default_dict(self):
        code = "def foo(config={}):\n    return config"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("None", golden)
        self.assertNotIn("{}", golden)
        assert_parses(self, golden)

    def test_mutable_default_both(self):
        code = ("def foo(items=[], config={}):\n"
                "    return items, config")
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertNotIn("[]", golden)
        self.assertNotIn("{}", golden)
        assert_parses(self, golden)

    def test_does_not_replace_non_default_empty_list(self):
        code = "x = []\nfor i in range(10):\n    x.append(i)"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        # The = [] on a regular assignment should NOT be changed
        self.assertIn("x = []", golden)


# ======================================================================
# TEST: Combined Multi-Issue Files
# ======================================================================

class TestMultiIssue(unittest.TestCase):
    """Test files with multiple issue types simultaneously."""

    def test_all_surface_and_structural(self):
        code = ("import os\n"
                "def process(data):\n"
                "    if data == None:\n"
                "        print 'no data'\n"
                "    try:\n"
                "        result = data.strip()\n"
                "    except:\n"
                "        print 'error'\n"
                "    return result\n")
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)

        self.assertIn("is None", golden)
        self.assertIn("print(", golden)
        self.assertIn("except Exception:", golden)
        assert_parses(self, golden)

    def test_kitchen_sink(self):
        code = ("import sys\n\n"
                "def run(items=[], config={}):\n"
                "    if items == None:\n"
                "        print 'empty'\n"
                "        return\n"
                "    for item in items:\n"
                "        try:\n"
                "            process(item)\n"
                "        except:\n"
                "            print 'fail'\n"
                "    return items\n")
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)

        self.assertIn("is None", golden)
        self.assertIn("print(", golden)
        self.assertIn("except Exception:", golden)
        self.assertNotIn("[]", golden)
        self.assertNotIn("{}", golden)
        assert_parses(self, golden)


# ======================================================================
# TEST: Edge Cases
# ======================================================================

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_file(self):
        code = ""
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        # Should not crash, should produce valid output
        self.assertIn("TLRW FIXED CODE", result)

    def test_clean_file_no_issues(self):
        code = ("def hello():\n"
                "    \"\"\"Say hello.\"\"\"\n"
                "    print('hello')\n")
        fixer = TLRWFixer(code)
        think_result = fixer.think()
        # May detect some issues (like missing type hints) but should not crash
        result = fixer.cascade()
        golden = extract_golden(result)
        assert_parses(self, golden)

    def test_single_line(self):
        code = "x = 1"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("x = 1", golden)

    def test_comments_preserved(self):
        code = "# This is a comment\nx = 1  # inline comment\n"
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        self.assertIn("# This is a comment", golden)
        self.assertIn("# inline comment", golden)

    def test_multiline_string_not_broken(self):
        code = 'x = """this is\na multiline\nstring"""\n'
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        assert_parses(self, golden)

    def test_large_file(self):
        # Generate a 200-line file
        lines = ["import os", ""]
        for i in range(100):
            lines.append(f"def func_{i}():")
            lines.append(f"    return {i}")
        code = "\n".join(lines)
        fixer = TLRWFixer(code)
        result = fixer.cascade()
        golden = extract_golden(result)
        assert_parses(self, golden)


# ======================================================================
# TEST: Cascade Pipeline
# ======================================================================

class TestCascadePipeline(unittest.TestCase):
    """Test the full cascade pipeline mechanics."""

    def test_cascade_returns_string(self):
        fixer = TLRWFixer("x = 1")
        result = fixer.cascade()
        self.assertIsInstance(result, str)

    def test_cascade_header_format(self):
        fixer = TLRWFixer("x = 1")
        result = fixer.cascade()
        self.assertIn("# TLRW FIXED CODE", result)
        self.assertIn("# Primer ID:", result)
        self.assertIn("# Fix Level:", result)
        self.assertIn("# Confidence:", result)
        self.assertIn("# Issues Found:", result)

    def test_think_returns_issues(self):
        code = "print 'hello'\n"
        fixer = TLRWFixer(code)
        result = fixer.think()
        self.assertIn("issue_count", result)
        self.assertIn("primer_id", result)
        self.assertGreater(result["issue_count"], 0)

    def test_learn_returns_conventions(self):
        code = "    x = 1\n"
        fixer = TLRWFixer(code)
        think_data = fixer.think()
        learn_data = fixer.learn(think_data)
        self.assertIn("conventions", learn_data)
        self.assertIn("indentation", learn_data["conventions"])

    def test_reflect_returns_three_fixes(self):
        code = "print 'hello'"
        fixer = TLRWFixer(code)
        think_data = fixer.think()
        learn_data = fixer.learn(think_data)
        reflect_data = fixer.reflect(learn_data)
        self.assertIn("fixes", reflect_data)
        self.assertIn("surface", reflect_data["fixes"])
        self.assertIn("structural", reflect_data["fixes"])
        self.assertIn("systemic", reflect_data["fixes"])

    def test_divergence_score_computed(self):
        code = "print 'hello'"
        fixer = TLRWFixer(code)
        think_data = fixer.think()
        learn_data = fixer.learn(think_data)
        reflect_data = fixer.reflect(learn_data)
        self.assertIn("divergence_score", reflect_data)
        self.assertIsInstance(reflect_data["divergence_score"], float)

    def test_agent_selects_golden_fix(self):
        code = "print 'hello'"
        fixer = TLRWFixer(code)
        think_data = fixer.think()
        learn_data = fixer.learn(think_data)
        reflect_data = fixer.reflect(learn_data)
        agent_data = fixer.agent_discovery(reflect_data)
        self.assertIn("golden_fix", agent_data)
        self.assertIn("selected_level", agent_data)
        self.assertIn(agent_data["selected_level"], ["surface", "structural", "systemic"])

    def test_confidence_is_percentage(self):
        code = "x = 1"
        fixer = TLRWFixer(code)
        think_data = fixer.think()
        learn_data = fixer.learn(think_data)
        reflect_data = fixer.reflect(learn_data)
        agent_data = fixer.agent_discovery(reflect_data)
        self.assertGreaterEqual(agent_data["fix_confidence"], 0)
        self.assertLessEqual(agent_data["fix_confidence"], 100)


# ======================================================================
# TEST: Signature Uniqueness
# ======================================================================

class TestSignature(unittest.TestCase):
    """Test primer signature generation."""

    def test_signature_is_deterministic(self):
        code = "x = 1"
        f1 = TLRWFixer(code)
        f2 = TLRWFixer(code)
        self.assertEqual(f1.signature, f2.signature)

    def test_different_code_different_signature(self):
        f1 = TLRWFixer("x = 1")
        f2 = TLRWFixer("x = 2")
        self.assertNotEqual(f1.signature, f2.signature)

    def test_signature_length(self):
        fixer = TLRWFixer("x = 1")
        self.assertEqual(len(fixer.signature), 12)


# ======================================================================
# TEST: Report Generation
# ======================================================================

class TestReport(unittest.TestCase):
    """Test the report generation feature."""

    def test_report_generated(self):
        code = "print 'hello'\n"
        fixer = TLRWFixer(code)
        report = fixer.generate_report()
        self.assertIn("ANALYSIS REPORT", report)
        self.assertIn("Primer ID:", report)
        self.assertIn("Issues Detected:", report)

    def test_report_contains_issue_breakdown(self):
        code = ("def foo(x=[]):\n"
                "    try:\n"
                "        pass\n"
                "    except:\n"
                "        pass\n")
        fixer = TLRWFixer(code)
        report = fixer.generate_report()
        self.assertIn("ISSUE BREAKDOWN", report)

    def test_report_contains_conventions(self):
        code = "    x = 1\n"
        fixer = TLRWFixer(code)
        report = fixer.generate_report()
        self.assertIn("LEARNED CONVENTIONS", report)


# ======================================================================
# TEST: AST Detection Patterns
# ======================================================================

class TestASTDetection(unittest.TestCase):
    """Test AST-based deep detection patterns."""

    def test_detect_silent_exception(self):
        code = ("try:\n"
                "    x = 1\n"
                "except Exception:\n"
                "    pass\n")
        fixer = TLRWFixer(code)
        think_data = fixer.think()
        texts = [i["text"] for i in think_data["issues"]]
        self.assertTrue(any("Silent exception" in t for t in texts))

    def test_detect_duplicate_dict_keys(self):
        code = 'x = {"a": 1, "b": 2, "a": 3}\n'
        fixer = TLRWFixer(code)
        think_data = fixer.think()
        texts = [i["text"] for i in think_data["issues"]]
        self.assertTrue(any("Duplicate dict key" in t for t in texts))

    def test_detect_assert_statement(self):
        code = "def foo():\n    assert True\n"
        fixer = TLRWFixer(code)
        think_data = fixer.think()
        texts = [i["text"] for i in think_data["issues"]]
        self.assertTrue(any("Assert" in t for t in texts))

    def test_detect_wildcard_import(self):
        code = "from os import *\n"
        fixer = TLRWFixer(code)
        think_data = fixer.think()
        texts = [i["text"] for i in think_data["issues"]]
        self.assertTrue(any("Wildcard" in t for t in texts))


# ======================================================================
# TEST: Self-Healing Agent
# ======================================================================

class TestSelfHealingAgent(unittest.TestCase):
    """Test the self-healing agent mechanics."""

    def test_agent_initializes(self):
        agent = SelfHealingAgent()
        self.assertTrue(agent.fixer_path.exists())

    def test_agent_reads_own_source(self):
        agent = SelfHealingAgent()
        source = agent.fixer_path.read_text(encoding="utf-8")
        self.assertIn("class TLRWFixer", source)
        self.assertIn("class SelfHealingAgent", source)

    def test_agent_can_analyze_self(self):
        agent = SelfHealingAgent()
        source = agent.fixer_path.read_text(encoding="utf-8")
        fixer = TLRWFixer(source)
        think_data = fixer.think()
        # The fixer should be parseable and analyzable
        self.assertIn("issue_count", think_data)
        self.assertIn("primer_id", think_data)


# ======================================================================
# TEST: Output Validity
# ======================================================================

class TestOutputValidity(unittest.TestCase):
    """Ensure all fixed output is valid Python."""

    SAMPLES = [
        "print 'hello'",
        "x == None",
        "try:\n    pass\nexcept:\n    pass",
        "def foo(x=[]):\n    return x",
        "import os\nfrom sys import *\n",
        "x = 1; y = 2",
        "def bar(d={}):\n    if d != None:\n        print 'yes'",
    ]

    def test_all_samples_produce_valid_python(self):
        for i, code in enumerate(self.SAMPLES):
            fixer = TLRWFixer(code)
            result = fixer.cascade()
            golden = extract_golden(result)
            assert_parses(self, golden, f"Sample {i}: {code[:40]}")


# ======================================================================
# TEST: Version
# ======================================================================

class TestVersion(unittest.TestCase):
    """Test version metadata."""

    def test_version_exists(self):
        self.assertIsNotNone(__version__)

    def test_version_format(self):
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)
        for p in parts:
            self.assertTrue(p.isdigit())


# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":
    unittest.main()
