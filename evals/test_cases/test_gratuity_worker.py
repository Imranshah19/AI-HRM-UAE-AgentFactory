"""
Gratuity worker eval — known-correct test cases.

Tests the pure calculation functions in app/agents/uae/gratuity.py directly.
No DB, no async, no LangGraph needed.

Ground truth: Federal Decree-Law No. 33/2021, Article 51 worked examples.

Run: pytest evals/test_cases/test_gratuity_worker.py -v
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.agents.uae.gratuity import (
    _calculate_gratuity,
    _calculate_settlement,
    _determine_scenario,
    _fetch_service,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def gratuity(basic: float, years: float, reason: str = "termination") -> str:
    """Run the full calculation pipeline for a given input."""
    state = {
        "basic_salary": str(basic),
        "years_of_service": years,
        "exit_reason": reason,
    }
    state.update(_calculate_gratuity(state))
    return state["gratuity_amount"]


def total(basic: float, years: float, reason: str = "termination",
          unpaid: str = "0", leave_enc: str = "0") -> str:
    state = {
        "basic_salary": str(basic),
        "years_of_service": years,
        "exit_reason": reason,
        "gratuity_amount": gratuity(basic, years, reason),
        "unpaid_salary": unpaid,
        "leave_encashment": leave_enc,
    }
    state.update(_calculate_settlement(state))
    return state["total_settlement"]


# ─── Art. 51 worked examples (ground truth from the law) ──────────────────────

def test_6yr_happy_path_art51():
    """
    Art. 51 official worked example: 6 years, basic 10000.
    first 5 years: 5 × 21 × (10000/30) = 35000
    year 6:        1 × 30 × (10000/30) = 10000
    total:         45000.00
    """
    assert gratuity(10000, 6.0) == "45000.00"


def test_5yr_exact_boundary():
    """
    Exact 5-year boundary. Must use 21-days rate, not 30.
    5 × 21 × (10000/30) = 35000.00
    """
    assert gratuity(10000, 5.0) == "35000.00"


def test_under_1yr_is_nil():
    """< 1 year → no entitlement. Returns "0.00" — valid zero, not an error."""
    result = _calculate_gratuity({
        "basic_salary": "8000",
        "years_of_service": 0.67,
        "exit_reason": "resignation",
    })
    assert result["gratuity_amount"] == "0.00"
    assert result["gratuity_days"] == 0.0
    assert result["capped"] is False


def test_cap_applied_at_24_months():
    """
    30 years, basic 10000.
    Uncapped = 855 × 333.33 = 285000. Cap = 24 × 10000 = 240000.
    """
    result = _calculate_gratuity({
        "basic_salary": "10000",
        "years_of_service": 30.0,
        "exit_reason": "completion",
    })
    assert result["gratuity_amount"] == "240000.00"
    assert result["capped"] is True


def test_cap_not_applied_when_below_limit():
    """6 years: 45000 < 240000. Must not be flagged as capped."""
    result = _calculate_gratuity({
        "basic_salary": "10000",
        "years_of_service": 6.0,
        "exit_reason": "termination",
    })
    assert result["capped"] is False
    assert result["gratuity_amount"] == "45000.00"


# ─── Rate boundary tests ───────────────────────────────────────────────────────

def test_rate_switches_at_5yr_boundary():
    """Year 5 uses 21-day rate; year 6 adds 30-day rate."""
    g5 = Decimal(gratuity(10000, 5.0))
    g6 = Decimal(gratuity(10000, 6.0))
    year_6_increment = g6 - g5
    # Year 6: 30 days × (10000/30) = 10000
    assert year_6_increment == Decimal("10000.00")


def test_daily_rate_is_basic_div_30():
    """
    Basic 9000, 1 year: 21 × (9000/30) = 21 × 300 = 6300.
    """
    assert gratuity(9000, 1.0) == "6300.00"


# ─── Settlement calculation ────────────────────────────────────────────────────

def test_settlement_adds_unpaid_and_leave_encashment():
    """total_settlement = gratuity + unpaid_salary + leave_encashment"""
    t = total(10000, 6.0, unpaid="5000", leave_enc="2000")
    assert t == "52000.00"  # 45000 + 5000 + 2000


def test_settlement_with_zero_extras():
    """With no extras, total == gratuity."""
    assert total(10000, 6.0) == "45000.00"


# ─── Idempotency — deterministic, no randomness ───────────────────────────────

def test_idempotent_same_inputs():
    state = {"basic_salary": "10000", "years_of_service": 6.0, "exit_reason": "termination"}
    r1 = _calculate_gratuity(state.copy())
    r2 = _calculate_gratuity(state.copy())
    assert r1["gratuity_amount"] == r2["gratuity_amount"]
    assert r1["gratuity_days"]   == r2["gratuity_days"]
    assert r1["capped"]          == r2["capped"]


# ─── Service year calculation ──────────────────────────────────────────────────

def test_service_from_dates_6yr():
    result = _fetch_service({"join_date": "2020-01-01", "exit_date": "2026-01-01"})
    assert abs(result["years_of_service"] - 6.0) < 0.01


def test_service_from_dates_under_1yr():
    result = _fetch_service({"join_date": "2025-05-01", "exit_date": "2026-01-01"})
    assert result["years_of_service"] < 1.0


def test_service_missing_exit_date_uses_today():
    """Missing exit_date must not raise — defaults to today."""
    result = _fetch_service({"join_date": "2020-01-01"})
    assert result["years_of_service"] > 0.0


# ─── Scenario notes ───────────────────────────────────────────────────────────

def test_under_1yr_notes_say_nil():
    state = {"years_of_service": 0.5, "exit_reason": "resignation"}
    result = _determine_scenario(state)
    assert "1 year" in result["notes"].lower()


def test_over_5yr_termination_notes():
    state = {"years_of_service": 6.0, "exit_reason": "termination"}
    result = _determine_scenario(state)
    assert "termination" in result["notes"].lower() or "full" in result["notes"].lower()


# ─── NEW LAW: resignation = termination (no reduction) ───────────────────────
#
# Federal Decree-Law No. 33/2021 abolished old-law resignation reductions.
# Under the new law, resignation and termination must produce IDENTICAL amounts.
#
# These tests are marked xfail because the current code (gratuity.py lines 102-106)
# still applies the old-law reduction. Remove those lines to fix.
#
# Once fixed, remove the xfail markers.

@pytest.mark.xfail(
    reason="Code gap: gratuity.py lines 102-106 apply old-law reductions. "
           "Federal Decree-Law 33/2021 Art. 51 abolished them. "
           "Remove the resignation reduction block to fix.",
    strict=True,
)
def test_resign_4yr_equals_terminate_4yr():
    """4 years: resign must equal terminate (28000.00) — no 2/3 reduction."""
    g_resign    = gratuity(10000, 4.0, reason="resignation")
    g_terminate = gratuity(10000, 4.0, reason="termination")
    assert g_resign == g_terminate, (
        f"Resign={g_resign}, Terminate={g_terminate} — "
        "old-law reduction still active (expected equal under new law)"
    )


@pytest.mark.xfail(
    reason="Code gap: same resignation reduction bug, 2-year case.",
    strict=True,
)
def test_resign_2yr_equals_terminate_2yr():
    """2 years: resign must equal terminate (14000.00) — no 1/3 reduction."""
    g_resign    = gratuity(10000, 2.0, reason="resignation")
    g_terminate = gratuity(10000, 2.0, reason="termination")
    assert g_resign == g_terminate


def test_resign_over_5yr_already_equals_terminate():
    """
    > 5 years resignation already gives full gratuity in both old and new law.
    This passes with the current code — useful as a sanity check.
    """
    g_resign    = gratuity(10000, 6.0, reason="resignation")
    g_terminate = gratuity(10000, 6.0, reason="termination")
    assert g_resign == g_terminate == "45000.00"


# ─── Known values table (from the skill) ──────────────────────────────────────

@pytest.mark.parametrize("years,basic,expected", [
    (6.0, 10000, "45000.00"),
    (5.0, 10000, "35000.00"),
    (1.0, 10000, "7000.00"),    # 1 × 21 × (10000/30) = 7000
    (1.0, 9000,  "6300.00"),    # 1 × 21 × (9000/30)  = 6300
    (30.0, 10000, "240000.00"), # capped
])
def test_known_values_table(years, basic, expected):
    assert gratuity(basic, years) == expected
