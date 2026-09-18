"""Synthetic cache tests, including write freshness and private responses."""

import os
from unittest.mock import patch

from flask import Flask, url_for

from src.core.project_board import ProjectBoard
from src.core.tenant import normalize_tenant
from tests.fakes import MemoryS3Store
from web.performance import register_performance


def board_at(tmp_path):
    store = MemoryS3Store()
    board = ProjectBoard(store=store, local_path=tmp_path / "board.json",
                         tenant=normalize_tenant({"projects": []}, source_path="test"))
    board.save({"projects": [{"id": "example", "name": "Example", "lane": "idea"}]})
    return board


def test_display_cache_reduces_reads_and_returns_independent_values(tmp_path):
    board = board_at(tmp_path)
    with patch.object(board.store, "get_json", wraps=board.store.get_json) as reads:
        first = board.view()
        first["projects"][0]["name"] = "Changed only in memory"
        assert board.view()["projects"][0]["name"] == "Example"
        assert reads.call_count == 1


def test_expiry_and_mutations_observe_external_writes(tmp_path):
    board = board_at(tmp_path)
    with patch("src.core.project_board.time.monotonic", return_value=100):
        board.view()
    # Another writer adds information after the display cache fills.
    remote = board.load()
    remote["projects"][0]["summary"] = "External update"
    board.store.put_json(board.s3_key(), remote)
    with patch("src.core.project_board.time.monotonic", return_value=101):
        board.move_lane("example", "active")
        assert board.load()["projects"][0]["summary"] == "External update"
        assert board.view()["projects"][0]["lane"] == "active"
    remote["projects"][0]["name"] = "Renamed elsewhere"
    board.store.put_json(board.s3_key(), remote)
    with patch("src.core.project_board.time.monotonic", return_value=117):
        assert board.view()["projects"][0]["name"] == "Renamed elsewhere"


def test_another_worker_save_invalidates_display_cache(tmp_path):
    first = board_at(tmp_path)
    second = ProjectBoard(store=first.store, local_path=first.local_path, tenant=first.tenant)
    first.view()
    stamp = first.local_path.stat().st_mtime_ns
    second.update_card("example", name="Updated in another worker")
    os.utime(first.local_path, ns=(stamp + 1000000, stamp + 1000000))
    assert first.view()["projects"][0]["name"] == "Updated in another worker"


def asset_app(tmp_path):
    app = Flask(__name__, static_folder=str(tmp_path), static_url_path="/static")
    register_performance(app)

    @app.get("/")
    def home():
        return url_for("static", filename="app.js")

    @app.get("/api/private")
    def private():
        return {"fictional": True}

    return app


def test_only_matching_versioned_assets_are_cached(tmp_path):
    (tmp_path / "app.js").write_text("/* version one */")
    client = asset_app(tmp_path).test_client()
    response = client.get("/")
    versioned_url = response.text
    assert "?v=" in versioned_url
    assert response.headers["Cache-Control"] == "no-store"
    assert client.get("/api/private").headers["Cache-Control"] == "no-store"
    assert client.get(versioned_url).headers["Cache-Control"] == "private, max-age=31536000, immutable"
    for path in ("/static/app.js", "/static/app.js?v=old-version", "/static/missing.js?v=bad"):
        assert "immutable" not in client.get(path).headers.get("Cache-Control", "")
    (tmp_path / "app.js").write_text("/* version two */")
    updated = asset_app(tmp_path).test_client()
    assert updated.get("/").text != versioned_url
    assert "immutable" not in updated.get(versioned_url).headers.get("Cache-Control", "")
