#!/usr/bin/env python3
"""
Automated SOP Validation Engine (Layer 2.5)
============================================
Validates agent outputs against SOP contracts using AgentContract library.

Usage:
    python sop_validator.py <contract_path> <output_text> [--verbose]
    python sop_validator.py --check-delivery <task_type> <output_text>
"""

import json
import re
import sys
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── AgentContract imports (from ac-env venv) ──────────────────────────────────
AC_ENV = Path("/tmp/ac-env")
AC_VENV_PYTHON = AC_ENV / "bin" / "python"

try:
    sys.path.insert(0, str(AC_ENV / "lib" / "python3.11" / "site-packages"))
    from agentcontract import Contract, ContractViolation
    from agentcontract.validators import (
        PatternValidator, SchemaValidator, LatencyValidator,
        CostValidator, LLMValidator, ValidationResult
    )
    AGENTCONTRACT_AVAILABLE = True
except ImportError:
    AGENTCONTRACT_AVAILABLE = False
    print("[WARN] agentcontract not installed. Using fallback pattern validator.", file=sys.stderr)


# ── Contract paths ────────────────────────────────────────────────────────────
HERMES_CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"
DEFAULT_CONTRACT = HERMES_CONTRACTS_DIR / "hermes-default.contract.yaml"


# ── Built-in validators (when agentcontract unavailable) ──────────────────────
class FallbackValidator:
    """Minimal fallback when agentcontract is not installed."""

    PII_PATTERNS = [
        (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 'Credit Card'),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'Email'),
    ]

    def __init__(self, contract: dict):
        self.contract = contract

    def validate(self, output: str) -> dict:
        violations = []
        checks_passed = []

        # Check must_not clauses (PII patterns)
        for clause in self.contract.get("must_not", []):
            result = self._check_pattern(clause, output)
            if result["violated"]:
                violations.append(result["violation"])
            else:
                checks_passed.append(result["check_name"])

        # Check must clauses (required elements)
        for clause in self.contract.get("must", []):
            result = self._check_required(clause, output)
            if result["missing"]:
                violations.append(result["violation"])
            else:
                checks_passed.append(result["check_name"])

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "checks_passed": checks_passed,
            "validator": "fallback"
        }

    def _check_pattern(self, clause: dict, output: str) -> dict:
        name = clause.get("name", "unnamed")
        pattern = clause.get("pattern", "")
        if not pattern:
            return {"violated": False, "check_name": name}

        if re.search(pattern, output, re.IGNORECASE):
            return {
                "violated": True,
                "check_name": name,
                "violation": {
                    "type": "pattern",
                    "clause": name,
                    "detail": f"Pattern matched: {pattern}",
                    "action": clause.get("on_violation", "block")
                }
            }
        return {"violated": False, "check_name": name}

    def _check_required(self, clause: dict, output: str) -> dict:
        name = clause.get("name", "unnamed")
        required = clause.get("required_element", "")
        if not required:
            return {"missing": False, "check_name": name}

        if required.lower() in output.lower():
            return {"missing": False, "check_name": name}
        return {
            "missing": True,
            "check_name": name,
            "violation": {
                "type": "required_element",
                "clause": name,
                "detail": f"Missing required element: {required}",
                "action": clause.get("on_violation", "warn")
            }
        }


# ── Core validator ────────────────────────────────────────────────────────────
class SOPValidator:
    """
    Layer 2.5 SOP validation engine.
    
    Validates agent outputs against .contract.yaml files using AgentContract
    when available, with fallback to built-in pattern matching.
    """

    def __init__(self, contract_path: Optional[str] = None):
        self.contract_path = Path(contract_path) if contract_path else DEFAULT_CONTRACT
        self.contract = self._load_contract()
        self.validator = self._init_validator()

    def _load_contract(self) -> dict:
        """Load contract YAML file."""
        import yaml
        if not self.contract_path.exists():
            print(f"[WARN] Contract not found: {self.contract_path}", file=sys.stderr)
            return {"must_not": [], "must": []}
        with open(self.contract_path) as f:
            return yaml.safe_load(f)

    def _init_validator(self):
        """Initialize AgentContract validator or fallback."""
        if AGENTCONTRACT_AVAILABLE:
            try:
                return Contract.from_yaml(self.contract_path)
            except Exception as e:
                print(f"[WARN] Failed to load AgentContract: {e}", file=sys.stderr)
        return FallbackValidator(self.contract)

    def validate(self, output: str, task_type: str = "generic") -> dict:
        """
        Validate output against contract.
        
        Returns:
            dict with keys: passed, violations, checks_passed, validator, run_id
        """
        run_id = hashlib.sha256(
            f"{uuid.uuid4()}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:12]

        if AGENTCONTRACT_AVAILABLE and isinstance(self.validator, Contract):
            # Use AgentContract
            result = self.validator.validate(output)
            return {
                "passed": result.passed,
                "violations": [
                    {"type": v.rule, "detail": str(v), "action": v.action}
                    for v in result.violations
                ],
                "checks_passed": [c for c in result.checks_passed],
                "validator": "agentcontract",
                "run_id": run_id
            }
        else:
            # Use fallback
            result = self.validator.validate(output)
            result["run_id"] = run_id
            return result

    def validate_delivery(self, output: str, task_type: str) -> dict:
        """
        Validate sub-agent delivery output.
        
        Loads task-specific contract if available, falls back to default.
        """
        task_contract = HERMES_CONTRACTS_DIR / f"{task_type}.contract.yaml"
        if task_contract.exists():
            original_path = self.contract_path
            self.contract_path = task_contract
            self.contract = self._load_contract()
            self.validator = self._init_validator()
            result = self.validate(output, task_type)
            self.contract_path = original_path
        else:
            result = self.validate(output, task_type)

        # Always check common Hermes rules
        result["hermes_specific"] = self._check_hermes_rules(output)

        return result

    def _check_hermes_rules(self, output: str) -> dict:
        """Check Hermes-specific rules that should always apply."""
        violations = []

        # Rule 1: Don't reveal system prompt
        if "SOUL.md" in output or "system prompt" in output.lower():
            violations.append({
                "type": "security",
                "clause": "no_system_prompt_reveal",
                "detail": "Output should not reveal internal system prompts",
                "action": "warn"
            })

        # Rule 2: Must include [TO_MEMORY] blocks in final output
        # (this is informational - sub-agent may have valid reasons)
        if "[TO_MEMORY]" not in output:
            violations.append({
                "type": "completeness",
                "clause": "memory_sync_marker",
                "detail": "No [TO_MEMORY] block found - ensure memory sync if needed",
                "action": "warn"
            })

        return {
            "passed": len(violations) == 0,
            "violations": violations
        }


# ── CLI entry point ──────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SOP Validation CLI")
    parser.add_argument("contract", nargs="?", help="Path to .contract.yaml")
    parser.add_argument("output", nargs="?", help="Output text or @filename")
    parser.add_argument("--check-delivery", metavar="TASK_TYPE",
                        help="Validate sub-agent delivery for TASK_TYPE")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    # Load output
    if args.output and args.output.startswith("@"):
        with open(args.output[1:]) as f:
            output = f.read()
    elif args.output:
        output = args.output
    else:
        output = sys.stdin.read()

    # Validate
    validator = SOPValidator(args.contract)
    if args.check_delivery:
        result = validator.validate_delivery(output, args.check_delivery)
    else:
        result = validator.validate(output, "generic")

    # Output
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"✅ PASSED" if result["passed"] else "❌ FAILED", file=sys.stdout)
        if result["violations"]:
            print("\nViolations:")
            for v in result["violations"]:
                print(f"  [{v.get('action', 'block')}] {v.get('type')}: {v.get('detail')}")
        if args.verbose and result.get("checks_passed"):
            print("\nPassed checks:")
            for c in result["checks_passed"]:
                print(f"  ✓ {c}")
        print(f"\nValidator: {result.get('validator', 'unknown')}")
        print(f"Run ID: {result.get('run_id', 'N/A')}")

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
