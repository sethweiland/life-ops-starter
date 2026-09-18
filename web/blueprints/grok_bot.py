"""
Grok Bot routines blueprint — catalog of recurring cron/event automations.

Read-only. Start/stop belongs in Grok Bot settings, not this app.
"""

from flask import Blueprint, render_template, request

from src.core.grok_bot import (
    filter_routines,
    format_last_run,
    get_grok_bot_routines,
    group_by_category,
    summarize,
)
from src.core.tenant import load_tenant


bp = Blueprint("grok_bot", __name__)


def _catalog():
    return get_grok_bot_routines()


@bp.route("/")
def index():
    selected_filter = request.args.get("filter", "all")

    catalog = _catalog()
    try:
        catalog.ensure_seeded()
    except Exception:
        pass

    data = catalog.load()
    summary = summarize(data)
    routines = list((data or {}).get("routines") or [])
    tenant = load_tenant()
    names = {agent["id"]: agent["name"] for agent in tenant.agents}
    agents = sorted(summary["agent_counts"])
    filters = ("all", "enabled", *agents)
    if selected_filter not in filters:
        selected_filter = "all"
    filtered = []
    for routine in filter_routines(routines, selected_filter):
        item = dict(routine)
        item["last_run_display"] = format_last_run(routine.get("last_run_at"), tenant.timezone)
        filtered.append(item)

    grouped = group_by_category(filtered)

    return render_template(
        "grok_bot/index.html",
        active_page="grok_bot",
        section="grok_bot",
        data=data,
        summary=summary,
        grouped=grouped,
        selected_filter=selected_filter,
        agents=agents,
        agent_names=names,
        filtered_count=len(filtered),
    )
