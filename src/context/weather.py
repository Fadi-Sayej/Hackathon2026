"""weather.py — current conditions from Open-Meteo (free, no API key).

Ported from src/lib/context/weather.js so the ordering decision can use weather at
pipeline time instead of at render time. Same endpoint, same classification bands,
so the pipeline and the browser cannot describe the same day differently.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date
from typing import Any, Dict, Optional

BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Kafr Qasim — the pilot store. The JS default was 31.95/35.93, which is ~100km
# away near Jerusalem; weather-driven demand for THIS shop was being read off the
# wrong town.
DEFAULT_LAT = 32.114
DEFAULT_LON = 34.976


def classify(temperature_c: Optional[float], precipitation: Optional[float]) -> str:
    """Coarse label the demand rules key on. Bands match weather.js."""
    if temperature_c is None:
        return "unknown"
    if precipitation is not None and precipitation > 0.5:
        return "rainy"
    if temperature_c >= 30:
        return "hot"
    if temperature_c >= 20:
        return "warm"
    if temperature_c >= 10:
        return "mild"
    return "cold"


def get_weather(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    *,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    """Current weather, or a null-filled shape. Never raises."""
    empty = {
        "temperatureC": None, "precipitation": None, "windSpeed": None,
        "weatherCode": None, "label": "unknown", "observedAt": None,
        "lat": lat, "lon": lon, "source": None,
    }
    params = (
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,weather_code,precipitation,wind_speed_10m"
        "&timezone=auto"
    )
    try:
        req = urllib.request.Request(BASE_URL + params, headers={"User-Agent": "smartshelf/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            current = (json.loads(response.read()) or {}).get("current") or {}
    except (urllib.error.URLError, OSError, ValueError):
        return empty

    temp = current.get("temperature_2m")
    precip = current.get("precipitation")
    return {
        "temperatureC": temp,
        "precipitation": precip,
        "windSpeed": current.get("wind_speed_10m"),
        "weatherCode": current.get("weather_code"),
        "label": classify(temp, precip),
        "observedAt": current.get("time"),
        "lat": lat, "lon": lon,
        "source": "open-meteo",
    }
