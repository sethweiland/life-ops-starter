"""Exercise the actual app boundary with synthetic records and no network."""

import hashlib
import re
import time
from unittest.mock import patch

import pytest

from scripts.setup_auth import generate_auth, main as setup_auth_main
from src.core.auth_config import hosted_auth_settings
from src.core.project_board import ProjectBoard, reset_project_board
from src.core.tenant import normalize_tenant, reset_tenant
from src.core.x_activity import XActivityQueue, reset_x_activity_queue
from tests.fakes import MemoryS3Store
from tests.test_x_activity import DATE, FOLLOW_ID, POST_ID, REPLY_ID, _fixture
from web import create_app
from web.security import SESSION_SECONDS


ORIGIN = "https://ops.example.test"
KEY = "A" * 43  # Deliberately fictional; real installations use setup_auth.py.
ENV = {
    "LIFE_OPS_ORIGIN": ORIGIN,
    "LIFE_OPS_OWNER_KEY_SHA256": hashlib.sha256(KEY.encode()).hexdigest(),
    "LIFE_OPS_SESSION_SECRET": "B" * 64,
    "AWS_EC2_METADATA_DISABLED": "true",
}


@pytest.fixture
def secured(tmp_path):
    tenant = normalize_tenant({
        "modules": {"x": True, "projects": True, "calendar": False, "spend": False, "grok_bot": False},
        "projects": [{"id": "demo", "name": "Demo", "lane": "idea"}],
    }, source_path="test")
    reset_tenant(tenant)
    queue = XActivityQueue(store=MemoryS3Store(), local_dir=tmp_path / "drafts")
    queue.save(DATE, _fixture())
    board = ProjectBoard(store=MemoryS3Store(), local_path=tmp_path / "board.json")
    reset_x_activity_queue(queue)
    reset_project_board(board)
    try:
        with patch.dict("os.environ", ENV, clear=True), \
                patch("boto3.client", side_effect=AssertionError("Cloud access forbidden")), \
                patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")):
            app = create_app()
            app.testing = True
            yield app, queue, board
    finally:
        reset_tenant()
        reset_x_activity_queue()
        reset_project_board()


def csrf_from(response):
    html = response.get_data(as_text=True)
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not match:
        match = re.search(r'name="csrf-token" content="([^"]+)"', html)
    assert match, html
    return match.group(1)


def login(client):
    token = csrf_from(client.get("/auth/login", base_url=ORIGIN))
    response = client.post("/auth/login", base_url=ORIGIN,
                           headers={"Origin": ORIGIN, "Referer": ORIGIN + "/auth/login"},
                           data={"access_key": KEY, "csrf_token": token})
    assert response.status_code == 302
    return csrf_from(client.get(f"/x/?date={DATE}", base_url=ORIGIN))


def post(client, path, token=None, **kwargs):
    headers = {"Origin": ORIGIN, "Referer": ORIGIN + "/"}
    if token:
        headers["X-CSRFToken"] = token
    headers.update(kwargs.pop("headers", {}))
    return client.post(path, base_url=ORIGIN, headers=headers, **kwargs)


def test_hosted_boot_fails_before_loading_any_private_stores():
    with patch.dict("os.environ", {}, clear=True), patch("src.core.tenant.load_tenant") as tenant:
        with pytest.raises(ValueError, match="LIFE_OPS_ORIGIN"):
            create_app()
        tenant.assert_not_called()


@pytest.mark.parametrize("name,value", [
    ("LIFE_OPS_ORIGIN", "http://ops.example.test"),
    ("LIFE_OPS_ORIGIN", "https://owner:PRIVATE@ops.example.test"),
    ("LIFE_OPS_ORIGIN", "https://ops.example.test/path"),
    ("LIFE_OPS_ORIGIN", "https://.example.test"),
    ("LIFE_OPS_ORIGIN", "https://ops.example.test:bad"),
    ("LIFE_OPS_OWNER_KEY_SHA256", "PRIVATE"),
    ("LIFE_OPS_SESSION_SECRET", "PRIVATE"),
    ("LIFE_OPS_PROXY_HOPS", "PRIVATE"),
])
def test_hosted_config_validation_never_echoes_values(name, value):
    with pytest.raises(ValueError) as error:
        hosted_auth_settings({**ENV, name: value})
    assert "PRIVATE" not in str(error.value)


def test_anonymous_requests_cannot_read_or_mutate_records(secured):
    app, queue, board = secured
    client = app.test_client()
    with patch("src.core.tenant.load_tenant", side_effect=AssertionError("Private read")):
        page = client.get("/auth/login", base_url=ORIGIN)
        assert page.status_code == 200
        assert "Demo" not in page.get_data(as_text=True)
        for path in ["/", "/projects/", "/spend/", "/x/", "/grok-bot/"]:
            response = client.get(path, base_url=ORIGIN)
            assert response.status_code == 302
            assert response.location == "/auth/login"
        assert client.get(f"/x/api/candidates/{DATE}", base_url=ORIGIN).status_code == 401
        for action in ["approve", "skip", "update-body"]:
            response = post(client, f"/x/api/candidates/{DATE}/{action}/{FOLLOW_ID}", json={})
            assert response.status_code == 401
        assert post(client, "/projects/api/projects/demo/lane", json={"lane": "active"}).status_code == 401
    assert queue.load(DATE)["candidates"][0]["status"] == "pending"
    assert board.load()["projects"][0]["lane"] == "idea"
    assert client.get("/healthz", base_url="http://internal").json == {"status": "ok"}


def test_login_requires_valid_csrf_key_and_origin(secured):
    app, _, _ = secured
    client = app.test_client()
    assert post(client, "/auth/login", data={"access_key": KEY}).status_code == 400
    token = csrf_from(client.get("/auth/login", base_url=ORIGIN))
    assert post(client, "/auth/login", data={"access_key": "wrong", "csrf_token": token}).status_code == 401
    assert post(client, "/auth/login", data={"access_key": KEY, "csrf_token": token},
                headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.get(f"/x/api/candidates/{DATE}", base_url=ORIGIN).status_code == 401
    login(client)
    assert client.get(f"/x/api/candidates/{DATE}", base_url=ORIGIN).status_code == 200


def test_cross_origin_forms_missing_foreign_and_stale_tokens_do_not_mutate(secured):
    app, queue, board = secured
    client = app.test_client()
    anonymous_token = csrf_from(client.get("/auth/login", base_url=ORIGIN))
    token = login(client)
    foreign_token = login(app.test_client())
    routes = [f"/x/api/candidates/{DATE}/{action}/{FOLLOW_ID}" for action in ["approve", "skip", "update-body"]]
    routes.append("/projects/api/projects/demo/lane")
    for path in routes:
        assert post(client, path, token, data={"body": "changed"},
                    headers={"Origin": "https://untrusted.example"}).status_code == 403
        for bad_token in [None, "invalid", foreign_token, anonymous_token]:
            assert post(client, path, bad_token, json={"body": "changed", "lane": "active"}).status_code == 400
        assert post(client, path, token, json={}, headers={"Origin": "null"}).status_code == 403
        assert post(client, path, token, json={}, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
        assert post(client, path, token, json={}, headers={"Referer": "https://untrusted.example/"}).status_code == 400
    assert queue.load(DATE)["candidates"][0]["status"] == "pending"
    assert board.load()["projects"][0]["lane"] == "idea"


def test_authenticated_valid_requests_preserve_all_mutation_flows(secured):
    app, queue, board = secured
    client = app.test_client()
    token = login(client)
    assert post(client, f"/x/api/candidates/{DATE}/approve/{FOLLOW_ID}", token, json={"body": "Edited"}).status_code == 200
    assert post(client, f"/x/api/candidates/{DATE}/skip/{POST_ID}", token, json={}).status_code == 200
    assert post(client, f"/x/api/candidates/{DATE}/update-body/{REPLY_ID}", token, json={"body": "Revised"}).status_code == 200
    assert post(client, "/projects/api/projects/demo/lane", token, json={"lane": "active"}).status_code == 200
    candidates = queue.load(DATE)["candidates"]
    assert candidates[0]["status"] == "approved"
    assert candidates[0]["body"] == "Edited"
    assert candidates[1]["status"] == "skipped"
    assert candidates[2]["body"] == "Revised"
    assert board.load()["projects"][0]["lane"] == "active"


def test_json_shape_limits_and_logout(secured):
    app, _, _ = secured
    client = app.test_client()
    token = login(client)
    path = f"/x/api/candidates/{DATE}/approve/{FOLLOW_ID}"
    assert post(client, path, token, data={}).status_code == 415
    assert post(client, path, token, json=[]).status_code == 400
    assert post(client, path, token, data="{", content_type="application/json").status_code == 400
    assert post(client, path, token, json={"body": "a" * 65536}).status_code == 413
    assert client.get("/auth/logout", base_url=ORIGIN).status_code == 405
    assert post(client, "/auth/logout").status_code == 400
    assert post(client, "/auth/logout", token).status_code == 302
    assert client.get(f"/x/api/candidates/{DATE}", base_url=ORIGIN).status_code == 401


def test_cookie_flags_expiration_and_cross_worker_sessions(secured):
    app, _, _ = secured
    client = app.test_client()
    login(client)
    cookie = client.get_cookie("__Host-life_ops", domain="ops.example.test")
    assert cookie.secure and cookie.http_only and cookie.same_site == "Strict" and cookie.path == "/"
    # A new worker with the same configuration accepts the established session.
    worker_client = create_app().test_client()
    worker_client.set_cookie("__Host-life_ops", cookie.value, domain="ops.example.test")
    assert worker_client.get(f"/x/api/candidates/{DATE}", base_url=ORIGIN).status_code == 200
    with client.session_transaction(base_url=ORIGIN) as state:
        state["authenticated_at"] = time.time() - SESSION_SECONDS - 1
    assert client.get(f"/x/api/candidates/{DATE}", base_url=ORIGIN).status_code == 401
    with patch.dict("os.environ", {"LIFE_OPS_OWNER_KEY_SHA256": hashlib.sha256(b"new-key").hexdigest()}):
        rotated_client = create_app().test_client()
        rotated_client.set_cookie("__Host-life_ops", cookie.value, domain="ops.example.test")
        assert rotated_client.get(f"/x/api/candidates/{DATE}", base_url=ORIGIN).status_code == 401
    with patch.dict("os.environ", {"LIFE_OPS_SESSION_SECRET": "C" * 64}):
        rotated_client = create_app().test_client()
        rotated_client.set_cookie("__Host-life_ops", cookie.value, domain="ops.example.test")
        assert rotated_client.get(f"/x/api/candidates/{DATE}", base_url=ORIGIN).status_code == 401


def test_transport_hostname_and_spoofed_proxy_headers(secured):
    app, _, _ = secured
    client = app.test_client()
    login(client)
    assert client.get("/auth/login", base_url="https://alternate.example").status_code == 403
    assert client.get("/auth/login", base_url="http://ops.example.test").status_code == 403
    assert client.get("/auth/login", base_url="http://ops.example.test", headers={"X-Forwarded-Proto": "https"}).status_code == 403
    with patch.dict("os.environ", {"LIFE_OPS_PROXY_HOPS": "1"}):
        proxy = create_app().test_client()
        assert proxy.get("/auth/login", base_url="http://ops.example.test", headers={"X-Forwarded-Proto": "https"}).status_code == 200
        assert proxy.get(f"/x/api/candidates/{DATE}", base_url="http://ops.example.test",
                         headers={"X-Forwarded-Proto": "https", "X-Forwarded-User": "owner"}).status_code == 401
        assert proxy.get("/auth/login", base_url="http://alternate.example",
                         headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "ops.example.test"}).status_code == 403


def test_local_demo_is_loopback_only_and_still_uses_csrf(secured):
    _, queue, _ = secured
    client = create_app(local_only=True).test_client()
    assert client.get(f"/x/?date={DATE}").status_code == 200
    assert client.get("/x/", environ_overrides={"REMOTE_ADDR": "192.0.2.1"}, headers={"X-Forwarded-For": "127.0.0.1"}).status_code == 403
    assert client.get("/x/", base_url="http://untrusted.example").status_code == 403
    path = f"/x/api/candidates/{DATE}/approve/{FOLLOW_ID}"
    assert client.post(path, json={}).status_code == 400
    assert client.post(path, data={}, headers={"Origin": "https://untrusted.example"}).status_code == 403
    token = csrf_from(client.get(f"/x/?date={DATE}"))
    assert client.post(path, json={}, headers={"X-CSRFToken": token}).status_code == 200
    assert queue.load(DATE)["candidates"][0]["status"] == "approved"


def test_sensitive_responses_are_not_cached_or_embeddable(secured):
    app, _, _ = secured
    response = app.test_client().get("/auth/login", base_url=ORIGIN)
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    policy = response.headers["Content-Security-Policy"]
    assert "script-src 'self';" in policy
    assert "script-src-attr 'none';" in policy
    assert "object-src 'none'" in policy


def test_private_theme_requires_login_and_only_serves_fixed_file(secured, tmp_path):
    app, _, _ = secured
    app.instance_path = str(tmp_path)
    css = ":root { --accent: #24634b; }"
    (tmp_path / "theme.css").write_text(css)
    (tmp_path / "private.txt").write_text("fictional private record")
    client = app.test_client()
    assert client.get("/theme.css", base_url=ORIGIN).status_code == 302
    login(client)
    response = client.get("/theme.css", base_url=ORIGIN)
    assert response.get_data(as_text=True) == css
    assert response.mimetype == "text/css"
    assert response.headers["Cache-Control"] == "no-store"
    assert "/theme.css" in client.get("/", base_url=ORIGIN).get_data(as_text=True)
    assert client.get("/theme.css/../private.txt", base_url=ORIGIN).status_code == 404


def test_expired_csrf_and_tampered_session_are_rejected(secured):
    app, queue, _ = secured
    client = app.test_client()
    token = login(client)
    path = f"/x/api/candidates/{DATE}/approve/{FOLLOW_ID}"
    with patch("time.time", return_value=time.time() + 3601):
        assert post(client, path, token, json={}).status_code == 400
    assert queue.load(DATE)["candidates"][0]["status"] == "pending"
    cookie = client.get_cookie("__Host-life_ops", domain="ops.example.test")
    client.set_cookie("__Host-life_ops", "tampered." + cookie.value, domain="ops.example.test")
    assert client.get(f"/x/api/candidates/{DATE}", base_url=ORIGIN).status_code == 401


def test_generator_keeps_keys_private_and_refuses_overwrite(tmp_path, capsys):
    output = tmp_path / "auth"
    assert setup_auth_main(["--origin", ORIGIN, "--output-dir", str(output)]) == 0
    key = (output / "owner-access-key.txt").read_text().strip()
    settings = (output / "server.env").read_text()
    assert len(key) == 43 and key not in settings
    assert hashlib.sha256(key.encode()).hexdigest() in settings
    assert output.stat().st_mode & 0o777 == 0o700
    for child in output.iterdir():
        assert child.stat().st_mode & 0o777 == 0o600
    assert key not in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        generate_auth(ORIGIN, output)
    assert (output / "owner-access-key.txt").read_text().strip() == key
