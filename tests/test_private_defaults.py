"""Private records are never seeded from public demonstration data."""

from pathlib import Path
from unittest.mock import patch

from src.core.grok_bot import GrokBotRoutines, format_last_run, reset_grok_bot_routines
from src.core.s3_store import S3Store
from src.core.tenant import normalize_tenant, reset_tenant
from tests.fakes import MemoryS3Store
from tests.test_grok_bot import _nav_app
from web import create_app
from web.blueprints.grok_bot import bp


def test_disabled_modules_do_not_seed_or_construct_their_stores():
    reset_tenant(normalize_tenant({"modules": {"projects": False, "grok_bot": False}}, source_path="test"))
    try:
        with patch("src.core.grok_bot.get_grok_bot_routines") as routines, \
                patch("src.core.project_board.get_project_board") as projects:
            create_app(local_only=True)
            routines.assert_not_called()
            projects.assert_not_called()
    finally:
        reset_tenant()


def test_enabled_catalog_with_empty_storage_does_not_load_examples(tmp_path):
    store = MemoryS3Store()
    catalog = GrokBotRoutines(store=store, local_path=tmp_path / "routines.json")
    assert catalog.ensure_seeded() is False
    assert catalog.load() is None
    assert store.put_calls == 0
    assert not (tmp_path / "routines.json").exists()


def test_arbitrary_agent_filters_and_timezone_are_personal_configuration(tmp_path):
    reset_tenant(normalize_tenant({
        "human": {"timezone": "Asia/Tokyo"},
        "agents": [{"id": "orbit", "name": "Orbit Assistant"}],
    }, source_path="test"))
    catalog = GrokBotRoutines(store=MemoryS3Store(), local_path=tmp_path / "routines.json")
    catalog.save({"routines": [
        {"id": "weekly-review", "name": "Weekly review", "owner_agent": "orbit", "last_run_at": "2026-01-01T12:00:00Z"},
        {"id": "reading", "name": "Reading reminder", "owner_agent": "another-agent"},
    ]})
    reset_grok_bot_routines(catalog)
    try:
        html = _nav_app(bp).test_client().get("/grok-bot/?filter=orbit").get_data(as_text=True)
        assert "Orbit Assistant" in html
        assert "Weekly review" in html
        assert "Reading reminder" not in html
        assert "9:00PM JST" in html
        assert "Routines" in html
        assert "12:00PM UTC" in format_last_run("2026-01-01T12:00:00Z", "UTC")
    finally:
        reset_grok_bot_routines()
        reset_tenant()


def test_neutral_bucket_name_takes_precedence_and_legacy_alias_still_works():
    with patch.dict("os.environ", {"OPS_BUCKET": "new-private", "MEME_ASSETS_BUCKET": "legacy-private"}, clear=True):
        assert S3Store().bucket == "new-private"
        assert S3Store(bucket="explicit-private").bucket == "explicit-private"
    with patch.dict("os.environ", {"MEME_ASSETS_BUCKET": "legacy-private"}, clear=True):
        assert S3Store().bucket == "legacy-private"
