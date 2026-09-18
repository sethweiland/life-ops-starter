"""Billing connections are explicit, bounded, and cannot hide saved costs."""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from src.core.aws_costs import current_month_cost, reset_cost_cache
from src.core.projects import build_project_rollup
from src.core.tech_spend import normalize_ledger
from src.core.token_tracker import _build_event, _summarize, _with_totals
from web.blueprints.spend import _calculate_totals, _get_all_token_usage


@pytest.fixture(autouse=True)
def isolated_costs():
    reset_cost_cache()
    with patch.dict("os.environ", {}, clear=True), patch("src.core.aws_costs.date") as clock:
        clock.today.return_value = date(2026, 9, 16)
        yield
    reset_cost_cache()


def test_cost_explorer_never_connects_without_explicit_opt_in():
    with patch("boto3.client", side_effect=AssertionError("Must not connect")), patch.dict(
        "os.environ", {"AWS_ACCESS_KEY_ID": "fictional", "AWS_SECRET_ACCESS_KEY": "fictional"}
    ):
        assert current_month_cost() is None


def test_cost_explorer_supports_profiles_without_environment_key_pair_and_caches():
    client = Mock()
    client.get_cost_and_usage.return_value = {"ResultsByTime": [
        {"Total": {"UnblendedCost": {"Amount": "12.34", "Unit": "USD"}}}]}
    with patch.dict("os.environ", {"LIFE_OPS_AWS_COSTS": "true", "AWS_PROFILE": "fictional"}), \
            patch("boto3.client", return_value=client) as make_client:
        assert current_month_cost()["amount"] == 12.34
        assert current_month_cost()["amount"] == 12.34
        assert make_client.call_count == client.get_cost_and_usage.call_count == 1
    assert client.get_cost_and_usage.call_args.kwargs["TimePeriod"] == {"Start": "2026-09-01", "End": "2026-09-16"}


def test_provider_error_is_redacted_and_saved_amount_remains_in_both_totals():
    with patch.dict("os.environ", {"LIFE_OPS_AWS_COSTS": "true"}), \
            patch("boto3.client", side_effect=RuntimeError("PRIVATE_ACCOUNT_AND_SECRET")):
        error = current_month_cost()
    assert "PRIVATE" not in str(error)
    ledger = [{"id": "aws", "category": "variable", "cadence": "usage", "status": "active", "amount_usd": 12}]
    assert _calculate_totals(ledger, aws_live=error)["total"] == 12
    assert build_project_rollup(ledger, aws_live=error)["total"] == 12
    assert _calculate_totals([], aws_live={"amount": 12})["total"] == 12
    assert build_project_rollup([], aws_live={"amount": 12})["total"] == 12


def test_complete_provider_logs_replace_only_their_own_saved_rows():
    data = {
        "openai": {"total_tokens": 20, "total_cost_usd": 2, "call_count": 1, "source": "local"},
        "anthropic": {"total_tokens": 40, "total_cost_usd": 3, "call_count": 1, "source": "s3"},
    }
    with patch.dict("os.environ", {"LIFE_OPS_USAGE_PROVIDERS": "openai,anthropic"}), \
            patch("src.core.token_tracker.get_month_usage", side_effect=lambda provider, *_: data[provider]):
        usage = _get_all_token_usage()
    assert usage["amount"] == 5 and usage["calls"] == 2
    ledger = [{"id": "openai-tokens", "amount_usd": 99, "category": "variable", "status": "active", "cadence": "usage"},
              {"id": "other", "amount_usd": 7, "category": "fixed", "status": "active", "cadence": "monthly"}]
    assert _calculate_totals(ledger, xai_usage=usage)["total"] == 12
    assert build_project_rollup(ledger, xai_usage=usage)["total"] == 12


def test_non_xai_token_counts_do_not_invent_a_cost():
    event = _build_event("openai", "fictional-model", 100, 100, None, project="demo")
    assert event["estimated_cost_usd"] is None
    usage = _summarize(_with_totals({"provider": "openai"}, [event]), "local")
    assert usage["unpriced_call_count"] == 1
    with patch.dict("os.environ", {"LIFE_OPS_USAGE_PROVIDERS": "openai"}), \
            patch("src.core.token_tracker.get_month_usage", return_value=usage):
        summary = _get_all_token_usage()
    assert summary["warnings"] and summary["replaces"] == []
    ledger = [{"id": "openai-tokens", "amount_usd": 8, "category": "variable", "status": "active", "cadence": "usage"}]
    assert _calculate_totals(ledger, xai_usage=summary)["total"] == 8
    assert build_project_rollup(ledger, xai_usage=summary)["total"] == 8


@pytest.mark.parametrize("value", ["not a number", "NaN", float("inf"), -3])
def test_invalid_expense_is_rejected(value):
    assert normalize_ledger({"subscriptions": [{"amount_usd": value}]}) is None


def test_annual_costs_and_explicit_zero_token_cost():
    ledger = [{"id": "annual", "amount_usd": 120, "category": "fixed", "status": "active", "cadence": "yearly"}]
    assert _calculate_totals(ledger)["total"] == 10
    with patch("src.core.token_tracker.get_month_usage", return_value={"total_tokens": 1000, "total_cost_usd": 0, "call_count": 1}):
        assert _get_all_token_usage()["amount"] == 0
