"""
Spend blueprint - Tech spending tracker for ops/engineering costs.
Tracks subscriptions, API/usage costs, and provides live AWS data when available.
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

from flask import Blueprint, render_template

from src.core.projects import (
    SHARED_PROJECT,
    UNALLOCATED_PROJECT,
    build_project_rollup,
    format_project_label,
    project_meta,
    subscription_shares,
)

bp = Blueprint("spend", __name__)


def _annotate_items(items: List[Dict]) -> List[Dict]:
    annotated = []
    for item in items:
        row = dict(item)
        shares = subscription_shares(item)
        row["project_label"] = format_project_label(item)
        if UNALLOCATED_PROJECT in shares and (
            len(shares) == 1 or shares.get(UNALLOCATED_PROJECT, 0) >= 0.5
        ):
            row["project_tone"] = UNALLOCATED_PROJECT
        else:
            row["project_tone"] = max(shares, key=shares.get)
        annotated.append(row)
    return annotated


def _load_tech_spend() -> Dict[str, Any]:
    """S3 ops/spend/tech_spend.json, else local data/tech_spend.json, else empty."""
    from src.core.tech_spend import load_tech_spend

    return load_tech_spend()


def _get_xai_token_usage(provider="xai") -> Optional[Dict[str, Any]]:
    """
    Get current month xAI token usage from the shared S3 monthly object
    (ops/usage/xai/{YYYY}/{MM}.json), with local fallback.
    """
    try:
        from src.core.token_tracker import get_month_usage

        now = datetime.now()
        usage = get_month_usage(provider, now.year, now.month)

        if usage["call_count"] == 0:
            return None

        # Heuristic only — not xAI billing. See token_tracker.estimate_cost_usd.
        estimated_cost = usage.get("total_cost_usd", 0.0)

        source = usage.get("source") or "local"
        by_project = usage.get("by_project") or {}
        project_parts = []
        for project_id, bucket in by_project.items():
            meta = project_meta(str(project_id))
            cost = round(float((bucket or {}).get("total_cost_usd") or 0), 2)
            calls = int((bucket or {}).get("call_count") or 0)
            pid = str(project_id)
            note = ""
            if pid == UNALLOCATED_PROJECT:
                note = "Missing project tag — shown on purpose."
            elif pid == SHARED_PROJECT:
                note = "Overhead that is not one product."
            project_parts.append(
                {
                    "id": pid,
                    "name": meta["name"],
                    "amount": cost,
                    "calls": calls,
                    "tokens": int((bucket or {}).get("total_tokens") or 0),
                    "note": note,
                }
            )
        project_parts.sort(key=lambda part: (-part["amount"], part["name"]))
        return {
            "amount": round(estimated_cost, 2),
            "unpriced_calls": usage.get("unpriced_call_count", 0),
            "tokens": usage["total_tokens"],
            "calls": usage["call_count"],
            "source": source,
            "period": f"{now.year}-{now.month:02d}",
            "by_project": by_project,
            "project_parts": project_parts,
            "legacy_untagged_xai_as_memes": int(
                usage.get("legacy_untagged_xai_as_memes") or 0
            ),
        }
    except Exception:
        return {
            "error": "Usage records could not be read. Check the private data format and storage permissions.",
            "source": "usage_read_failed",
        }


def _get_all_token_usage():
    providers = list(dict.fromkeys(os.environ.get("LIFE_OPS_USAGE_PROVIDERS", "xai").split(",")))
    providers = [value.strip() for value in providers if value.strip()]
    if len(providers) > 8 or any(not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", value) for value in providers):
        return {"error": "Invalid usage provider setting. Use up to eight comma-separated provider IDs."}
    found = []
    warnings = []
    for provider in providers:
        usage = _get_xai_token_usage(provider)
        if not usage:
            continue
        if usage.get("error"):
            warnings.append(f"{provider}: usage unavailable; saved ledger amounts retained.")
            continue
        if usage.get("unpriced_calls"):
            warnings.append(f"{provider}: some calls have no price. This provider's log is excluded from cost totals; saved ledger amounts are retained.")
        found.append((provider, usage))
    if not found:
        return {"error": " ".join(warnings)} if warnings else None
    by_project = {}
    replaces = []
    amount = 0.0
    for provider, usage in found:
        if usage.get("unpriced_calls"):
            continue
        replaces.append(provider + "-tokens")
        amount += usage["amount"]
        parts = usage.get("by_project") or {UNALLOCATED_PROJECT: {
            "total_cost_usd": usage["amount"], "call_count": usage["calls"], "total_tokens": usage["tokens"]}}
        for project, values in parts.items():
            bucket = by_project.setdefault(project, {"total_cost_usd": 0.0, "call_count": 0, "total_tokens": 0})
            for field in bucket:
                bucket[field] += values.get(field, 0)
    project_parts = [{"id": project, "name": project_meta(project)["name"],
                      "amount": values["total_cost_usd"], "calls": values["call_count"],
                      "tokens": values["total_tokens"], "note": "Missing project tag — shown on purpose." if project == UNALLOCATED_PROJECT else ""}
                     for project, values in by_project.items()]
    return {"amount": round(amount, 2), "calls": sum(usage["calls"] for _, usage in found),
            "tokens": sum(usage["tokens"] for _, usage in found), "replaces": replaces,
            "source": found[0][1]["source"] if len(found) == 1 else "mixed",
            "period": found[0][1]["period"], "by_project": by_project,
            "provider_label": "xAI / application usage" if providers == ["xai"] else " / ".join(providers) + " application usage",
            "project_parts": project_parts, "warnings": warnings,
            "providers": [{"id": provider, "source": usage["source"], "calls": usage["calls"]} for provider, usage in found],
            "legacy_untagged_xai_as_memes": sum(usage.get("legacy_untagged_xai_as_memes", 0) for _, usage in found)}


def _get_aws_current_month_cost() -> Optional[Dict[str, Any]]:
    from src.core.aws_costs import current_month_cost

    return current_month_cost()


def _calculate_totals(subscriptions: List[Dict], aws_live: Optional[Dict] = None, xai_usage: Optional[Dict] = None) -> Dict[str, float]:
    """Calculate fixed and variable monthly totals."""
    fixed_total = 0.0
    variable_total = 0.0
    
    for sub in subscriptions:
        # Include active and cancelling (still paying until cancelled)
        if sub.get('status') not in ('active', 'cancelling'):
            continue
            
        amount = sub.get('amount_usd', 0)
        cadence = sub.get('cadence', 'monthly')
        category = sub.get('category', 'fixed')
        
        # Skip AWS from config if we have live data
        if aws_live and not aws_live.get('error') and sub.get('id') == 'aws':
            continue
        
        # Skip xAI tokens from config if we have usage data
        if xai_usage and not xai_usage.get('error') and sub.get('id') in xai_usage.get('replaces', ['xai-tokens']):
            continue
        
        # Convert to monthly equivalent
        monthly_amount = 0
        if cadence == 'monthly':
            monthly_amount = amount
        elif cadence == 'yearly':
            monthly_amount = amount / 12
        elif cadence == 'usage':
            monthly_amount = amount
        
        # Add to appropriate category
        if category == 'variable':
            variable_total += monthly_amount
        else:
            fixed_total += monthly_amount
    
    # Add live AWS to variable if available
    if aws_live and not aws_live.get('error'):
        variable_total += aws_live.get('amount', 0)
    
    # Add xAI token usage to variable if available
    if xai_usage and not xai_usage.get('error'):
        variable_total += xai_usage.get('amount', 0)
    
    return {
        'fixed': round(fixed_total, 2),
        'variable': round(variable_total, 2),
        'total': round(fixed_total + variable_total, 2)
    }


def _count_by_status(subscriptions: List[Dict], cancelled: List[Dict]) -> Dict[str, int]:
    """Count subscriptions by status."""
    active = sum(1 for s in subscriptions if s.get('status') == 'active')
    cancelling = sum(1 for s in subscriptions if s.get('status') == 'cancelling')
    cancelled_count = len(cancelled)
    
    return {
        'active': active,
        'cancelling': cancelling,
        'cancelled': cancelled_count
    }


@bp.route("/")
def index():
    """Spend tracking dashboard."""
    # Load spend config
    spend_data = _load_tech_spend()
    subscriptions = spend_data.get('subscriptions', [])
    cancelled = spend_data.get('cancelled', [])
    
    # Try to get live data
    aws_live = _get_aws_current_month_cost()
    xai_usage = _get_all_token_usage()
    
    # Calculate totals and counts
    totals = _calculate_totals(subscriptions, aws_live, xai_usage)
    status_counts = _count_by_status(subscriptions, cancelled)
    
    # Organize items by category
    fixed_items = _annotate_items(
        [s for s in subscriptions if s.get("category") == "fixed"]
    )
    variable_items = _annotate_items(
        [s for s in subscriptions if s.get("category") == "variable"]
    )
    cancelled_items = _annotate_items(cancelled)

    project_rollup = build_project_rollup(
        subscriptions, aws_live=aws_live, xai_usage=xai_usage
    )
    
    return render_template(
        "spend/index.html",
        fixed_items=fixed_items,
        variable_items=variable_items,
        cancelled=cancelled_items,
        totals=totals,
        status_counts=status_counts,
        aws_live=aws_live,
        xai_usage=xai_usage,
        project_rollup=project_rollup,
        last_updated=spend_data.get('last_updated'),
        note=spend_data.get('note'),
        active_page="spend",
        section="spend",
        aws_enabled=os.environ.get('LIFE_OPS_AWS_COSTS', '').lower() == 'true',
        usage_providers=os.environ.get('LIFE_OPS_USAGE_PROVIDERS', 'xai'),
        ledger_source=spend_data.get('_source', 'provided'),
        ledger_warning=spend_data.get('_warning'),
    )
