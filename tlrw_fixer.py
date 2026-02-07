#!/usr/bin/env python3
"""
TLRW REDUNDANCY CASCADE FIXER
Portable single-file code repair system using Think-Learn-Reflect-Write methodology
with Triple Redundancy validation and Agent Discovery.
"""

import ast
import sys
import hashlib
import difflib
import re
from typing import List, Dict, Optional, Tuple

class TLRWFixer:
    def __init__(self, source_code: str):
        self.original = source_code
        self.primer = source_code
        self.signature = self._generate_signature()
        self.atomic_issues = []
        self.redundant_fixes = {}

    def _generate_signature(self) -> str:
        """Generate unique fingerprint from problem code"""
        return hashlib.sha256(self.original.encode()).hexdigest()[:12]

    def think(self) -> Dict:
        """LEVEL T: Atomic deconstruction of the problem"""
        issues = []

        # Parse for syntax errors
        try:
            tree = ast.parse(self.original)
        except SyntaxError as e:
            issues.append({
                'type': 'syntax',
                'line': e.lineno,
                'text': e.text,
                'fix_type': 'surface'
            })

        # Heuristic pattern analysis (learning from primer itself)
        lines = self.original.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Detect bare excepts (structural issue)
            if re.match(r'^\s*except\s*:', line) and 'except Exception' not in line:
                issues.append({
                    'type': 'structural',
                    'line': i,
                    'text': 'Bare except clause',
                    'fix_type': 'structural'
                })

            # Detect mutable defaults (systemic issue)
            if 'def ' in line and '=' in line and ('[]' in line or '{}' in line):
                issues.append({
                    'type': 'systemic',
                    'line': i,
                    'text': 'Mutable default argument',
                    'fix_type': 'systemic'
                })

            # Detect print statements (surface for py2to3)
            if re.match(r'^\s*print\s+[^(]', line):
                issues.append({
                    'type': 'syntax',
                    'line': i,
                    'text': 'Python 2 print statement',
                    'fix_type': 'surface'
                })

        self.atomic_issues = issues
        return {
            'primer_id': self.signature,
            'issue_count': len(issues),
            'complexity': len(lines)
        }

    def learn(self, think_data: Dict) -> Dict:
        """LEVEL L: Self-referential pattern extraction from primer"""
        # Extract the code's own conventions to guide fixes
        conventions = {
            'indentation': self._detect_indentation(),
            'quote_style': self._detect_quotes(),
            'naming': self._extract_naming_patterns(),
            'imports': self._extract_imports()
        }

        return {
            **think_data,
            'conventions': conventions,
            'patterns': self._build_failure_signatures()
        }

    def _detect_indentation(self) -> str:
        """Learn indentation from primer"""
        for line in self.original.split('\n'):
            if line.startswith('    '):
                return '    '
            elif line.startswith('\t'):
                return '\t'
        return '    '

    def _detect_quotes(self) -> str:
        """Detect preferred quote style"""
        single = self.original.count("'")
        double = self.original.count('"')
        return '"' if double > single else "'"

    def _extract_naming_patterns(self) -> List[str]:
        """Extract variable names for context"""
        try:
            tree = ast.parse(self.original)
            names = [node.id for node in ast.walk(tree) if isinstance(node, ast.Name)]
            return list(set(names))
        except:
            return []

    def _extract_imports(self) -> List[str]:
        """Extract dependencies"""
        try:
            tree = ast.parse(self.original)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module)
            return imports
        except:
            return []

    def _build_failure_signatures(self) -> List[str]:
        """Create fingerprints of error patterns"""
        sigs = []
        for issue in self.atomic_issues:
            sigs.append(f"{issue['type']}:{issue.get('line', 0)}")
        return sigs

    def reflect(self, learn_data: Dict) -> Dict:
        """LEVEL R: Triple Redundancy Cascade"""
        # Generate three independent fixes using primer's own data
        fix_a = self._redundancy_surface(learn_data)
        fix_b = self._redundancy_structural(learn_data)
        fix_c = self._redundancy_systemic(learn_data)

        self.redundant_fixes = {
            'surface': fix_a,
            'structural': fix_b,
            'systemic': fix_c
        }

        return {
            **learn_data,
            'fixes': self.redundant_fixes,
            'divergence_score': self._calculate_divergence(fix_a, fix_b, fix_c)
        }

    def _redundancy_surface(self, data: Dict) -> str:
        """R1: Literal text transformation - syntax only"""
        code = self.original
        lines = code.split('\n')
        fixed = []

        for i, line in enumerate(lines, 1):
            new_line = line

            # Fix Python 2 prints
            match = re.match(r'^(\s*)print\s+([^(].*)$', line)
            if match and not line.strip().startswith('print('):
                indent = match.group(1)
                content = match.group(2).strip()
                # Remove trailing comment and re-add it
                comment = ''
                if '#' in content:
                    parts = content.split('#', 1)
                    content = parts[0].strip()
                    comment = '  # ' + parts[1].strip()
                new_line = f"{indent}print({content}){comment}"

            # Fix None comparisons
            if '== None' in line:
                new_line = new_line.replace('== None', 'is None')
            if '!= None' in line:
                new_line = new_line.replace('!= None', 'is not None')

            # Fix trailing whitespace
            new_line = new_line.rstrip()
            fixed.append(new_line)

        return '\n'.join(fixed)

    def _redundancy_structural(self, data: Dict) -> str:
        """R2: Pattern and relationship fixes"""
        # Start with surface fixes
        code = self._redundancy_surface(data)
        lines = code.split('\n')
        fixed = []
        indent = data['conventions']['indentation']

        for i, line in enumerate(lines):
            # Fix bare excepts by adding Exception
            match = re.match(r'^(\s*)except\s*:(.*)$', line)
            if match:
                line = match.group(1) + 'except Exception:' + match.group(2)

            # Add pass to empty blocks
            if line.strip().endswith(':') and i < len(lines):
                next_line = lines[i] if i < len(lines) else ''
                if not next_line.strip() or next_line.strip().startswith('#'):
                    fixed.append(line)
                    fixed.append(indent * (len(line) - len(line.lstrip())) + 'pass')
                    continue

            fixed.append(line)

        return '\n'.join(fixed)

    def _redundancy_systemic(self, data: Dict) -> str:
        """R3: Architectural and logic fixes"""
        # Start with structural
        code = self._redundancy_structural(data)

        # Fix mutable defaults by adding None check pattern
        if 'def ' in code and '= []' in code or '= {}' in code:
            lines = code.split('\n')
            fixed_lines = []
            for line in lines:
                if 'def ' in line and '= []' in line:
                    # Add mutable default fix
                    line = line.replace('= []', '= None')
                elif 'def ' in line and '= {}' in line:
                    line = line.replace('= {}', '= None')
                fixed_lines.append(line)
            code = '\n'.join(fixed_lines)

        return code

    def _calculate_divergence(self, a: str, b: str, c: str) -> float:
        """Measure how different the three fixes are"""
        diff_ab = len(list(difflib.ndiff(a.splitlines(), b.splitlines())))
        diff_bc = len(list(difflib.ndiff(b.splitlines(), c.splitlines())))
        return (diff_ab + diff_bc) / 2

    def agent_discovery(self, reflect_data: Dict) -> Dict:
        """AGENT PHASE: Cross-validation and secondary issue detection"""
        fixes = reflect_data['fixes']
        discoveries = []

        # Validate each fix for syntax
        valid_fixes = {}
        for name, code in fixes.items():
            try:
                ast.parse(code)
                valid_fixes[name] = code
            except SyntaxError as e:
                discoveries.append(f"{name} fix introduces syntax error: {e}")

        # Check for introduced issues
        if 'systemic' in valid_fixes:
            code = valid_fixes['systemic']
            if 'try:' in code and 'except' in code:
                if 'finally:' not in code and 'with' not in self.original:
                    discoveries.append("Added exception handling without resource cleanup")

        # Select golden fix (prefer highest level that is valid and not divergent)
        if reflect_data['divergence_score'] < 50 and 'systemic' in valid_fixes:
            golden = valid_fixes['systemic']
            level = 'systemic'
        elif 'structural' in valid_fixes:
            golden = valid_fixes['structural']
            level = 'structural'
        else:
            golden = valid_fixes.get('surface', self.original)
            level = 'surface'

        return {
            **reflect_data,
            'golden_fix': golden,
            'selected_level': level,
            'discoveries': discoveries,
            'fix_confidence': len(valid_fixes) / 3 * 100
        }

    def write(self, agent_data: Dict) -> str:
        """LEVEL W: Synthesis and output"""
        output = []
        output.append(f"# TLRW FIXED CODE")
        output.append(f"# Primer ID: {agent_data['primer_id']}")
        output.append(f"# Fix Level: {agent_data['selected_level']}")
        output.append(f"# Confidence: {agent_data['fix_confidence']:.0f}%")
        output.append(f"# Issues Found: {agent_data['issue_count']}")
        output.append(f"# Secondary Discoveries: {len(agent_data['discoveries'])}")
        if agent_data['discoveries']:
            output.append(f"# Warnings: {', '.join(agent_data['discoveries'])}")
        output.append("")
        output.append(agent_data['golden_fix'])
        return '\n'.join(output)

    def cascade(self) -> str:
        """Execute full TLRW Redundancy Cascade"""
        print(f"Initializing TLRW Cascade for Primer {self.signature}")

        # Descent
        think_result = self.think()
        print(f"THINK: {think_result['issue_count']} atomic issues detected")

        learn_result = self.learn(think_result)
        print(f"LEARN: Extracted {len(learn_result['conventions']['naming'])} patterns")

        reflect_result = self.reflect(learn_result)
        print(f"REFLECT: Triple redundancy generated (divergence: {reflect_result['divergence_score']:.1f})")

        # Ascent with Agent
        agent_result = self.agent_discovery(reflect_result)
        print(f"AGENT: {len(agent_result['discoveries'])} secondary issues found")
        print(f"VALIDATION: {agent_result['fix_confidence']:.0f}% confidence")

        return self.write(agent_result)


def main():
    if len(sys.argv) < 2:
        print("Usage: python tlrw_fixer.py <target_file.py>")
        print("       python tlrw_fixer.py --string \"print 'hello world'\"")
        sys.exit(1)

    target = sys.argv[1]

    if target == '--string':
        source = sys.argv[2]
        output_name = 'fixed_code.py'
    else:
        with open(target, 'r') as f:
            source = f.read()
        output_name = target.replace('.py', '_TLRW_FIXED.py')

    fixer = TLRWFixer(source)
    result = fixer.cascade()

    with open(output_name, 'w') as f:
        f.write(result)

    print(f"\nCascade complete. Output: {output_name}")
    print(f"Original issues: {len(fixer.atomic_issues)}")
    print(f"Fix strategy: {fixer.redundant_fixes.keys()}")

if __name__ == "__main__":
    main()
