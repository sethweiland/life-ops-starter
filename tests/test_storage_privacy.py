"""Storage names and untrusted dates must not escape into paths or logs."""

import logging
from unittest.mock import patch

import pytest

from src.core.grok_bot import GrokBotRoutines
from src.core.project_board import ProjectBoard
from src.core.tenant import normalize_tenant
from src.core.token_tracker import _append_s3
from src.core.x_activity import XActivityQueue, require_date
from tests.fakes import MemoryS3Store


@pytest.mark.parametrize("value", [
    "../outside", "/tmp/outside", "2026-09-18/../../outside",
    "2026-09-18\nFORGED_LOG", "2026-02-30", "2026-99-01", "２０２６-09-18",
])
def test_invalid_dates_are_rejected_before_any_storage_access(tmp_path, value):
    store = MemoryS3Store()
    queue = XActivityQueue(store=store, local_dir=tmp_path / "queue")
    for action in (lambda: queue.load(value), lambda: queue.save(value, {})):
        with pytest.raises(ValueError) as error:
            action()
        assert value not in str(error.value)
    assert not queue.local_dir.exists()
    assert store.objects == {}


def test_valid_leap_day_preserves_the_date_contract():
    assert require_date("2028-02-29") == "2028-02-29"


def test_queue_cannot_read_or_overwrite_a_symlink_outside_storage(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text('{"fictional": "private"}')
    directory = tmp_path / "queue"
    directory.mkdir()
    try:
        (directory / "2026-09-18.json").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable on this test platform")
    queue = XActivityQueue(store=MemoryS3Store(configured=False), local_dir=directory)
    with pytest.raises(ValueError, match="storage directory"):
        queue.load("2026-09-18")
    with pytest.raises(ValueError, match="storage directory"):
        queue.save("2026-09-18", {"candidates": []})
    assert outside.read_text() == '{"fictional": "private"}'
    assert queue.list_dates() == []


def test_queue_listing_skips_impossible_dates_and_keeps_valid_records(tmp_path):
    store = MemoryS3Store()
    store.put_json("ops/queue/x-activity/2026-02-30.json", {"candidates": []})
    (tmp_path / "2026-99-01.json").write_text('{"candidates": []}')
    queue = XActivityQueue(store=store, local_dir=tmp_path)
    queue.save("2026-09-18", {"date": "2026-09-18", "candidates": []})
    assert [row["date"] for row in queue.list_dates()] == ["2026-09-18"]


def test_storage_success_logs_omit_bucket_identifiers(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    store = MemoryS3Store()
    store.bucket = "fictional-private-storage-sentinel"
    queue = XActivityQueue(store=store, local_dir=tmp_path / "queue")
    queue.save("2026-09-18", {"candidates": []})
    queue.load("2026-09-18")
    board = ProjectBoard(store=store, local_path=tmp_path / "board.json",
                         tenant=normalize_tenant({}, source_path="test"))
    board.save({"projects": []})
    board.load()
    catalog = GrokBotRoutines(store=store, local_path=tmp_path / "routines.json")
    catalog.save({"routines": []})
    catalog.load()
    event = {"id": "fictional", "provider": "example", "timestamp": "2026-09-18T12:00:00Z"}
    _append_s3(store, event, {"events": [event]})
    assert store.bucket not in caplog.text
    assert "Saved" in caplog.text


def test_queue_failure_logs_omit_provider_details_and_local_paths(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    queue = XActivityQueue(store=MemoryS3Store(), local_dir=tmp_path / "fictional-private-path")
    message = "fictional-sensitive-provider-response\nFORGED_LOG"
    with patch.object(queue.store, "put_object", side_effect=RuntimeError(message)):
        queue.save("2026-09-18", {"candidates": []})
    with patch.object(queue.store, "get_json", side_effect=RuntimeError(message)):
        assert queue.load("2026-09-18") == {"candidates": []}
    assert message not in caplog.text
    assert "FORGED_LOG" not in caplog.text
    assert str(queue.local_dir) not in caplog.text
