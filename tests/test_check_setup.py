"""Onboarding diagnostics stay offline and never echo credentials/config values."""

from unittest.mock import patch

from scripts.check_setup import check_config, main


def test_supported_local_configuration_needs_no_cloud_credentials():
    checks = check_config({"human": {"timezone": "Europe/London"},
                           "secrets": {"backend": "env"}, "modules": {"projects": True}}, {})
    assert not any(status == "FAIL" for status, _ in checks)
    assert any("Local storage selected" in message for _, message in checks)


def test_values_are_redacted_even_when_configuration_is_invalid():
    marker = "PRIVATE_VALUE_MUST_NOT_APPEAR"
    checks = check_config({"human": {"timezone": marker}, "secrets": {"backend": marker},
                           "api_key": marker, "modules": {"projects": marker}},
                          {"CALENDAR_ICS_URL": marker, "AWS_ACCESS_KEY_ID": marker,
                           "APP_SECRET_ARN": marker})
    assert marker not in repr(checks)
    assert sum(status == "FAIL" for status, _ in checks) >= 5
    assert any("unverified" in message for _, message in checks)


def test_remote_secret_is_never_mistaken_for_verified_local_storage():
    checks = check_config({}, {"APP_SECRET_ARN": "private-secret-reference"})
    assert not any("Local storage selected" in message for _, message in checks)
    assert any("depends on the remote secret" in message for _, message in checks)


def test_cli_does_not_contact_providers_or_print_environment_values(tmp_path, capsys):
    config = tmp_path / "tenant.yaml"
    config.write_text("human:\n  timezone: UTC\nsecrets:\n  backend: env\n")
    env = tmp_path / ".env"
    env.write_text("APP_SECRET_ARN=PRIVATE_SECRET_REFERENCE\nOPS_BUCKET=PRIVATE_BUCKET\n")
    with patch.dict("os.environ", {}, clear=True), \
            patch("boto3.client", side_effect=AssertionError("Network not permitted")), \
            patch("socket.create_connection", side_effect=AssertionError("Network not permitted")):
        assert main(["--config", str(config), "--env-file", str(env)]) == 0
    output = capsys.readouterr()
    assert "PRIVATE_" not in output.out + output.err
    assert "unverified" in output.out


def test_yaml_error_does_not_echo_input(tmp_path, capsys):
    config = tmp_path / "tenant.yaml"
    config.write_text("api_key: [PRIVATE_VALUE_MUST_NOT_APPEAR\n")
    assert main(["--config", str(config)]) == 1
    output = capsys.readouterr()
    assert "PRIVATE_VALUE" not in output.out + output.err


def test_unimplemented_adapter_is_an_actionable_failure():
    checks = check_config({"secrets": {"backend": "aws"}}, {})
    assert any(status == "FAIL" and "Only secrets.backend: env" in message
               for status, message in checks)


def test_hosted_check_requires_valid_auth_and_redacts_bad_settings(tmp_path, capsys):
    from scripts.setup_auth import generate_auth

    config = tmp_path / "tenant.yaml"
    config.write_text("human:\n  timezone: UTC\n")
    with patch.dict("os.environ", {}, clear=True):
        assert main(["--config", str(config), "--hosted"]) == 1
    capsys.readouterr()
    output = tmp_path / "auth"
    generate_auth("https://ops.example.test", output)
    env_file = output / "server.env"
    with patch.dict("os.environ", {}, clear=True):
        assert main(["--config", str(config), "--hosted", "--env-file", str(env_file)]) == 0
    values = dict(line.split("=", 1) for line in env_file.read_text().splitlines())
    messages = capsys.readouterr().out
    assert values["LIFE_OPS_SESSION_SECRET"] not in messages
    assert values["LIFE_OPS_OWNER_KEY_SHA256"] not in messages
    with patch.dict("os.environ", {"LIFE_OPS_ORIGIN": "https://PRIVATE_VALUE@ops.example.test"}, clear=True):
        assert main(["--config", str(config), "--hosted"]) == 1
    assert "PRIVATE_VALUE" not in capsys.readouterr().out
