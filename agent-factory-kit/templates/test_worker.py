"""
{{WORKER_NAME}} eval — known-correct test cases.

Tests the pure calculation/logic functions in
app/agents/uae/{{worker_slug}}.py directly.
No DB, no async, no LangGraph needed.

Ground truth: {{Law / policy reference}}

Run: pytest evals/test_cases/test_{{worker_slug}}_worker.py -v
"""

from __future__ import annotations

import sys
from decimal import Decimal
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

# Import the pure functions to test:
from app.agents.uae.{{worker_slug}} import (
    _validate_inputs,
    # _calculate_{{metric}},
    # _check_{{rule}},
    # Add specific functions here
)


# ─── Known-correct fixtures ───────────────────────────────────────────────────
# Fill in with realistic UAE test data.

COMPANY_OK = {
    "id": "co-001",
    "name_en": "Gulf Holdings Company A",
    "mohre_establishment_id": "CO00001",
}

# Add employee/payroll fixtures here.


# ─── Happy path (law-grounded) ────────────────────────────────────────────────

def test_happy_path_known_value():
    """
    {{Describe: what input, what law basis, what expected output}}
    {{e.g. Art. 51: 6 years, basic 10000 → 45000.00}}
    """
    # result = _calculate_{{metric}}({...})
    # assert result["{{key}}"] == "{{expected}}"
    pass  # replace with real assertion


# ─── Guard tests ──────────────────────────────────────────────────────────────

def test_missing_required_field_blocks():
    """Missing {{key_field}} → BLOCKED, no output computed."""
    result = _validate_inputs({
        "{{key_field}}": None,
        "{{other_field}}": "value",
    })
    assert result["blocked"] is True
    assert "{{key_field}}" in result["blocked_reason"].lower()


def test_valid_inputs_not_blocked():
    """Clean inputs must not be blocked."""
    result = _validate_inputs({
        "{{key_field}}": "{{valid_value}}",
    })
    assert result["blocked"] is False


# ─── Boundary tests ───────────────────────────────────────────────────────────

def test_{{boundary_name}}():
    """
    {{Describe the boundary: e.g. exactly at the threshold}}
    """
    pass  # replace with real assertion


# ─── Idempotency ──────────────────────────────────────────────────────────────

def test_idempotent_same_inputs():
    """Same inputs twice → identical output."""
    state = {"{{key}}": "{{value}}"}
    r1 = _validate_inputs(state.copy())
    r2 = _validate_inputs(state.copy())
    assert r1 == r2


# ─── Known values table ───────────────────────────────────────────────────────

@pytest.mark.parametrize("input_val,expected", [
    # ("{{input}}", "{{expected}}"),  # {{law reference}}
])
def test_known_values_table(input_val, expected):
    pass  # replace with real assertion
