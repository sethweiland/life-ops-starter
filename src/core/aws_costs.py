"""Opt-in, cached AWS Cost Explorer reads using Boto3's credential chain."""

from datetime import date, datetime, timezone
import math
import os
from threading import Lock
import time


_lock = Lock()
_cache = {}
CACHE_SECONDS = 3600


def current_month_cost():
    if os.environ.get("LIFE_OPS_AWS_COSTS", "").lower() != "true":
        return None
    today = date.today()
    cache_key = (today.isoformat(), os.environ.get("AWS_PROFILE"), os.environ.get("AWS_ROLE_ARN"))
    with _lock:
        cached = _cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            return dict(cached[1])
        start = today.replace(day=1)
        if start == today:
            result = {"amount": 0.0, "source": "live_api", "period": "No complete days this month"}
        else:
            try:
                import boto3
                from botocore.config import Config

                client = boto3.client("ce", region_name="us-east-1", config=Config(
                    connect_timeout=2, read_timeout=5, retries={"mode": "standard", "total_max_attempts": 2}))
                response = client.get_cost_and_usage(
                    TimePeriod={"Start": start.isoformat(), "End": today.isoformat()},
                    Granularity="MONTHLY", Metrics=["UnblendedCost"])
                rows = response.get("ResultsByTime") or []
                if not rows:
                    raise ValueError("Empty cost response")
                values = [row["Total"]["UnblendedCost"] for row in rows]
                amounts = [float(value["Amount"]) for value in values]
                if any(value.get("Unit") != "USD" for value in values) or not all(map(math.isfinite, amounts)):
                    raise ValueError("Unsupported cost response")
                result = {"amount": round(sum(amounts), 2), "source": "live_api",
                          "period": f"{start.isoformat()} to {today.isoformat()} (end exclusive)"}
            except Exception:
                # Provider exceptions may contain account IDs, ARNs, or signed URLs.
                result = {"error": "AWS costs unavailable. Check the runtime identity, Cost Explorer access and billing setup; saved amounts are retained.",
                          "source": "api_failed"}
        result["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _cache.clear()
        _cache[cache_key] = (time.monotonic(), result)
        return dict(result)


def reset_cost_cache():
    with _lock:
        _cache.clear()
