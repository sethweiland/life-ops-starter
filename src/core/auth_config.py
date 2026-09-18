"""Validate hosted authentication settings without reading files or providers."""

from dataclasses import dataclass
import re
from typing import Mapping
from urllib.parse import urlsplit


@dataclass(frozen=True)
class AuthSettings:
    origin: str
    host: str
    key_hash: str
    session_secret: str
    proxy_hops: int


def normalize_origin(value: str) -> str:
    """One exact HTTPS origin; no credentials, paths, wildcards or redirects."""
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == "https" and parsed.hostname
                 and parsed.path in {"", "/"} and not parsed.query
                 and not parsed.fragment and not parsed.username and not parsed.password
                 and not any(c.isspace() for c in value)
                 and re.fullmatch(r"[a-zA-Z0-9.-]+", parsed.hostname)
                 and not parsed.hostname.startswith(".")
                 and ".." not in parsed.hostname and parsed.port != 0)
        if valid:
            port = parsed.port
            return "https://" + parsed.hostname.lower() + (f":{port}" if port and port != 443 else "")
    except ValueError:
        pass
    raise ValueError("LIFE_OPS_ORIGIN must be one HTTPS origin without a path or credentials.")


def hosted_auth_settings(environ: Mapping[str, str]) -> AuthSettings:
    origin = normalize_origin(environ.get("LIFE_OPS_ORIGIN", ""))
    key_hash = environ.get("LIFE_OPS_OWNER_KEY_SHA256", "")
    secret = environ.get("LIFE_OPS_SESSION_SECRET", "")
    if not re.fullmatch(r"[0-9a-f]{64}", key_hash):
        raise ValueError("LIFE_OPS_OWNER_KEY_SHA256 is missing or invalid. Run scripts/setup_auth.py.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", secret):
        raise ValueError("LIFE_OPS_SESSION_SECRET is missing or invalid. Run scripts/setup_auth.py.")
    hops = environ.get("LIFE_OPS_PROXY_HOPS", "0")
    if hops not in {"0", "1"}:
        raise ValueError("LIFE_OPS_PROXY_HOPS must be 0, or 1 behind one trusted TLS proxy.")
    return AuthSettings(origin, urlsplit(origin).netloc, key_hash, secret, int(hops))
