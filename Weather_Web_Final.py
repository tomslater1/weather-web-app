

import os
from datetime import datetime, timedelta, timezone

import requests
from flask import Flask, render_template_string, request

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
]

PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Weather Dashboard</title>
    <style>
        :root {
            --bg: #0a1020;
            --panel: rgba(17, 24, 43, 0.88);
            --panel-2: rgba(23, 33, 58, 0.88);
            --panel-3: #1a2642;
            --border: #263657;
            --text: #edf2ff;
            --muted: #9db0d2;
            --accent: #88aaff;
            --accent-2: #5c81f6;
            --error-bg: rgba(255, 125, 125, 0.08);
            --error-border: rgba(255, 125, 125, 0.25);
            --shadow: 0 20px 45px rgba(0, 0, 0, 0.26);
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--text);
            min-height: 100vh;
            background:
                radial-gradient(circle at top, rgba(136, 170, 255, 0.18), transparent 28%),
                linear-gradient(180deg, #09101d 0%, #0c1324 100%);
        }

        .container {
            width: min(1280px, calc(100% - 32px));
            margin: 28px auto;
            padding-bottom: 24px;
        }

        .page-grid {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 20px;
        }

        .panel {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 20px;
            backdrop-filter: blur(10px);
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .sidebar-sticky {
            position: sticky;
            top: 20px;
        }

        .mobile-search-bar {
            display: none;
        }

        .brand {
            margin-bottom: 18px;
        }

        .brand h1 {
            margin: 0 0 8px;
            font-size: clamp(1.9rem, 4vw, 2.7rem);
            letter-spacing: -0.04em;
        }

        .brand .subtle {
            color: var(--muted);
            margin: 0;
            line-height: 1.5;
        }

        .label {
            display: block;
            margin-bottom: 8px;
            color: var(--muted);
            font-size: 0.95rem;
        }

        .input, .select {
            width: 100%;
            border-radius: 14px;
            border: 1px solid var(--border);
            background: var(--panel-3);
            color: var(--text);
            padding: 14px 14px;
            font-size: 1rem;
            outline: none;
            margin-bottom: 12px;
        }

        .input:focus, .select:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 4px rgba(136, 170, 255, 0.12);
        }

        .button {
            width: 100%;
            border: 0;
            border-radius: 14px;
            padding: 14px 16px;
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            color: #09101d;
            font-size: 1rem;
            font-weight: 800;
            cursor: pointer;
            letter-spacing: -0.01em;
        }

        .button:hover {
            filter: brightness(1.04);
        }

        .quick-list {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 14px;
        }

        .quick-list form {
            margin: 0;
        }

        .quick-button {
            width: 100%;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: var(--panel-2);
            color: var(--text);
            padding: 12px 10px;
            cursor: pointer;
            font-size: 0.95rem;
        }

        .quick-button:hover {
            border-color: var(--accent);
        }

        .error {
            margin-top: 14px;
            padding: 12px 14px;
            background: var(--error-bg);
            color: #ffd0d0;
            border: 1px solid var(--error-border);
            border-radius: 14px;
        }

        .content-grid {
            display: grid;
            gap: 18px;
        }

        .desktop-sidebar {
            display: block;
        }

        .top-grid {
            display: grid;
            grid-template-columns: 1.25fr 0.85fr;
            gap: 18px;
        }

        .summary-row {
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: flex-start;
            margin-bottom: 18px;
        }

        .eyebrow {
            color: var(--muted);
            font-size: 0.95rem;
            margin: 0 0 6px;
        }

        .location {
            margin: 0;
            font-size: clamp(1.8rem, 4vw, 2.6rem);
            letter-spacing: -0.04em;
        }

        .timestamp {
            color: var(--muted);
            margin-top: 8px;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(136, 170, 255, 0.12);
            border: 1px solid rgba(136, 170, 255, 0.18);
            color: var(--muted);
            font-size: 0.9rem;
            white-space: nowrap;
        }

        .hero-weather {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 18px;
            align-items: center;
            margin-bottom: 18px;
        }

        .weather-icon {
            width: 92px;
            height: 92px;
            object-fit: contain;
            filter: drop-shadow(0 10px 20px rgba(0, 0, 0, 0.18));
        }

        .temperature {
            font-size: clamp(3.5rem, 9vw, 5.8rem);
            line-height: 0.95;
            margin: 0;
            letter-spacing: -0.07em;
            font-weight: 900;
        }

        .condition {
            color: var(--muted);
            font-size: 1.05rem;
            margin-top: 8px;
        }

        .range-line {
            color: var(--muted);
            margin-top: 10px;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }

        .metric {
            background: var(--panel-2);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 14px;
            min-height: 92px;
        }

        .metric .name {
            color: var(--muted);
            font-size: 0.9rem;
            margin-bottom: 10px;
        }

        .metric .value {
            font-size: 1.22rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        .metric .tiny {
            color: var(--muted);
            margin-top: 8px;
            font-size: 0.86rem;
            line-height: 1.4;
        }

        .mini-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }

        .section-title {
            margin: 0 0 14px;
            font-size: 1.05rem;
            letter-spacing: -0.02em;
        }

        .hourly-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(125px, 1fr));
            gap: 12px;
        }

        .hour-card {
            background: var(--panel-2);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 14px;
        }

        .hourly-grid::-webkit-scrollbar {
            height: 8px;
        }

        .hourly-grid::-webkit-scrollbar-thumb {
            background: rgba(136, 170, 255, 0.22);
            border-radius: 999px;
        }

        .hour-time {
            color: var(--muted);
            font-size: 0.9rem;
            margin-bottom: 10px;
        }

        .hour-icon {
            width: 46px;
            height: 46px;
            object-fit: contain;
            margin-bottom: 8px;
        }

        .hour-temp {
            font-size: 1.15rem;
            font-weight: 800;
            margin-bottom: 4px;
        }

        .hour-desc, .hour-meta {
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.4;
        }

        .daily-grid {
            display: grid;
            gap: 10px;
        }

        .day-row {
            display: grid;
            grid-template-columns: 1.2fr 0.8fr 0.9fr 0.8fr 0.8fr;
            gap: 12px;
            align-items: center;
            background: var(--panel-2);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px;
        }

        .day-main {
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 0;
        }

        .day-icon {
            width: 42px;
            height: 42px;
            object-fit: contain;
        }

        .day-name {
            font-weight: 700;
        }

        .day-desc {
            color: var(--muted);
            font-size: 0.88rem;
        }

        .right {
            text-align: right;
        }

        .empty-state {
            min-height: 420px;
            display: grid;
            place-items: center;
            text-align: center;
            color: var(--muted);
        }

        @media (max-width: 1200px) {
            .metrics-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }

        @media (max-width: 1024px) {
            .page-grid,
            .top-grid {
                grid-template-columns: 1fr;
            }

            .sidebar-sticky {
                position: static;
            }
        }

        @media (max-width: 760px) {
            .container {
                width: min(100%, calc(100% - 16px));
                margin: 8px auto;
                padding-bottom: 16px;
            }

            .page-grid,
            .top-grid {
                grid-template-columns: 1fr;
                gap: 10px;
            }

            .desktop-sidebar {
                display: none;
            }

            .mobile-search-bar {
                display: block;
                margin-bottom: 10px;
            }

            .panel {
                border-radius: 18px;
                padding: 14px;
            }

            .brand {
                margin-bottom: 10px;
            }

            .brand h1 {
                font-size: 1.35rem;
                margin-bottom: 4px;
            }

            .brand .subtle,
            .eyebrow,
            .timestamp,
            .condition,
            .range-line,
            .metric .tiny,
            .hour-desc,
            .hour-meta,
            .day-desc {
                font-size: 0.82rem;
            }

            .summary-row {
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
                margin-bottom: 12px;
            }

            .hero-weather {
                grid-template-columns: 64px 1fr;
                gap: 12px;
                margin-bottom: 12px;
                align-items: center;
            }

            .weather-icon {
                width: 64px;
                height: 64px;
            }

            .location {
                font-size: 1.45rem;
            }

            .temperature {
                font-size: clamp(2.5rem, 12vw, 3.7rem);
            }

            .metrics-grid,
            .mini-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 8px;
            }

            .metric {
                min-height: 72px;
                padding: 10px;
                border-radius: 14px;
            }

            .metric .name {
                margin-bottom: 6px;
                font-size: 0.8rem;
            }

            .metric .value {
                font-size: 1rem;
            }

            .hourly-grid {
                display: grid;
                grid-auto-flow: column;
                grid-auto-columns: minmax(132px, 68vw);
                grid-template-columns: none;
                overflow-x: auto;
                overflow-y: hidden;
                padding-bottom: 4px;
                scroll-snap-type: x proximity;
                gap: 8px;
            }

            .hour-card {
                scroll-snap-align: start;
                padding: 12px;
                border-radius: 14px;
            }

            .hour-time {
                margin-bottom: 8px;
                font-size: 0.82rem;
            }

            .hour-icon {
                width: 40px;
                height: 40px;
                margin-bottom: 6px;
            }

            .hour-temp {
                font-size: 1rem;
            }

            .day-row {
                grid-template-columns: 1fr;
                text-align: left;
                gap: 6px;
                padding: 12px;
                border-radius: 14px;
            }

            .day-icon {
                width: 36px;
                height: 36px;
            }

            .right {
                text-align: left;
            }

            .section-title {
                margin-bottom: 10px;
                font-size: 0.95rem;
            }
        }

        @media (max-width: 520px) {
            .input, .select, .button {
                padding: 12px 11px;
                font-size: 0.95rem;
                margin-bottom: 10px;
            }

            .quick-list {
                display: none;
            }

            .metrics-grid,
            .mini-grid {
                grid-template-columns: 1fr 1fr;
            }

            .hero-weather {
                grid-template-columns: 56px 1fr;
                gap: 10px;
            }

            .weather-icon {
                width: 56px;
                height: 56px;
            }

            .location {
                font-size: 1.3rem;
            }

            .temperature {
                font-size: clamp(2.25rem, 11vw, 3.2rem);
            }
        }
    </style>
</head>
<body>
    <main class="container">
        <section class="mobile-search-bar panel">
            <form method="post">
                <label class="label" for="mobile-city">City</label>
                <input class="input" id="mobile-city" name="city" type="text" placeholder="Enter a city" value="{{ city }}">
                <button class="button" type="submit">Search</button>
            </form>
            {% if error %}
                <div class="error">{{ error }}</div>
            {% endif %}
        </section>

        <section class="page-grid">
            <aside class="panel sidebar-sticky desktop-sidebar">
                <div class="brand">
                    <h1>Weather</h1>
                    <p class="subtle">Live conditions and forecast</p>
                </div>

                <form method="post">
                    <label class="label" for="city">City</label>
                    <input class="input" id="city" name="city" type="text" placeholder="Enter a city" value="{{ city }}">

                    <label class="label" for="saved_city">Saved cities</label>
                    <select class="select" id="saved_city" name="saved_city" onchange="if(this.value){document.getElementById('city').value=this.value;}">
                        <option value="">Choose a city</option>
                        {% for item in saved_cities %}
                            <option value="{{ item }}">{{ item }}</option>
                        {% endfor %}
                    </select>

                    <button class="button" type="submit">Search</button>
                </form>

                <div class="quick-list">
                    {% for item in saved_cities %}
                        <form method="post">
                            <input type="hidden" name="city" value="{{ item }}">
                            <button class="quick-button" type="submit">{{ item }}</button>
                        </form>
                    {% endfor %}
                </div>

                {% if error %}
                    <div class="error">{{ error }}</div>
                {% endif %}
            </aside>

            <section class="content-grid">
                {% if weather %}
                    <div class="top-grid">
                        <section class="panel">
                            <div class="summary-row">
                                <div>
                                    <p class="eyebrow">Current weather</p>
                                    <h2 class="location">{{ weather.location }}</h2>
                                    <div class="timestamp">{{ weather.local_time }}</div>
                                </div>
                                <div class="badge">{{ weather.country_code }}</div>
                            </div>

                            <div class="hero-weather">
                                <img class="weather-icon" src="{{ weather.icon_url }}" alt="{{ weather.description }} icon">
                                <div>
                                    <div class="temperature">{{ weather.temp }}°C</div>
                                    <div class="condition">{{ weather.description }}</div>
                                    <div class="range-line">Feels like {{ weather.feels_like }}°C · H {{ weather.temp_max }}°C · L {{ weather.temp_min }}°C</div>
                                </div>
                            </div>

                            <div class="metrics-grid">
                                <div class="metric">
                                    <div class="name">Humidity</div>
                                    <div class="value">{{ weather.humidity }}%</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Pressure</div>
                                    <div class="value">{{ weather.pressure }} hPa</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Visibility</div>
                                    <div class="value">{{ weather.visibility_km }} km</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Cloud cover</div>
                                    <div class="value">{{ weather.clouds }}%</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Wind</div>
                                    <div class="value">{{ weather.wind_speed }} m/s</div>
                                    <div class="tiny">Direction {{ weather.wind_deg }}°{% if weather.wind_gust != '--' %} · Gust {{ weather.wind_gust }} m/s{% endif %}</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Sun</div>
                                    <div class="value">{{ weather.sunrise }}</div>
                                    <div class="tiny">Sunset {{ weather.sunset }}</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Precipitation</div>
                                    <div class="value">{{ weather.rain_1h }} mm</div>
                                    <div class="tiny">Snow {{ weather.snow_1h }} mm</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Air quality</div>
                                    <div class="value">{{ weather.aqi_label }}</div>
                                    <div class="tiny">PM2.5 {{ weather.pm25 }} · PM10 {{ weather.pm10 }}</div>
                                </div>
                            </div>
                        </section>

                        <section class="panel">
                            <h3 class="section-title">Extra detail</h3>
                            <div class="mini-grid">
                                <div class="metric">
                                    <div class="name">Coordinates</div>
                                    <div class="value">{{ weather.lat }}, {{ weather.lon }}</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Timezone</div>
                                    <div class="value">{{ weather.timezone_name }}</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Sea level</div>
                                    <div class="value">{{ weather.sea_level }} hPa</div>
                                </div>
                                <div class="metric">
                                    <div class="name">Ground level</div>
                                    <div class="value">{{ weather.grnd_level }} hPa</div>
                                </div>
                                <div class="metric">
                                    <div class="name">CO</div>
                                    <div class="value">{{ weather.co }}</div>
                                </div>
                                <div class="metric">
                                    <div class="name">NO₂</div>
                                    <div class="value">{{ weather.no2 }}</div>
                                </div>
                                <div class="metric">
                                    <div class="name">O₃</div>
                                    <div class="value">{{ weather.o3 }}</div>
                                </div>
                                <div class="metric">
                                    <div class="name">SO₂</div>
                                    <div class="value">{{ weather.so2 }}</div>
                                </div>
                            </div>
                        </section>
                    </div>

                    <section class="panel">
                        <h3 class="section-title">Next 8 forecast blocks</h3>
                        <div class="hourly-grid">
                            {% for item in forecast %}
                                <article class="hour-card">
                                    <div class="hour-time">{{ item.time }}</div>
                                    <img class="hour-icon" src="{{ item.icon_url }}" alt="{{ item.description }} icon">
                                    <div class="hour-temp">{{ item.temp }}°C</div>
                                    <div class="hour-desc">{{ item.description }}</div>
                                    <div class="hour-meta">Feels {{ item.feels_like }}°C · Rain {{ item.pop }}%</div>
                                    <div class="hour-meta">Wind {{ item.wind_speed }} m/s · Humidity {{ item.humidity }}%</div>
                                </article>
                            {% endfor %}
                        </div>
                    </section>

                    <section class="panel">
                        <h3 class="section-title">5 day outlook</h3>
                        <div class="daily-grid">
                            {% for day in daily_summary %}
                                <div class="day-row">
                                    <div class="day-main">
                                        <img class="day-icon" src="{{ day.icon_url }}" alt="{{ day.description }} icon">
                                        <div>
                                            <div class="day-name">{{ day.day_name }}</div>
                                            <div class="day-desc">{{ day.description }}</div>
                                        </div>
                                    </div>
                                    <div class="right"><strong>{{ day.temp_max }}°C</strong> / {{ day.temp_min }}°C</div>
                                    <div class="right">Rain {{ day.pop }}%</div>
                                    <div class="right">Wind {{ day.wind_speed }} m/s</div>
                                    <div class="right">Humidity {{ day.humidity }}%</div>
                                </div>
                            {% endfor %}
                        </div>
                    </section>
                {% else %}
                    <section class="panel empty-state">
                        <div>
                            <h2>Search a city</h2>
                        </div>
                    </section>
                {% endif %}
            </section>
        </section>
    </main>
</body>
</html>
"""


AQI_LABELS = {
    1: "Good",
    2: "Fair",
    3: "Moderate",
    4: "Poor",
    5: "Very Poor",
}


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


def format_local_time(timestamp_value, tz_offset_seconds, fmt):
    if timestamp_value is None:
        return "--"
    tz_info = timezone(timedelta(seconds=tz_offset_seconds))
    return datetime.fromtimestamp(timestamp_value, tz=tz_info).strftime(fmt)


def get_coordinates(city_name):
    params = {
        "q": city_name,
        "limit": 1,
        "appid": API_KEY,
    }
    response = requests.get(GEOCODE_URL, params=params, timeout=8)
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    return results[0]


def get_current_weather(lat, lon):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
    }
    response = requests.get(WEATHER_URL, params=params, timeout=8)
    response.raise_for_status()
    return response.json()


def get_forecast(lat, lon):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
        "cnt": 8,
    }
    response = requests.get(FORECAST_URL, params=params, timeout=8)
    response.raise_for_status()
    return response.json()


def get_full_forecast(lat, lon):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=8)
    response.raise_for_status()
    return response.json()


def get_air_pollution(lat, lon):
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
    }
    response = requests.get(AIR_POLLUTION_URL, params=params, timeout=8)
    response.raise_for_status()
    return response.json()


def build_weather_context(current_data, coordinate_data, air_data):
    weather_entry = current_data["weather"][0]
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
        "local_time": format_local_time(current_data.get("dt"), tz_offset, "%a %d %b %Y · %H:%M"),
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
        "description": weather_entry.get("description", "Unknown").title(),
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
    }


def build_hourly_context(forecast_data, tz_offset):
    items = []
    for entry in forecast_data.get("list", []):
        weather_entry = entry["weather"][0]
        main_data = entry.get("main", {})
        wind_data = entry.get("wind", {})
        rain_data = entry.get("rain", {})
        snow_data = entry.get("snow", {})

        items.append(
            {
                "time": format_local_time(entry.get("dt"), tz_offset, "%a %H:%M"),
                "temp": safe_round(main_data.get("temp")),
                "feels_like": safe_round(main_data.get("feels_like")),
                "description": weather_entry.get("description", "Unknown").title(),
                "icon_url": icon_url(weather_entry.get("icon")),
                "pop": safe_round((entry.get("pop") or 0) * 100),
                "wind_speed": safe_round(wind_data.get("speed"), 1),
                "humidity": main_data.get("humidity", "--"),
                "rain_mm": safe_round(rain_data.get("3h"), 1),
                "snow_mm": safe_round(snow_data.get("3h"), 1),
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
                "description": weather_entry.get("description", "Unknown").title(),
                "icon_url": icon_url(weather_entry.get("icon")),
                "temp_min": safe_round(min(temps) if temps else None),
                "temp_max": safe_round(max(temps) if temps else None),
                "humidity": safe_round(sum(humidities) / len(humidities), 0) if humidities else "--",
                "wind_speed": safe_round(max(wind_speeds) if wind_speeds else None, 1),
                "pop": safe_round(max(pops) if pops else None),
            }
        )
    return summaries


@app.route("/", methods=["GET", "POST"])
def index():
    city = "Manchester"
    error = None
    weather = None
    forecast = []
    daily_summary = []

    if request.method == "POST":
        city = (request.form.get("city") or request.form.get(
            "saved_city") or "").strip()
        if not API_KEY:
            error = "Missing API key. Set OPENWEATHER_API_KEY before starting Flask."
        elif not city:
            error = "Please enter a city name."
        else:
            try:
                coordinate_data = get_coordinates(city)
                if not coordinate_data:
                    error = "City not found. Try a more specific name."
                else:
                    lat = coordinate_data["lat"]
                    lon = coordinate_data["lon"]
                    current_data = get_current_weather(lat, lon)
                    forecast_data = get_forecast(lat, lon)
                    full_forecast_data = get_full_forecast(lat, lon)
                    air_data = get_air_pollution(lat, lon)
                    tz_offset = current_data.get("timezone", 0)

                    weather = build_weather_context(
                        current_data, coordinate_data, air_data)
                    forecast = build_hourly_context(forecast_data, tz_offset)
                    daily_summary = build_daily_summary(
                        full_forecast_data, tz_offset)
            except requests.exceptions.HTTPError:
                error = "The weather provider returned an error for that location."
            except requests.exceptions.RequestException as exc:
                error = f"Network error: {exc}"
            except (KeyError, IndexError, ValueError):
                error = "The provider returned data in an unexpected format."

    return render_template_string(
        PAGE_TEMPLATE,
        city=city,
        saved_cities=SAVED_CITIES,
        weather=weather,
        forecast=forecast,
        daily_summary=daily_summary,
        error=error,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
