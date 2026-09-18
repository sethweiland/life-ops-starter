"""Fictional forecasts only: never discover a location or contact a provider."""

from datetime import datetime, timezone
import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.check_setup import check_config
from src.core.tenant import normalize_tenant, reset_tenant
from src.core.weather import (
    CACHE_SECONDS, MAX_BYTES, UNITS, _fetch_forecast, get_weather,
    normalize_forecast, reset_weather_cache, summarize_forecast, weather_settings,
)
from web import create_app


NOW = datetime(2026, 9, 16, 12, 30, tzinfo=timezone.utc)
ENV = {"LIFE_OPS_WEATHER_LATITUDE": "0", "LIFE_OPS_WEATHER_LONGITUDE": "0",
       "LIFE_OPS_WEATHER_LABEL": "Example town", "LIFE_OPS_WEATHER_UNITS": "fahrenheit"}


def forecast(*, feels=16, probability=0, amount=0, code=0, gust=10):
    start = int(NOW.replace(minute=0).timestamp())
    return {"hourly_units": dict(UNITS), "hourly": {
        "time": [start + i * 3600 for i in range(24)],
        "apparent_temperature": [feels] * 24,
        "precipitation_probability": [probability] * 24,
        "precipitation": [amount] * 24,
        "weather_code": [code] * 24,
        "wind_gusts_10m": [gust] * 24,
    }}


def summary(data, units="fahrenheit", zone="UTC", now=NOW):
    return summarize_forecast(normalize_forecast(data), weather_settings({**ENV, "LIFE_OPS_WEATHER_UNITS": units}), zone, now)


def titles(result):
    return [cue["title"] for cue in result["cues"]]


@pytest.fixture(autouse=True)
def isolate_weather():
    reset_weather_cache()
    with patch("src.core.weather._fetch_forecast", side_effect=AssertionError("Network forbidden")):
        yield
    reset_weather_cache()


def test_umbrella_is_based_on_upcoming_hours_with_realistic_rain_timing():
    data = forecast(feels=10)
    data["hourly"]["precipitation_probability"][3:5] = [65, 80]
    result = summary(data, zone="America/New_York")
    assert titles(result) == ["Bring an umbrella", "Bring a jacket"]
    assert result["wet_window"] == "Wed 10:00 AM EDT – Wed 12:00 PM EDT"
    assert result["peak_probability"] == 80
    assert result["feels_low"] == 50


def test_rain_in_past_accumulation_or_after_window_does_not_trigger_umbrella():
    data = forecast()
    data["hourly"]["precipitation"][0] = 3
    data["hourly"]["precipitation_probability"][10] = 100
    assert titles(summary(data))[0] == "Low rain risk in this forecast"
    data["hourly"]["weather_code"][0] = 61
    assert titles(summary(data))[0] == "Bring an umbrella"


@pytest.mark.parametrize("settings,expected", [
    ({"amount": 0.5}, "Bring an umbrella"),
    ({"probability": 40, "gust": 45}, "Choose a hooded rain jacket"),
    ({"code": 73, "probability": 90, "feels": -2}, "Snow possible"),
    ({"code": 66, "probability": 90}, "Freezing rain possible"),
    ({"code": 95, "probability": 90}, "Thunderstorms possible"),
])
def test_rain_snow_ice_and_storms_get_distinct_advice(settings, expected):
    result = summary(forecast(**settings))
    assert titles(result)[0] == expected
    if settings.get("code") in {73, 66, 95}:
        assert "Bring an umbrella" not in titles(result)


@pytest.mark.parametrize("feels,expected", [(-3, "Wear a warm coat"), (8, "Bring a jacket"),
                                            (16, "Bring a light layer"), (24, "Choose light, breathable clothing")])
def test_clothing_uses_feels_like_temperature(feels, expected):
    assert expected in titles(summary(forecast(feels=feels)))


def test_units_temperature_swings_and_gusts():
    data = forecast(feels=10, gust=48)
    data["hourly"]["apparent_temperature"][6] = 22
    result = summary(data, units="celsius")
    assert (result["feels_low"], result["feels_high"], result["temperature_unit"]) == (10, 22, "°C")
    assert result["gust"] == 48 and result["wind_unit"] == "km/h"
    assert "Expect a temperature swing" in titles(result)
    assert "Bring a wind-resistant layer" in titles(result)
    assert "Plan for warm hours" in titles(summary(forecast(feels=30)))


def test_midnight_and_dst_use_aware_local_labels():
    data = forecast()
    offset = int(datetime(2026, 11, 1, 4, tzinfo=timezone.utc).timestamp()) - data["hourly"]["time"][0]
    data["hourly"]["time"] = [stamp + offset for stamp in data["hourly"]["time"]]
    now = datetime(2026, 11, 1, 4, 30, tzinfo=timezone.utc)
    result = summary(data, zone="America/New_York", now=now)
    assert result["window_end"] == "Sun 7:00 AM EST"


@pytest.mark.parametrize("field,bad", [("precipitation_probability", None), ("apparent_temperature", float('nan')),
                                       ("precipitation", -1), ("weather_code", 12), ("time", True)])
def test_missing_or_invalid_values_are_not_treated_as_fine_weather(field, bad):
    data = forecast()
    data["hourly"][field][2] = bad
    with pytest.raises(ValueError):
        summary(data)


def test_partial_wrong_units_and_old_forecasts_are_rejected():
    wrong_units = forecast()
    wrong_units["hourly_units"]["apparent_temperature"] = "°F"
    partial = forecast()
    partial["hourly"]["precipitation_probability"].pop()
    old = forecast()
    old["hourly"]["time"] = [stamp - 86400 for stamp in old["hourly"]["time"]]
    for data in [wrong_units, partial, old]:
        with pytest.raises(ValueError):
            summary(data)


def test_success_cache_failure_backoff_and_no_expired_advice():
    with patch("src.core.weather._fetch_forecast", return_value=forecast(probability=70)) as fetch, \
            patch("src.core.weather.time.monotonic", return_value=0):
        assert get_weather("UTC", environ=ENV, now=NOW)["status"] == "ready"
        assert get_weather("UTC", environ=ENV, now=NOW)["status"] == "ready"
        assert fetch.call_count == 1
    with patch("src.core.weather._fetch_forecast", side_effect=RuntimeError("PRIVATE_URL_AND_COORDINATES")) as fetch, \
            patch("src.core.weather.time.monotonic", return_value=CACHE_SECONDS + 1):
        result = get_weather("UTC", environ=ENV, now=NOW)
        assert result["status"] == "unavailable" and "cues" not in result
        assert "PRIVATE_" not in repr(result)
        get_weather("UTC", environ=ENV, now=NOW)
        assert fetch.call_count == 1


def test_location_changes_do_not_reuse_other_locations_forecast():
    with patch("src.core.weather._fetch_forecast", return_value=forecast()) as fetch:
        get_weather("UTC", environ=ENV, now=NOW)
        get_weather("UTC", environ={**ENV, "LIFE_OPS_WEATHER_LATITUDE": "1"}, now=NOW)
        assert fetch.call_count == 2


def test_configuration_redacts_coordinates_and_requires_explicit_location():
    assert get_weather("UTC", environ={}, now=NOW)["status"] == "setup"
    for value in ["PRIVATE_COORDINATE", "nan", "91", "inf"]:
        env = {**ENV, "LIFE_OPS_WEATHER_LATITUDE": value}
        checks = check_config({"modules": {"weather": True}}, env)
        assert any(status == "FAIL" and "weather" in message for status, message in checks)
        assert value not in repr(checks)
    settings = weather_settings({**ENV, "LIFE_OPS_WEATHER_LATITUDE": "12.1234567"})
    assert settings.latitude == 12.12


@pytest.mark.parametrize("flag", [None, False, "false", "true", 1])
def test_weather_requires_a_literal_boolean_opt_in(flag):
    tenant = normalize_tenant({"modules": {"weather": flag}}, source_path="test")
    assert not tenant.module_enabled("weather")


def test_transport_is_fixed_bounded_and_does_not_follow_redirects():
    # Exercise the transport itself; the autouse patch stops all incidental calls.
    from src.core import weather as module
    original_fetch = _fetch_forecast
    response = MagicMock(status=200)
    response.read.return_value = json.dumps(forecast()).encode()
    connection = MagicMock()
    connection.getresponse.return_value = response
    with patch.object(module.http.client, "HTTPSConnection", return_value=connection) as connect:
        original_fetch(weather_settings(ENV))
        connect.assert_called_once_with("api.open-meteo.com", timeout=4)
        assert connection.request.call_args.args[1].startswith("/v1/forecast?")
        assert "forecast_hours=48" in connection.request.call_args.args[1]
        response.read.assert_called_once_with(MAX_BYTES + 1)
        connection.close.assert_called_once()
        response.status = 302
        with pytest.raises(ValueError):
            original_fetch(weather_settings(ENV))
        response.status = 200
        response.read.return_value = b"x" * (MAX_BYTES + 1)
        with pytest.raises(ValueError):
            original_fetch(weather_settings(ENV))


def test_home_load_is_independent_weather_is_optional_and_endpoint_is_private(tmp_path):
    tenant = {"modules": {"projects": False, "calendar": False, "spend": False, "weather": True}}
    reset_tenant(normalize_tenant(tenant, source_path="test"))
    settings = {**ENV, "LIFE_OPS_ORIGIN": "https://ops.example.test",
                "LIFE_OPS_OWNER_KEY_SHA256": hashlib.sha256(b"test").hexdigest(),
                "LIFE_OPS_SESSION_SECRET": "B" * 64}
    try:
        with patch.dict("os.environ", settings, clear=True), patch("src.core.weather.get_weather") as weather:
            weather.return_value = summary(forecast(probability=70)) | {"updated_label": "Wed 12:30 PM UTC"}
            app = create_app()
            app.instance_path = str(tmp_path)
            assert app.test_client().get("/api/weather", base_url="https://ops.example.test").status_code == 401
            weather.assert_not_called()
            local = create_app(local_only=True).test_client()
            assert "Before you head out" in local.get("/").get_data(as_text=True)
            weather.assert_not_called()
            response = local.get("/api/weather")
            assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
            assert "Bring an umbrella" in response.get_data(as_text=True)
            assert "data-weather-evening" in response.get_data(as_text=True)
            assert "This evening" in response.get_data(as_text=True)
            assert "api.open-meteo.com" not in response.get_data(as_text=True)
            weather.return_value["label"] = '<script>alert("example")</script>'
            html = local.get("/api/weather").get_data(as_text=True)
            assert "<script>" not in html and "&lt;script&gt;" in html
            tenant["modules"]["weather"] = False
            reset_tenant(normalize_tenant(tenant, source_path="test"))
            weather.reset_mock()
            assert "Before you head out" not in local.get("/").get_data(as_text=True)
            assert local.get("/api/weather").status_code == 404
            weather.assert_not_called()
    finally:
        reset_tenant()


def evening_forecast(now=NOW, feels=22):
    data = forecast(feels=feels)
    for field in data["hourly"]:
        data["hourly"][field] *= 2
    start = int(now.replace(minute=0, second=0, microsecond=0).timestamp())
    data["hourly"]["time"] = [start + i * 3600 for i in range(48)]
    return data


def test_morning_view_includes_cool_evening_beyond_eight_hour_window():
    data = evening_forecast()
    data["hourly"]["apparent_temperature"][10:15] = [16, 15, 13, 10, 9]
    result = summary(data, zone="America/New_York")
    assert result["feels_low"] == result["feels_high"] == 72
    evening = result["evening"]
    assert evening == {"available": True, "label": "This evening", "period": "6 PM–10 PM EDT",
                       "feels_low": 48, "feels_high": 61, "clothing": "Bring a jacket"}
    celsius = summary(data, units="celsius", zone="America/New_York")["evening"]
    assert (celsius["feels_low"], celsius["feels_high"]) == (9, 16)


def test_evening_uses_remaining_hours_and_not_earlier_temperatures():
    data = evening_forecast()
    data["hourly"]["apparent_temperature"][10] = -15  # 6 PM has already passed.
    data["hourly"]["apparent_temperature"][13:15] = [12, 10]
    now = datetime(2026, 9, 17, 1, 30, tzinfo=timezone.utc)  # 9:30 PM local.
    evening = summary(data, zone="America/New_York", now=now)["evening"]
    assert evening["period"] == "Now–10 PM EDT"
    assert (evening["feels_low"], evening["feels_high"]) == (50, 54)


def test_late_night_switches_to_tomorrow_evening_then_midnight_to_today():
    data = evening_forecast()
    data["hourly"]["apparent_temperature"][34:39] = [4, 5, 6, 7, 8]
    now = datetime(2026, 9, 17, 2, 0, tzinfo=timezone.utc)  # 10 PM local.
    evening = summary(data, zone="America/New_York", now=now)["evening"]
    assert evening["label"] == "Tomorrow evening" and evening["period"] == "6 PM–10 PM EDT"
    assert evening["feels_low"] == 39 and evening["clothing"] == "Wear a warm coat"
    now = datetime(2026, 9, 17, 4, 30, tzinfo=timezone.utc)
    after_midnight = summary(data, zone="America/New_York", now=now)["evening"]
    assert after_midnight["label"] == "This evening"
    assert after_midnight["feels_low"] == evening["feels_low"]


def test_evening_handles_dst_changes_and_half_hour_timezones():
    now = datetime(2026, 11, 1, 3, 30, tzinfo=timezone.utc)  # Before DST ends overnight.
    evening = summary(evening_forecast(now), zone="America/New_York", now=now)["evening"]
    assert evening["label"] == "Tomorrow evening"
    assert evening["period"] == "6 PM–10 PM EST"
    india = summary(evening_forecast(), zone="Asia/Kolkata")["evening"]
    assert india["label"] == "This evening" and india["period"] == "6:30 PM–9:30 PM IST"


def test_missing_evening_hours_do_not_invent_a_temperature_or_hide_current_forecast():
    data = evening_forecast()
    data["hourly"] = {key: values[:9] for key, values in data["hourly"].items()}
    result = summary(data, zone="America/New_York")
    assert result["status"] == "ready"
    assert result["evening"] == {"label": "This evening", "available": False}
