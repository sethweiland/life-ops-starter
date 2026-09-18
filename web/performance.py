"""Version shared assets for browser caching; never cache private pages."""

from hashlib import sha256
from pathlib import Path

from flask import request


def register_performance(app):
    root = Path(app.static_folder)
    versions = {
        str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()[:16]
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink() and path.suffix in {".css", ".js"}
    }

    @app.url_defaults
    def version_static(endpoint, values):
        if endpoint == "static" and values.get("filename") in versions:
            values.setdefault("v", versions[values["filename"]])

    @app.after_request
    def cache_assets(response):
        if request.endpoint == "static":
            filename = (request.view_args or {}).get("filename")
            version = versions.get(filename)
            if version and request.args.get("v") == version and response.status_code in {200, 304}:
                # Browser-only caching also keeps Cloudflare Access in the request path.
                response.headers["Cache-Control"] = "private, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-store"
        return response
