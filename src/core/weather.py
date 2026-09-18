"""Opt-in, cached weather for getting dressed; no location discovery or tracking."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import http.client
import json
import math
import os
from threading import Lock
import time
from urllib.parse import urlencode
from zoneinfo import ZoneInfo


HOURS = 8
CACHE_SECONDS = 20 * 60
ERROR_CACHE_SECONDS = 60
MAX_BYTES = 256 * 1024
FIELDS = ("apparent_temperature", "precipitation_probability", "precipitation",
          "weather_code", "wind_gusts_10m")
UNITS = {"time": "unixtime", "apparent_temperature": "°C",
         "precipitation_probability": "%", "precipitation": "mm",
         "weather_code": "wmo code", "wind_gusts_10m": "km/h"}
SNOW = {71, 73, 75, 77, 85, 86}
ICE = {56, 57, 66, 67}
STORM = {95, 96, 99}
RAIN = {51, 53, 55, 61, 63, 65, 80, 81, 82}
WMO_CODES = {0, 1, 2, 3, 45, 48} | SNOW | ICE | STORM | RAIN


@dataclass(frozen=True)
class WeatherSettings:
    latitude: float
    longitude: float
    units: str
    label: str


def _number(value, minimum, maximum):
    if isinstance(value, bool) or value is None:
        raise ValueError("Invalid weather value")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError("Invalid weather value")
    return number


def weather_settings(environ=None):
    env = os.environ if environ is None else environ
    try:
        lat = _number(env.get("LIFE_OPS_WEATHER_LATITUDE"), -90, 90)
        lon = _number(env.get("LIFE_OPS_WEATHER_LONGITUDE"), -180, 180)
        units = env.get("LIFE_OPS_WEATHER_UNITS", "fahrenheit").strip().lower()
        if units not in {"fahrenheit", "celsius"}:
            raise ValueError("Invalid units")
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Set valid weather coordinates and units privately; see docs/onboarding/weather.md.") from None
    # City-level configuration is sufficient; never forward full GPS precision.
    return WeatherSettings(round(lat, 2), round(lon, 2), units,
                           env.get("LIFE_OPS_WEATHER_LABEL", "Your area").strip()[:60] or "Your area")


def _fetch_forecast(settings):
    query = urlencode({
        "latitude": settings.latitude, "longitude": settings.longitude,
        "hourly": ",".join(FIELDS), "forecast_hours": 48,
        "timeformat": "unixtime", "timezone": "GMT",
        "temperature_unit": "celsius", "wind_speed_unit": "kmh", "precipitation_unit": "mm",
    })
    # Fixed HTTPS host/path, no redirects, no user-supplied URL or credentials.
    connection = http.client.HTTPSConnection("api.open-meteo.com", timeout=4)
    try:
        connection.request("GET", "/v1/forecast?" + query,
                           headers={"Accept": "application/json", "User-Agent": "LifeOps-Weather/1"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Forecast unavailable")
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("Forecast too large")
        return json.loads(body)
    finally:
        connection.close()


def normalize_forecast(payload):
    """Reject missing/partial data; unknown weather must never imply dry weather."""
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError("Invalid forecast")
    units = payload.get("hourly_units")
    hourly = payload.get("hourly")
    if not isinstance(units, dict) or any(units.get(k) != v for k, v in UNITS.items()):
        raise ValueError("Unexpected forecast units")
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
        raise ValueError("Missing forecast hours")
    times = hourly["time"]
    if not 1 <= len(times) <= 48:
        raise ValueError("Invalid forecast length")
    if any(not isinstance(hourly.get(field), list) or len(hourly[field]) != len(times) for field in FIELDS):
        raise ValueError("Incomplete forecast")
    rows = []
    for i, stamp in enumerate(times):
        row = {
            "time": _number(stamp, 0, 4102444800),
            "feels_c": _number(hourly["apparent_temperature"][i], -100, 80),
            "probability": _number(hourly["precipitation_probability"][i], 0, 100),
            "precip_mm": _number(hourly["precipitation"][i], 0, 1000),
            "code": _number(hourly["weather_code"][i], 0, 99),
            "gust_kmh": _number(hourly["wind_gusts_10m"][i], 0, 500),
        }
        if row["code"] not in WMO_CODES or (rows and row["time"] - rows[-1]["time"] != 3600):
            raise ValueError("Invalid forecast timeline or condition")
        rows.append(row)
    return rows


def _time_label(stamp, zone):
    return datetime.fromtimestamp(stamp, zone).strftime("%a %I:%M %p %Z").replace(" 0", " ")


def _temperature(value, settings):
    return round(value * 9 / 5 + 32 if settings.units == "fahrenheit" else value)


def _clothing_cue(low):
    if low < 5:
        title, detail = "Wear a warm coat", "Add warm layers for the coldest part of this window."
    elif low < 13:
        title, detail = "Bring a jacket", "Dress for the feels-like temperature, especially early or late in the day."
    elif low < 19:
        title, detail = "Bring a light layer", "A removable layer should help through the cooler hours."
    else:
        title, detail = "Choose light, breathable clothing", "The forecast stays mild to warm through this window."
    return {"title": title, "detail": detail}


def _evening_outlook(by_time, settings, zone, now):
    """Remaining hourly points in the local 6–10 PM window; never past evenings."""
    local_now = now.astimezone(zone)
    start = local_now.replace(hour=18, minute=0, second=0, microsecond=0)
    end = start.replace(hour=22)
    tomorrow = local_now >= end
    if tomorrow:
        start += timedelta(days=1)
        end = start.replace(hour=22)
    first = max(math.ceil(start.timestamp() / 3600), math.floor(now.timestamp() / 3600))
    last = math.floor(end.timestamp() / 3600)
    expected = [hour * 3600 for hour in range(first, last + 1)]
    result = {"label": "Tomorrow evening" if tomorrow else "This evening", "available": False}
    if not expected or any(stamp not in by_time for stamp in expected):
        return result
    low = min(by_time[stamp]["feels_c"] for stamp in expected)
    high = max(by_time[stamp]["feels_c"] for stamp in expected)

    def clock(stamp):
        return datetime.fromtimestamp(stamp, zone).strftime("%I:%M %p").lstrip("0").replace(":00", "")

    begins = "Now" if expected[0] <= now.timestamp() else clock(expected[0])
    return result | {
        "available": True,
        "period": f"{begins}–{clock(expected[-1])} {end.tzname()}",
        "feels_low": _temperature(low, settings), "feels_high": _temperature(high, settings),
        "clothing": _clothing_cue(low)["title"],
    }


def summarize_forecast(rows, settings, zone_name, now):
    stamp = now.timestamp()
    start = math.floor(stamp / 3600) * 3600
    by_time = {row["time"]: row for row in rows}
    # Include the current hourly point plus eight future points. Accumulated
    # precipitation/gusts at each point describe its preceding hour.
    expected = [start + i * 3600 for i in range(HOURS + 1)]
    if any(t not in by_time for t in expected):
        raise ValueError("Forecast does not cover the upcoming hours")
    points = [by_time[t] for t in expected]
    future = points[1:]
    zone = ZoneInfo(zone_name)
    low, high = min(p["feels_c"] for p in points), max(p["feels_c"] for p in points)
    codes = {p["code"] for p in points}
    gust = max(p["gust_kmh"] for p in future)
    probability = max(p["probability"] for p in future)
    wet = [p for p in future if p["probability"] >= 40 or p["precip_mm"] >= 0.2 or p["code"] in RAIN | ICE | SNOW | STORM]
    wet_now = points[0]["code"] in RAIN | ICE | SNOW | STORM
    cues = []
    if codes & STORM:
        cues.append({"title": "Thunderstorms possible", "detail": "Check local alerts and plan indoor shelter; an umbrella is not storm protection."})
    elif codes & ICE:
        cues.append({"title": "Freezing rain possible", "detail": "Wear warm waterproof layers and shoes with grip; check conditions before leaving."})
    elif codes & SNOW:
        cues.append({"title": "Snow possible", "detail": "Bring warm waterproof layers and shoes with grip."})
    elif (wet or wet_now) and gust >= 40:
        cues.append({"title": "Choose a hooded rain jacket", "detail": "Wet weather and gusts may make an umbrella awkward."})
    elif wet or wet_now:
        cues.append({"title": "Bring an umbrella", "detail": "Pack a waterproof layer for possible rain."})
    else:
        cues.append({"title": "Low rain risk in this forecast", "detail": "No umbrella cue for this window; conditions can change."})

    cues.append(_clothing_cue(low))
    if high >= 28:
        cues.append({"title": "Plan for warm hours", "detail": "Keep layers removable and bring water if you will be outside."})
    elif high - low >= 8:
        cues.append({"title": "Expect a temperature swing", "detail": "Use layers you can take off as the day changes."})
    if gust >= 40 and not (wet or wet_now):
        cues.append({"title": "Bring a wind-resistant layer", "detail": "The forecast includes gusty conditions."})

    return {
        "status": "ready", "label": settings.label, "cues": cues,
        "window_end": _time_label(start + HOURS * 3600, zone),
        "feels_low": _temperature(low, settings), "feels_high": _temperature(high, settings),
        "evening": _evening_outlook(by_time, settings, zone, now),
        "temperature_unit": "°F" if settings.units == "fahrenheit" else "°C",
        "peak_probability": round(probability),
        "gust": round(gust / 1.609344 if settings.units == "fahrenheit" else gust),
        "wind_unit": "mph" if settings.units == "fahrenheit" else "km/h",
        "wet_window": (f"{_time_label(stamp if wet_now else max(stamp, wet[0]['time'] - 3600), zone)} – "
                       f"{_time_label(wet[-1]['time'], zone)}") if wet else ("the current hour" if wet_now else None),
    }


_cache = None
_lock = Lock()


def reset_weather_cache():
    global _cache
    with _lock:
        _cache = None


def get_weather(zone_name, *, environ=None, now=None):
    """Return redacted status or current guidance. Never return expired advice."""
    global _cache
    try:
        settings = weather_settings(environ)
        ZoneInfo(zone_name)
    except (TypeError, ValueError, KeyError):
        return {"status": "setup", "message": "Weather needs a location, valid timezone and units. See docs/onboarding/weather.md."}
    now = now or datetime.now(timezone.utc)
    key = (settings.latitude, settings.longitude)
    with _lock:
        tick = time.monotonic()
        if _cache is None or _cache[0] != key or tick >= _cache[1]:
            try:
                rows = normalize_forecast(_fetch_forecast(settings))
                summarize_forecast(rows, settings, zone_name, now)
                _cache = (key, time.monotonic() + CACHE_SECONDS, rows, now.timestamp())
            except Exception:
                # Do not log provider response bodies, request URLs or coordinates.
                _cache = (key, time.monotonic() + ERROR_CACHE_SECONDS, None, None)
        _, _, rows, fetched_at = _cache
    if rows is not None:
        try:
            result = summarize_forecast(rows, settings, zone_name, now)
            result["updated_label"] = _time_label(fetched_at, ZoneInfo(zone_name))
            return result
        except (TypeError, ValueError, KeyError):
            pass
    return {"status": "unavailable", "message": "Weather is unavailable. Check a local forecast before heading out; clothing guidance will return when the forecast refreshes."}
