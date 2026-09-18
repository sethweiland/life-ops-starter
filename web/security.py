"""Single-owner authentication and CSRF protection for the entire application.

The access key is generated from 32 random bytes, not a human-chosen password.
Only its SHA-256 digest is stored on the server. Session cookies contain no key.
"""

from datetime import timedelta
import hashlib
import hmac
import ipaddress
import os
import re
import secrets
import time

from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from src.core.auth_config import hosted_auth_settings
from src.core.urls import safe_url


SESSION_SECONDS = 8 * 60 * 60
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def install_security(app, *, local_only: bool = False) -> None:
    app.jinja_env.filters["safe_url"] = safe_url
    # Validate before any stores or provider clients can be constructed.
    settings = None if local_only else hosted_auth_settings(os.environ)
    app.extensions["life_ops_security"] = {"local_only": local_only}
    app.config.update(
        SECRET_KEY=secrets.token_urlsafe(48) if local_only else settings.session_secret,
        SESSION_COOKIE_NAME="life_ops_local" if local_only else "__Host-life_ops",
        SESSION_COOKIE_SECURE=not local_only,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_PATH="/",
        SESSION_COOKIE_DOMAIN=None,
        SESSION_REFRESH_EACH_REQUEST=False,
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=SESSION_SECONDS),
        MAX_CONTENT_LENGTH=64 * 1024,
        WTF_CSRF_TIME_LIMIT=3600,
    )
    if settings and settings.proxy_hops:
        # Only scheme is forwarded. Host, address and identity headers are never trusted.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=0, x_proto=1, x_host=0, x_port=0, x_prefix=0)

    version = hashlib.sha256(settings.key_hash.encode()).hexdigest() if settings else None

    def authenticated():
        issued = session.get("authenticated_at")
        stamp = session.get("credential_version")
        return (isinstance(issued, (int, float)) and 0 <= time.time() - issued < SESSION_SECONDS
                and isinstance(stamp, str) and hmac.compare_digest(stamp, version))

    @app.before_request
    def authenticate_request():
        g.owner_authenticated = False
        # Liveness contains no records and remains usable by an internal probe.
        if request.path == "/healthz" and request.method in {"GET", "HEAD"}:
            return jsonify(status="ok")
        if local_only:
            try:
                loopback = ipaddress.ip_address(request.remote_addr or "").is_loopback
            except ValueError:
                loopback = False
            # Host checking also rejects DNS-rebinding requests to the local demo.
            if not loopback or request.host.split(":")[0].lower() not in {"localhost", "127.0.0.1"}:
                abort(403)
            g.owner_authenticated = True
        else:
            # No alternate hostname, insecure transport or user-controlled identity bypass.
            if request.host.lower() != settings.host or not request.is_secure:
                abort(403)
            g.owner_authenticated = authenticated()

        if request.method not in SAFE_METHODS:
            expected_origin = request.host_url.rstrip("/") if local_only else settings.origin
            origin = request.headers.get("Origin")
            if (origin is not None and origin != expected_origin
                    or request.headers.get("Sec-Fetch-Site") == "cross-site"):
                return jsonify(error="Cross-site request rejected. Reload this page and try again."), 403

        if request.endpoint in {"auth.login", "static"} or g.owner_authenticated:
            return None
        if "/api/" in request.path or request.method not in SAFE_METHODS:
            return jsonify(error="Sign in to continue."), 401
        return redirect(url_for("auth.login"))

    # Registered after authentication; all state-changing routes, including login,
    # require a session-bound token. No module is exempt.
    CSRFProtect(app)

    @app.before_request
    def validate_api_payload():
        if "/api/" in request.path and request.method not in SAFE_METHODS:
            if not request.is_json:
                return jsonify(error="Send a JSON object."), 415
            if not isinstance(request.get_json(silent=True), dict):
                return jsonify(error="Send a valid JSON object."), 400

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        message = "This page expired or the request could not be verified. Reload and try again."
        if "/api/" in request.path:
            return jsonify(error=message), 400
        return render_template("auth/error.html", message=message), 400

    @app.after_request
    def private_response(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; script-src-attr 'none'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' https:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'self'; object-src 'none'"
        )
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    auth = Blueprint("auth", __name__)

    @auth.route("/auth/login", methods=["GET", "POST"])
    def login():
        if g.owner_authenticated:
            return redirect(url_for("home.index"))
        error = None
        if request.method == "POST":
            key = request.form.get("access_key", "")
            if (re.fullmatch(r"[A-Za-z0-9_-]{43}", key)
                    and hmac.compare_digest(hashlib.sha256(key.encode()).hexdigest(), settings.key_hash)):
                session.clear()  # Discard the anonymous session and its CSRF token.
                session.permanent = True
                session["authenticated_at"] = time.time()
                session["credential_version"] = version
                return redirect(url_for("home.index"))
            error = "That access key was not accepted."
        return render_template("auth/login.html", error=error), 401 if error else 200

    @auth.post("/auth/logout")
    def logout():
        session.clear()
        return redirect(url_for("auth.login"))

    app.register_blueprint(auth)
