"""HK Observatory — current weather + 9-day forecast.

Single endpoint, selected by `dataType`:
    rhrread  → current report (per-station temp, humidity, rainfall, UV, icon)
    flw      → local weather forecast (general situation, today/tomorrow)
    fnd      → 9-day forecast

Source: https://data.weather.gov.hk/weatherAPI/opendata/weather.php
"""

from __future__ import annotations

import httpx

HKO_WEATHER = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"

_HKO_ICONS = {
    50: "sunny", 51: "sunny periods", 52: "sunny intervals",
    53: "sunny periods with a few showers", 54: "sunny intervals with showers",
    60: "cloudy", 61: "overcast", 62: "light rain", 63: "rain", 64: "heavy rain",
    65: "thunderstorms", 70: "fine", 71: "fine", 72: "fine", 73: "fine",
    74: "fine", 75: "fine", 76: "mainly cloudy", 77: "mainly fine",
    80: "windy", 81: "dry", 82: "humid", 83: "fog", 84: "mist", 85: "haze",
    90: "hot", 91: "warm", 92: "cool", 93: "cold",
}


async def _hko_get(data_type: str, lang: str = "en") -> dict:
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(HKO_WEATHER, params={"dataType": data_type, "lang": lang})
        r.raise_for_status()
        return r.json()


def _match_place(district: str, rows: list[dict], default: str | None = None) -> dict | None:
    d = district.strip().lower()
    for row in rows:
        place = str(row.get("place", "")).lower()
        if place == d or d in place or place in d:
            return row
    if default:
        for row in rows:
            if str(row.get("place", "")).lower() == default.lower():
                return row
    return None


async def fetch_current_weather(district: str) -> dict:
    d = await _hko_get("rhrread")

    temp_rows = d.get("temperature", {}).get("data", [])
    temp = _match_place(district, temp_rows, default="Hong Kong Observatory")
    rain_rows = d.get("rainfall", {}).get("data", [])
    rain = _match_place(district, rain_rows)

    hum_rows = d.get("humidity", {}).get("data", [])
    humidity_pct = hum_rows[0].get("value") if hum_rows else None

    uv = d.get("uvindex")
    uv_index = None
    if isinstance(uv, dict) and uv.get("data"):
        uv_index = uv["data"][0].get("value")

    icons = d.get("icon") or []
    condition = _HKO_ICONS.get(icons[0]) if icons else None

    return {
        "district": district,
        "temp_c": temp.get("value") if temp else None,
        "temp_station": temp.get("place") if temp else None,
        "humidity_pct": humidity_pct,
        "rainfall_mm_last_hour": (rain.get("max") if rain else None),
        "uv_index": uv_index,
        "condition": condition,
        "warning_message": d.get("warningMessage") or None,
        "update_time": d.get("temperature", {}).get("recordTime") or d.get("updateTime"),
        "source": "HK Observatory — current weather (rhrread)",
        "source_url": HKO_WEATHER,
    }


async def fetch_weather_forecast(days: int = 5) -> dict:
    days = max(1, min(days, 9))
    flw = await _hko_get("flw")
    fnd = await _hko_get("fnd")

    daily = []
    for f in fnd.get("weatherForecast", [])[:days]:
        date = f.get("forecastDate", "")
        daily.append(
            {
                "date": f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else date,
                "week": f.get("week"),
                "weather": f.get("forecastWeather"),
                "max_temp_c": f.get("forecastMaxtemp", {}).get("value"),
                "min_temp_c": f.get("forecastMintemp", {}).get("value"),
                "max_humidity_pct": f.get("forecastMaxrh", {}).get("value"),
                "min_humidity_pct": f.get("forecastMinrh", {}).get("value"),
                "wind": f.get("forecastWind"),
                "chance_of_rain": f.get("PSR"),
            }
        )

    return {
        "general_situation": flw.get("generalSituation"),
        "tropical_cyclone_info": flw.get("tcInfo") or None,
        "today": {
            "period": flw.get("forecastPeriod"),
            "description": flw.get("forecastDesc"),
            "outlook": flw.get("outlook"),
        },
        "nine_day_forecast": daily,
        "update_time": flw.get("updateTime"),
        "source": "HK Observatory — local forecast (flw) + 9-day forecast (fnd)",
        "source_url": HKO_WEATHER,
    }
