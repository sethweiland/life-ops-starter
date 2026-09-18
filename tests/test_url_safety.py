"""Imported records must remain data, including inside links and buttons."""

from pathlib import Path

import pytest

from src.core.calendar import normalize_event
from src.core.project_board import normalize_project_card
from src.core.tenant import _safe_href
from src.core.urls import safe_url
from tests.test_x_activity import _fixture, DATE


@pytest.mark.parametrize("value", [
    "javascript:alert(1)", "JaVaScRiPt:alert(1)", "java\nscript:alert(1)",
    "\x00https://example.com", "data:text/html,hello", "//untrusted.example",
    "/\\untrusted.example", "https://user:password@example.com", "https://example.com:invalid",
    "https://", "https://exa mple.com", "file:///private/file", "vbscript:hello",
])
def test_unsafe_link_is_rejected_everywhere(value):
    assert safe_url(value) is None
    assert _safe_href(value) is None
    event = normalize_event({"title": "Demo", "start": "2026-09-16", "url": value})
    assert event["url"] is None
    card = normalize_project_card({"id": "demo", "links": {"repo": value, "prod": value}})
    assert card["links"] == {"repo": None, "prod": None}


def test_allowed_links_and_local_navigation():
    assert safe_url("https://example.com/page?name=hello#part")
    assert safe_url("HTTP://example.com")
    assert _safe_href("/projects/?project=demo")
    assert safe_url("/projects/") is None


def test_draft_links_and_identifiers_do_not_create_executable_markup():
    from tests.test_x_activity import XActivityFlaskTests

    test = XActivityFlaskTests()
    test.setUp()
    try:
        fixture = _fixture()
        fixture["candidates"][0]["media_urls"] = ["javascript:alert(1)", "https://example.com/image.jpg"]
        fixture["candidates"][0]["id"] = "quoted');alert(1);//"
        test.queue.save(DATE, fixture)
        html = test.client.get(f"/x/?date={DATE}").get_data(as_text=True)
        assert "javascript:" not in html
        assert 'href="https://example.com/image.jpg"' in html
        assert "onclick=" not in html
        assert '<script src="/static/x-activity.js"></script>' in html
    finally:
        test.tearDown()
