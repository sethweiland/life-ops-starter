"""Offline setup checks. Never contacts providers or prints configuration values."""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
from pathlib import Path
import sys
from typing import Mapping
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEPENDENCIES = ("flask", "flask_wtf", "dotenv", "yaml", "boto3", "dateutil")
PRIVATE_CONFIG_KEYS = {"api_key", "token", "password", "secret", "access_key",
                       "aws_access_key_id", "aws_secret_access_key", "calendar_ics_url"}


def contains_credentials(value) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in PRIVATE_CONFIG_KEYS or contains_credentials(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(contains_credentials(item) for item in value)
    return False


def check_config(config, environ: Mapping[str, str]) -> list[tuple[str, str]]:
    """Return fixed messages only; input values never appear in the result."""
    results = []
    if not isinstance(config, dict):
        return [("FAIL", "Configuration must be a YAML mapping. See docs/onboarding/start-here.md.")]
    if contains_credentials(config):
        results.append(("FAIL", "Credential-like fields found in tenant config. Move them to your secret store."))
    human = config.get("human") or {}
    if not isinstance(human, dict):
        results.append(("FAIL", "human must be a mapping with a timezone."))
    else:
        try:
            ZoneInfo(str(human.get("timezone") or "America/New_York"))
            results.append(("PASS", "Timezone is valid."))
        except (ZoneInfoNotFoundError, ValueError):
            results.append(("FAIL", "Timezone is not recognized. Use an IANA timezone such as Europe/London."))
    secrets = config.get("secrets") or {}
    backend = secrets.get("backend", "env") if isinstance(secrets, dict) else None
    if backend != "env":
        results.append(("FAIL", "Only secrets.backend: env is implemented. See docs/onboarding/secrets.md."))
    else:
        results.append(("PASS", "Supported environment secret backend selected."))
    modules = config.get("modules") or {}
    if not isinstance(modules, dict) or any(not isinstance(v, bool) for v in modules.values()):
        results.append(("FAIL", "Module settings must be YAML true/false values."))
    else:
        results.append(("PASS", "Module flags are valid."))
    if isinstance(modules, dict) and modules.get("weather") is True:
        from src.core.weather import weather_settings

        try:
            weather_settings(environ)
            results.append(("CHECK", "Weather is configured but unverified. It sends approximate coordinates to Open-Meteo; verify the location and forecast on Home."))
        except ValueError as error:
            results.append(("FAIL", str(error)))
    bucket = environ.get("OPS_BUCKET") or environ.get("MEME_ASSETS_BUCKET")
    manager = environ.get("APP_SECRET_ARN")
    if manager:
        results.append(("CHECK", "AWS secret lookup is configured but unverified; only settings using the AWS helper will read it."))
    if bucket:
        results.append(("CHECK", "Cloud storage is configured. Verify identity, permissions and a read/write round trip separately."))
    elif not manager:
        results.append(("PASS", "Local storage selected; cloud accounts are optional."))
    else:
        results.append(("CHECK", "Storage selection depends on the remote secret, which this offline check does not read."))
    access = bool(environ.get("AWS_ACCESS_KEY_ID"))
    secret = bool(environ.get("AWS_SECRET_ACCESS_KEY"))
    if access != secret:
        results.append(("FAIL", "AWS environment credentials are incomplete. Supply a matching pair or use a profile/role."))
    if environ.get("AWS_SESSION_TOKEN") and not (access and secret):
        results.append(("FAIL", "AWS session token requires its matching access-key pair."))
    if environ.get("CALENDAR_ICS_URL"):
        try:
            parsed = urlparse(environ["CALENDAR_ICS_URL"])
            valid = parsed.scheme in {"http", "https"} and bool(parsed.hostname)
        except ValueError:
            valid = False
        results.append(("CHECK" if valid else "FAIL",
                        "Calendar feed is configured; verify one known event in Home." if valid
                        else "Calendar feed must be a valid HTTP(S) URL. Its value is not displayed."))
    else:
        results.append(("PASS", "Calendar snapshot/empty mode selected; no calendar account required."))
    results.append(("CHECK", "Hosted authentication, backups and provider connectivity are not verified offline."))
    costs = environ.get("LIFE_OPS_AWS_COSTS", "false").lower()
    if costs not in {"true", "false"}:
        results.append(("FAIL", "LIFE_OPS_AWS_COSTS must be true or false."))
    elif costs == "true":
        results.append(("CHECK", "AWS cost reads are enabled. Verify identity, billing scope, permissions and API charges separately."))
    providers = [value.strip() for value in environ.get("LIFE_OPS_USAGE_PROVIDERS", "xai").split(",") if value.strip()]
    if len(providers) > 8 or any(not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", value) for value in providers):
        results.append(("FAIL", "Usage providers must be up to eight simple lowercase provider IDs."))
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Local tenant YAML to inspect; no S3 lookup occurs")
    parser.add_argument("--env-file", type=Path, help="Explicit private .env file; values are never printed")
    parser.add_argument("--hosted", action="store_true", help="Also validate required hosted login settings offline")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        print("FAIL: Python 3.11 or newer is required.")
        return 1
    if any(importlib.util.find_spec(name) is None for name in DEPENDENCIES):
        print("FAIL: Dependencies are missing. Activate your environment and run pip install -r requirements.txt.")
        return 1
    import yaml
    from dotenv import dotenv_values

    environ = {}
    if args.env_file:
        try:
            # Disabling interpolation also avoids resolving unexpected local values.
            with args.env_file.open(encoding="utf-8") as stream:
                environ.update({key: value for key, value in dotenv_values(stream=stream, interpolate=False).items()
                                if value is not None})
        except (OSError, UnicodeError):
            print("FAIL: Cannot read the supplied environment file. Check it locally.")
            return 1
    environ.update(os.environ)
    config_path = args.config or Path(environ.get("TENANT_CONFIG") or ROOT / "config/tenant.yaml")
    using_example = not args.config and not environ.get("TENANT_CONFIG") and not config_path.exists()
    if using_example:
        config_path = ROOT / "config/tenant.example.yaml"
        print("CHECK: Using example configuration. Copy it to config/tenant.yaml to personalize the app.")
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        print("FAIL: Configuration cannot be read or parsed. Check the YAML locally; contents are not displayed.")
        return 1
    results = check_config(config, environ)
    if args.hosted:
        from src.core.auth_config import hosted_auth_settings

        try:
            hosted_auth_settings(environ)
            results.append(("PASS", "Hosted login settings are structurally valid. Verify HTTPS, sign-in and signed-out denial on the deployed host."))
        except ValueError as error:
            results.append(("FAIL", str(error)))
    for status, message in results:
        print(f"{status}: {message}")
    print("Offline check only: PASS does not establish that an account is connected.")
    return int(any(status == "FAIL" for status, _ in results))


if __name__ == "__main__":
    raise SystemExit(main())
