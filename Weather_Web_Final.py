import hashlib
import os
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import quote_plus, unquote_plus

import requests
from flask import Flask, Response, redirect, render_template, request, url_for

app = Flask(__name__)

API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

SAVED_CITIES = [
    "Manchester",
    "London",
    "Edinburgh",
    "Montreal",
    "Dublin",
    "New York",
    "Paris",
    "Tokyo",
    "Barcelona",
    "Singapore",
    "Sydney",
    "Dubai",
    "Amsterdam",
    "Berlin",
    "Rome",
    "Madrid",
    "Los Angeles",
    "Toronto",
    "San Francisco",
    "Hong Kong",
    "Seoul",
    "Cape Town",
]

AQI_LABELS = {
    1: "Good",
    2: "Fair",
    3: "Moderate",
    4: "Poor",
    5: "Very Poor",
}

DESCRIPTION_MAP = {
    "clear sky": "Clear Sky",
    "few clouds": "Partly Cloudy",
    "scattered clouds": "Scattered Clouds",
    "broken clouds": "Broken Clouds",
    "overcast clouds": "Overcast",
    "mist": "Misty",
    "haze": "Hazy",
    "fog": "Foggy",
    "smoke": "Smoky",
    "light rain": "Light Rain",
    "moderate rain": "Rain",
    "heavy intensity rain": "Heavy Rain",
    "very heavy rain": "Very Heavy Rain",
    "extreme rain": "Extreme Rain",
    "light snow": "Light Snow",
    "snow": "Snow",
    "heavy snow": "Heavy Snow",
    "thunderstorm": "Thunderstorm",
}

CITY_CACHE = {}
CACHE_TTL_SECONDS = 600


def safe_round(value, digits=0):
    if value is None:
        return "--"
    if digits == 0:
        return round(value)
    return round(value, digits)


def icon_url(icon_code):
    if not icon_code:
        return ""
    return f"https://openweathermap.org/img/wn/{icon_code}@2x.png"


def city_image_url(city_name):
    safe_city = quote_plus((city_name or "City").strip())
    return f"/city-image/{safe_city}?v=2"


def city_palette(city_name):
    palettes = [
        ("#0c4a6e", "#0ea5a6", "#f59e0b"),
        ("#1d4ed8", "#0f766e", "#f97316"),
        ("#7c3aed", "#2563eb", "#14b8a6"),
        ("#be123c", "#4338ca", "#0ea5a6"),
        ("#065f46", "#1d4ed8", "#ea580c"),
    ]
    digest = int(hashlib.sha256(city_name.lower().encode("utf-8")).hexdigest(), 16)
    return palettes[digest % len(palettes)]


def deterministic_values(seed_text, count):
    values = []
    state = seed_text.encode("utf-8")
    while len(values) < count:
        state = hashlib.sha256(state).digest()
        values.extend(byte / 255 for byte in state)
    return values[:count]


def build_city_image_svg(city_name):
    first, second, accent = city_palette(city_name)
    safe_city = escape(city_name)
    initials = "".join(word[0] for word in city_name.split()[:2]).upper() or "CT"
    values = deterministic_values(city_name.lower(), 320)

    skyline_back = []
    skyline_front = []
    window_glow = []

    x = -18
    for i in range(20):
        width = 34 + int(values[i] * 72)
        height = 130 + int(values[40 + i] * 250)
        y = 780 - height
        radius = 6 + int(values[80 + i] * 8)
        opacity = 0.26 + values[120 + i] * 0.24
        skyline_back.append(
            f"<rect x='{x}' y='{y}' width='{width}' height='{height}' rx='{radius}' fill='#020617' opacity='{opacity:.3f}' />"
        )
        x += width - 10

    x = -24
    for i in range(26):
        width = 26 + int(values[160 + i] * 64)
        height = 180 + int(values[200 + i] * 410)
        y = 840 - height
        radius = 5 + int(values[240 + i] * 8)
        opacity = 0.46 + values[280 + i] * 0.38
        skyline_front.append(
            f"<rect x='{x}' y='{y}' width='{width}' height='{height}' rx='{radius}' fill='#01050f' opacity='{opacity:.3f}' />"
        )

        window_cols = max(1, int(width / 18))
        for col in range(window_cols):
            wx = x + 7 + col * 14
            if wx > x + width - 8:
                continue
            for row in range(6):
                if values[(i * 7 + col * 5 + row) % len(values)] > 0.53:
                    wy = y + 14 + row * 19
                    if wy < y + height - 8:
                        window_glow.append(
                            f"<rect x='{wx}' y='{wy}' width='4' height='8' rx='2' fill='{accent}' opacity='0.34' />"
                        )

        x += width - 20

    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='1600' height='1000' viewBox='0 0 1600 1000' role='img' aria-label='{safe_city}'>
<defs>
  <linearGradient id='sky' x1='0' y1='0' x2='1' y2='1'>
    <stop offset='0%' stop-color='{first}' />
    <stop offset='58%' stop-color='{second}' />
    <stop offset='100%' stop-color='#020617' />
  </linearGradient>
  <linearGradient id='mist' x1='0' y1='0' x2='0' y2='1'>
    <stop offset='0%' stop-color='rgba(255,255,255,0.06)' />
    <stop offset='70%' stop-color='rgba(2,6,23,0.24)' />
    <stop offset='100%' stop-color='rgba(2,6,23,0.78)' />
  </linearGradient>
  <radialGradient id='sun' cx='0.2' cy='0.2' r='0.7'>
    <stop offset='0%' stop-color='{accent}' stop-opacity='0.74' />
    <stop offset='65%' stop-color='{accent}' stop-opacity='0.1' />
    <stop offset='100%' stop-color='transparent' />
  </radialGradient>
  <filter id='softGlow'><feGaussianBlur stdDeviation='62' /></filter>
  <filter id='grain' x='-10%' y='-10%' width='120%' height='120%'>
    <feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2' stitchTiles='stitch' />
    <feColorMatrix type='saturate' values='0' />
    <feComponentTransfer>
      <feFuncA type='table' tableValues='0 0.06' />
    </feComponentTransfer>
  </filter>
  <pattern id='scan' width='4' height='4' patternUnits='userSpaceOnUse'>
    <rect width='4' height='1' fill='rgba(255,255,255,0.02)' />
  </pattern>
</defs>
<rect width='1600' height='1000' fill='url(#sky)' />
<rect width='1600' height='1000' fill='url(#scan)' />
<circle cx='260' cy='210' r='320' fill='url(#sun)' filter='url(#softGlow)' />
<circle cx='1320' cy='770' r='260' fill='{accent}' opacity='0.16' filter='url(#softGlow)' />
<path d='M0 640 C220 560, 360 560, 520 620 C680 680, 820 700, 1020 640 C1180 592, 1350 600, 1600 690 L1600 1000 L0 1000 Z' fill='rgba(2,6,23,0.36)' />
<g>{''.join(skyline_back)}</g>
<g>{''.join(skyline_front)}</g>
<g>{''.join(window_glow)}</g>
<rect width='1600' height='1000' fill='url(#mist)' />
<rect width='1600' height='1000' filter='url(#grain)' />
<rect x='74' y='694' width='1452' height='246' rx='28' fill='rgba(2,6,23,0.52)' stroke='rgba(148,163,184,0.22)' />
<text x='136' y='824' fill='#e2e8f0' font-family='Segoe UI, Arial, sans-serif' font-size='88' font-weight='700' letter-spacing='0.8'>{safe_city}</text>
<text x='136' y='892' fill='rgba(226,232,240,0.86)' font-family='Segoe UI, Arial, sans-serif' font-size='33'>Live Weather Cover Art</text>
<text x='1466' y='144' text-anchor='end' fill='rgba(226,232,240,0.62)' font-family='Segoe UI, Arial, sans-serif' font-size='140' font-weight='700'>{initials}</text>
</svg>"""


def format_local_time(timestamp_value, tz_offset_seconds, fmt):
    if timestamp_value is None:
        return "--"
    tz_info = timezone(timedelta(seconds=tz_offset_seconds))
    return datetime.fromtimestamp(timestamp_value, tz=tz_info).strftime(fmt)


def clean_weather_description(raw_description):
    if not raw_description:
        return "Unknown"

    text = str(raw_description).strip()
    if not text:
        return "Unknown"

    if any(marker in text for marker in ("Ã", "Â", "â")):
        try:
            text = text.encode("latin1").decode("utf-8")
        except UnicodeError:
            pass

    text = unicodedata.normalize("NFKC", text).replace("\ufffd", " ").strip()
    lowered = text.lower()
    if lowered in DESCRIPTION_MAP:
        return DESCRIPTION_MAP[lowered]

    cleaned = re.sub(r"[^A-Za-z0-9\s\-/,.()]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return "Unknown"
    return cleaned.title()


def fetch_json(url, params, timeout=8):
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_coordinates(city_name):
    return fetch_json(
        GEOCODE_URL,
        {
            "q": city_name,
            "limit": 1,
            "appid": API_KEY,
        },
    )


def get_current_weather(lat, lon):
    return fetch_json(
        WEATHER_URL,
        {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
            "units": "metric",
        },
    )


def get_current_weather_by_city(city_name):
    return fetch_json(
        WEATHER_URL,
        {
            "q": city_name,
            "appid": API_KEY,
            "units": "metric",
        },
    )


def get_forecast(lat, lon, count=None):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
    }
    if count is not None:
        params["cnt"] = count
    return fetch_json(FORECAST_URL, params)


def get_air_pollution(lat, lon):
    return fetch_json(
        AIR_POLLUTION_URL,
        {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
        },
    )


def build_weather_context(current_data, coordinate_data, air_data):
    weather_entry = current_data.get("weather", [{}])[0]
    main_data = current_data.get("main", {})
    wind_data = current_data.get("wind", {})
    sys_data = current_data.get("sys", {})
    clouds_data = current_data.get("clouds", {})
    rain_data = current_data.get("rain", {})
    snow_data = current_data.get("snow", {})
    visibility_m = current_data.get("visibility")
    tz_offset = current_data.get("timezone", 0)

    location_name = current_data.get(
        "name") or coordinate_data.get("name") or "Unknown"
    state_name = coordinate_data.get("state")
    country_code = current_data.get("sys", {}).get(
        "country") or coordinate_data.get("country", "--")

    if state_name:
        location = f"{location_name}, {state_name}, {country_code}"
    else:
        location = f"{location_name}, {country_code}"

    air_item = {}
    air_components = {}
    air_list = air_data.get("list", []) if air_data else []
    if air_list:
        air_item = air_list[0]
        air_components = air_item.get("components", {})

    timezone_hours = tz_offset / 3600
    if timezone_hours == int(timezone_hours):
        timezone_name = f"UTC{int(timezone_hours):+d}"
    else:
        timezone_name = f"UTC{timezone_hours:+.1f}"

    return {
        "location": location,
        "country_code": country_code,
        "local_time": format_local_time(current_data.get("dt"), tz_offset, "%a %d %b %Y | %H:%M"),
        "temp": safe_round(main_data.get("temp")),
        "feels_like": safe_round(main_data.get("feels_like")),
        "temp_min": safe_round(main_data.get("temp_min")),
        "temp_max": safe_round(main_data.get("temp_max")),
        "humidity": main_data.get("humidity", "--"),
        "pressure": main_data.get("pressure", "--"),
        "sea_level": main_data.get("sea_level", "--"),
        "grnd_level": main_data.get("grnd_level", "--"),
        "visibility_km": safe_round((visibility_m or 0) / 1000, 1) if visibility_m is not None else "--",
        "clouds": clouds_data.get("all", "--"),
        "wind_speed": safe_round(wind_data.get("speed"), 1),
        "wind_deg": wind_data.get("deg", "--"),
        "wind_gust": safe_round(wind_data.get("gust"), 1),
        "sunrise": format_local_time(sys_data.get("sunrise"), tz_offset, "%H:%M"),
        "sunset": format_local_time(sys_data.get("sunset"), tz_offset, "%H:%M"),
        "rain_1h": safe_round(rain_data.get("1h"), 1),
        "snow_1h": safe_round(snow_data.get("1h"), 1),
        "description": clean_weather_description(weather_entry.get("description")),
        "icon_url": icon_url(weather_entry.get("icon")),
        "lat": safe_round(current_data.get("coord", {}).get("lat"), 2),
        "lon": safe_round(current_data.get("coord", {}).get("lon"), 2),
        "timezone_name": timezone_name,
        "aqi_label": AQI_LABELS.get(air_item.get("main", {}).get("aqi"), "--"),
        "pm25": safe_round(air_components.get("pm2_5"), 1),
        "pm10": safe_round(air_components.get("pm10"), 1),
        "co": safe_round(air_components.get("co"), 1),
        "no2": safe_round(air_components.get("no2"), 1),
        "o3": safe_round(air_components.get("o3"), 1),
        "so2": safe_round(air_components.get("so2"), 1),
        "image_url": city_image_url(location_name),
    }


def build_hourly_context(forecast_data, tz_offset):
    items = []
    for entry in forecast_data.get("list", []):
        weather_entry = entry.get("weather", [{}])[0]
        main_data = entry.get("main", {})
        wind_data = entry.get("wind", {})

        items.append(
            {
                "time": format_local_time(entry.get("dt"), tz_offset, "%a %H:%M"),
                "temp": safe_round(main_data.get("temp")),
                "feels_like": safe_round(main_data.get("feels_like")),
                "description": clean_weather_description(weather_entry.get("description")),
                "icon_url": icon_url(weather_entry.get("icon")),
                "pop": safe_round((entry.get("pop") or 0) * 100),
                "wind_speed": safe_round(wind_data.get("speed"), 1),
                "humidity": main_data.get("humidity", "--"),
            }
        )
    return items


def build_daily_summary(full_forecast_data, tz_offset):
    grouped = {}
    for entry in full_forecast_data.get("list", []):
        day_key = format_local_time(entry.get("dt"), tz_offset, "%Y-%m-%d")
        grouped.setdefault(day_key, []).append(entry)

    summaries = []
    for _, entries in list(grouped.items())[:5]:
        temps = [item.get("main", {}).get("temp") for item in entries if item.get(
            "main", {}).get("temp") is not None]
        humidities = [item.get("main", {}).get("humidity") for item in entries if item.get(
            "main", {}).get("humidity") is not None]
        wind_speeds = [item.get("wind", {}).get(
            "speed") for item in entries if item.get("wind", {}).get("speed") is not None]
        pops = [(item.get("pop") or 0) * 100 for item in entries]

        midday_entry = entries[len(entries) // 2]
        weather_entry = midday_entry.get("weather", [{}])[0]

        summaries.append(
            {
                "day_name": format_local_time(midday_entry.get("dt"), tz_offset, "%A"),
                "description": clean_weather_description(weather_entry.get("description")),
                "icon_url": icon_url(weather_entry.get("icon")),
                "temp_min": safe_round(min(temps) if temps else None),
                "temp_max": safe_round(max(temps) if temps else None),
                "humidity": safe_round(sum(humidities) / len(humidities), 0) if humidities else "--",
                "wind_speed": safe_round(max(wind_speeds) if wind_speeds else None, 1),
                "pop": safe_round(max(pops) if pops else None),
            }
        )

    return summaries


def from_cache(key):
    payload = CITY_CACHE.get(key)
    if not payload:
        return None
    if time.time() - payload["ts"] > CACHE_TTL_SECONDS:
        CITY_CACHE.pop(key, None)
        return None
    return payload["value"]


def set_cache(key, value):
    CITY_CACHE[key] = {"ts": time.time(), "value": value}


def get_city_snapshot(city_name):
    cache_key = f"snapshot::{city_name.lower()}"
    cached = from_cache(cache_key)
    if cached:
        return cached

    current_data = get_current_weather_by_city(city_name)
    weather_entry = current_data.get("weather", [{}])[0]
    main_data = current_data.get("main", {})

    snapshot = {
        "city": current_data.get("name", city_name),
        "country": current_data.get("sys", {}).get("country", "--"),
        "description": clean_weather_description(weather_entry.get("description")),
        "temp": safe_round(main_data.get("temp")),
        "temp_min": safe_round(main_data.get("temp_min")),
        "temp_max": safe_round(main_data.get("temp_max")),
        "humidity": main_data.get("humidity", "--"),
        "wind_speed": safe_round(current_data.get("wind", {}).get("speed"), 1),
        "icon_url": icon_url(weather_entry.get("icon")),
        "image_url": city_image_url(current_data.get("name", city_name)),
        "updated": format_local_time(current_data.get("dt"), current_data.get("timezone", 0), "%H:%M"),
    }
    set_cache(cache_key, snapshot)
    return snapshot


def get_saved_city_snapshots(cities):
    cards = []
    for city_name in cities:
        try:
            cards.append(get_city_snapshot(city_name))
        except requests.exceptions.RequestException:
            cards.append(
                {
                    "city": city_name,
                    "country": "--",
                    "description": "Weather unavailable",
                    "temp": "--",
                    "temp_min": "--",
                    "temp_max": "--",
                    "humidity": "--",
                    "wind_speed": "--",
                    "icon_url": "",
                    "image_url": city_image_url(city_name),
                    "updated": "--",
                }
            )
    return cards


def fetch_city_bundle(city_name):
    if not API_KEY:
        raise RuntimeError(
            "Missing API key. Set OPENWEATHER_API_KEY before starting Flask.")

    coordinate_results = get_coordinates(city_name)
    if not coordinate_results:
        return None

    coordinate_data = coordinate_results[0]
    lat = coordinate_data["lat"]
    lon = coordinate_data["lon"]

    current_data = get_current_weather(lat, lon)
    forecast_data = get_forecast(lat, lon, count=8)
    full_forecast_data = get_forecast(lat, lon)
    air_data = get_air_pollution(lat, lon)
    tz_offset = current_data.get("timezone", 0)

    return {
        "weather": build_weather_context(current_data, coordinate_data, air_data),
        "forecast": build_hourly_context(forecast_data, tz_offset),
        "daily_summary": build_daily_summary(full_forecast_data, tz_offset),
    }


def load_city_bundle_for_view(city):
    error = None
    weather_bundle = None

    if not city:
        if not API_KEY:
            return None, "Missing API key. Set OPENWEATHER_API_KEY before starting Flask."
        return None, None

    try:
        weather_bundle = fetch_city_bundle(city)
        if weather_bundle is None:
            error = "City not found. Try a more specific name."
    except RuntimeError as exc:
        error = str(exc)
    except requests.exceptions.HTTPError:
        error = "The weather provider returned an error for that location."
    except requests.exceptions.RequestException:
        error = "Network issue while contacting OpenWeather."
    except (KeyError, IndexError, ValueError):
        error = "Unexpected weather data format received from provider."

    return weather_bundle, error


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compute_city_insights(cards):
    ranked = []
    for card in cards:
        temp = as_float(card.get("temp"))
        humidity = as_float(card.get("humidity"))
        wind_speed = as_float(card.get("wind_speed"))
        if temp is None or humidity is None or wind_speed is None:
            continue

        score = 100 - abs(temp - 21) * 2.2 - humidity * 0.18 - wind_speed * 1.7
        description = str(card.get("description", "")).lower()
        if "rain" in description or "storm" in description or "snow" in description:
            score -= 8
        if "clear" in description or "sun" in description:
            score += 4

        ranked.append(
            {
                **card,
                "comfort_score": max(0, min(100, round(score))),
                "temp_value": temp,
                "wind_value": wind_speed,
                "humidity_value": humidity,
            }
        )

    ranked.sort(key=lambda item: item["comfort_score"], reverse=True)
    warmest = sorted(ranked, key=lambda item: item["temp_value"], reverse=True)[:5]
    breeziest = sorted(ranked, key=lambda item: item["wind_value"], reverse=True)[:5]
    driest = sorted(ranked, key=lambda item: item["humidity_value"])[:5]

    return {
        "ranked": ranked,
        "top_three": ranked[:3],
        "warmest": warmest,
        "breeziest": breeziest,
        "driest": driest,
    }


@app.route("/city-image/<path:city_slug>")
def city_image(city_slug):
    city_name = unquote_plus(city_slug).strip() or "City"
    svg = build_city_image_svg(city_name)
    return Response(
        svg,
        mimetype="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.route("/")
def home():
    city = (request.args.get("city") or "London").strip()
    weather_bundle, error = load_city_bundle_for_view(city)

    spotlight_cards = []
    if API_KEY:
        spotlight_cards = get_saved_city_snapshots(SAVED_CITIES)

    return render_template(
        "home.html",
        city=city,
        error=error,
        saved_cities=SAVED_CITIES,
        spotlight_cards=spotlight_cards,
        weather=weather_bundle["weather"] if weather_bundle else None,
        forecast=weather_bundle["forecast"] if weather_bundle else [],
        daily_summary=weather_bundle["daily_summary"] if weather_bundle else [
        ],
    )


@app.route("/city", methods=["GET", "POST"])
def city_detail():
    city = ""
    if request.method == "POST":
        city = (request.form.get("city") or request.form.get(
            "saved_city") or "").strip()
    else:
        city = (request.args.get("city") or "").strip()

    weather_bundle, error = load_city_bundle_for_view(city)

    return render_template(
        "city.html",
        city=city,
        error=error,
        saved_cities=SAVED_CITIES,
        weather=weather_bundle["weather"] if weather_bundle else None,
        forecast=weather_bundle["forecast"] if weather_bundle else [],
        daily_summary=weather_bundle["daily_summary"] if weather_bundle else [
        ],
    )


@app.route("/weather", methods=["GET", "POST"])
def weather_page():
    if request.method == "POST":
        city = (request.form.get("city") or request.form.get(
            "saved_city") or "").strip()
    else:
        city = (request.args.get("city") or "").strip()
    if city:
        return redirect(url_for("city_detail", city=city))
    return redirect(url_for("city_detail"))


@app.route("/cities")
def cities_page():
    city_filter = (request.args.get("city") or "").strip()

    city_list = list(SAVED_CITIES)
    if city_filter and city_filter not in city_list:
        city_list.insert(0, city_filter)

    error = None
    cards = []

    if not API_KEY:
        error = "Missing API key. Set OPENWEATHER_API_KEY before starting Flask."
    else:
        try:
            cards = get_saved_city_snapshots(city_list)
        except requests.exceptions.RequestException:
            error = "Network issue while loading city snapshots."

    return render_template(
        "cities.html",
        cards=cards,
        error=error,
        city_filter=city_filter,
        city=city_filter,
    )


@app.route("/insights")
def insights_page():
    error = None
    cards = []
    insights = {"ranked": [], "top_three": [], "warmest": [], "breeziest": [], "driest": []}

    if not API_KEY:
        error = "Missing API key. Set OPENWEATHER_API_KEY before starting Flask."
    else:
        try:
            cards = get_saved_city_snapshots(SAVED_CITIES)
            insights = compute_city_insights(cards)
        except requests.exceptions.RequestException:
            error = "Network issue while loading city insights."

    return render_template(
        "insights.html",
        error=error,
        city="",
        insights=insights,
    )


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
