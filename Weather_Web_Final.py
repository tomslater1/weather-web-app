

import os
from datetime import datetime, timedelta, timezone

import requests
from flask import Flask, render_template_string, request, url_for

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
]

CITY_BACKGROUNDS = {
    "Manchester": "https://images.unsplash.com/photo-1529421306624-54a91fd114e3?auto=format&fit=crop&w=1200&q=80",
    "London": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1200&q=80",
    "Edinburgh": "https://images.unsplash.com/photo-1506377247377-2a5b3b417ebb?auto=format&fit=crop&w=1200&q=80",
    "Montreal": "https://images.unsplash.com/photo-1519178614-68673b201f36?auto=format&fit=crop&w=1200&q=80",
    "Dublin": "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1200&q=80",
    "New York": "https://images.unsplash.com/photo-1499092346589-b9b6be3e94b2?auto=format&fit=crop&w=1200&q=80",
    "Paris": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1200&q=80",
    "Tokyo": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=1200&q=80",
    "Barcelona": "https://images.unsplash.com/photo-1583422409516-2895a77efded?auto=format&fit=crop&w=1200&q=80",
    "Singapore": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=1200&q=80",
    "Sydney": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?auto=format&fit=crop&w=1200&q=80",
    "Dubai": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1200&q=80",
}

ICON_MAP = {
    "01d": "☀️", "01n": "🌙",
    "02d": "🌤️", "02n": "☁️",
    "03d": "☁️", "03n": "☁️",
    "04d": "☁️", "04n": "☁️",
    "09d": "🌧️", "09n": "🌧️",
    "10d": "🌦️", "10n": "🌧️",
    "11d": "⛈️", "11n": "⛈️",
    "13d": "❄️", "13n": "❄️",
    "50d": "🌫️", "50n": "🌫️",
}

AQI_LABELS = {
    1: "Good",
    2: "Fair",
    3: "Moderate",
    4: "Poor",
    5: "Very Poor",
}

BASE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ page_title }}</title>
    <meta name="theme-color" content="#081120">
    <style>
        ... (see user-provided code for full CSS) ...
    </style>
</head>
<body>
    <div class="shell">
        <div class="nav-wrap">
            <nav class="nav glass">
                <div class="brand">
                    <div class="brand-mark"></div>
                    <div>
                        <p class="brand-title">Atmos</p>
                        <p class="brand-subtitle">Modern weather for the day ahead</p>
                    </div>
                </div>
                <div class="nav-links">
                    <a class="nav-link {% if active_page == 'home' %}active{% endif %}" href="{{ url_for('home') }}">Home</a>
                    <a class="nav-link {% if active_page == 'weather' %}active{% endif %}" href="{{ url_for('weather_page') }}">Weather</a>
                    <a class="nav-link {% if active_page == 'cities' %}active{% endif %}" href="{{ url_for('cities_page') }}">Cities</a>
                </div>
            </nav>
        </div>

        {{ content|safe }}

        <footer class="footer glass">
            <div>Atmos · live weather dashboard</div>
            <div>Built with Flask · OpenWeather data</div>
        </footer>
    </div>

    <script>
        const reveals = document.querySelectorAll('.reveal');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in-view');
                }
            });
        }, { threshold: 0.12 });

        reveals.forEach((element, index) => {
            element.style.transition = 'opacity 600ms ease, translate 600ms ease, transform 240ms ease, box-shadow 240ms ease, border-color 240ms ease';
            element.style.transitionDelay = `${index * 45}ms`;
            observer.observe(element);
        });
    </script>
</body>
</html>
"""

# The rest of the code: HOME_CONTENT, WEATHER_CONTENT, CITIES_CONTENT, and all logic as provided by the user.

HOME_CONTENT = """
... (see user-provided code for full HOME_CONTENT) ...
"""

WEATHER_CONTENT = """
... (see user-provided code for full WEATHER_CONTENT) ...
"""

CITIES_CONTENT = """
... (see user-provided code for full CITIES_CONTENT) ...
"""


def safe_round(value, digits=0):
    if value is None:
        return "--"
    return round(value, digits) if digits else round(value)


def weather_symbol(icon_code):
    return ICON_MAP.get(icon_code, "🌤️")


def format_local_time(timestamp_value, tz_offset_seconds, fmt):
    if timestamp_value is None:
        return "--"
    tz_info = timezone(timedelta(seconds=tz_offset_seconds))
    return datetime.fromtimestamp(timestamp_value, tz=tz_info).strftime(fmt)


def pretty_description(raw_description):
    if not raw_description:
        return "Unknown"
    normalized = raw_description.strip().lower()
    replacements = {
        "sky is clear": "Clear Sky",
        "few clouds": "Partly Cloudy",
        "scattered clouds": "Scattered Clouds",
        "broken clouds": "Broken Clouds",
        "overcast clouds": "Overcast",
        "light rain": "Light Rain",
        "moderate rain": "Rain",
        "heavy intensity rain": "Heavy Rain",
        "very heavy rain": "Very Heavy Rain",
        "extreme rain": "Extreme Rain",
        "light snow": "Light Snow",
        "heavy snow": "Heavy Snow",
        "mist": "Misty",
        "haze": "Hazy",
        "smoke": "Smoky",
    }
    return replacements.get(normalized, normalized.title())


def render_page(page_title, active_page, content_template, **context):
    content = render_template_string(content_template, **context)
    return render_template_string(
        BASE_TEMPLATE,
        page_title=page_title,
        active_page=active_page,
        content=content,
    )


def get_coordinates(city_name):
    params = {"q": city_name, "limit": 1, "appid": API_KEY}
    response = requests.get(GEOCODE_URL, params=params, timeout=8)
    response.raise_for_status()
    results = response.json()
    return results[0] if results else None


def get_current_weather(lat, lon):
    params = {"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"}
    response = requests.get(WEATHER_URL, params=params, timeout=8)
    response.raise_for_status()
    return response.json()


def get_current_weather_by_city(city_name):
    params = {"q": city_name, "appid": API_KEY, "units": "metric"}
    response = requests.get(WEATHER_URL, params=params, timeout=8)
    response.raise_for_status()
    return response.json()


def get_forecast(lat, lon, count=8):
    params = {"lat": lat, "lon": lon, "appid": API_KEY,
              "units": "metric", "cnt": count}
    response = requests.get(FORECAST_URL, params=params, timeout=8)
    response.raise_for_status()
    return response.json()


def get_full_forecast(lat, lon):
    params = {"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"}
    response = requests.get(FORECAST_URL, params=params, timeout=8)
    response.raise_for_status()
    return response.json()


def get_air_pollution(lat, lon):
    params = {"lat": lat, "lon": lon, "appid": API_KEY}
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
    location = f"{location_name}, {state_name}, {country_code}" if state_name else f"{location_name}, {country_code}"

    air_item = {}
    air_components = {}
    air_list = air_data.get("list", []) if air_data else []
    if air_list:
        air_item = air_list[0]
        air_components = air_item.get("components", {})

    timezone_hours = tz_offset / 3600
    timezone_name = f"UTC{int(timezone_hours):+d}" if timezone_hours == int(
        timezone_hours) else f"UTC{timezone_hours:+.1f}"

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
        "description": pretty_description(weather_entry.get("description", "Unknown")),
        "symbol": weather_symbol(weather_entry.get("icon")),
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
        items.append(
            {
                "time": format_local_time(entry.get("dt"), tz_offset, "%a %H:%M"),
                "temp": safe_round(main_data.get("temp")),
                "feels_like": safe_round(main_data.get("feels_like")),
                "description": pretty_description(weather_entry.get("description", "Unknown")),
                "symbol": weather_symbol(weather_entry.get("icon")),
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
                "description": pretty_description(weather_entry.get("description", "Unknown")),
                "symbol": weather_symbol(weather_entry.get("icon")),
                "temp_min": safe_round(min(temps) if temps else None),
                "temp_max": safe_round(max(temps) if temps else None),
                "humidity": safe_round(sum(humidities) / len(humidities), 0) if humidities else "--",
                "wind_speed": safe_round(max(wind_speeds) if wind_speeds else None, 1),
                "pop": safe_round(max(pops) if pops else None),
            }
        )
    return summaries


def build_city_card_context(city_name, current_data):
    weather_entry = current_data["weather"][0]
    main_data = current_data.get("main", {})
    wind_data = current_data.get("wind", {})
    visibility_m = current_data.get("visibility")
    sys_data = current_data.get("sys", {})

    return {
        "city": current_data.get("name", city_name),
        "country_code": sys_data.get("country", "--"),
        "temp": safe_round(main_data.get("temp")),
        "feels_like": safe_round(main_data.get("feels_like")),
        "humidity": main_data.get("humidity", "--"),
        "wind_speed": safe_round(wind_data.get("speed"), 1),
        "visibility_km": safe_round((visibility_m or 0) / 1000, 1) if visibility_m is not None else "--",
        "description": pretty_description(weather_entry.get("description", "Unknown")),
        "symbol": weather_symbol(weather_entry.get("icon")),
        "photo_url": CITY_BACKGROUNDS.get(city_name, CITY_BACKGROUNDS["London"]),
    }


def get_city_cards(city_names):
    cards = []
    if not API_KEY:
        return cards
    for city_name in city_names:
        try:
            current_data = get_current_weather_by_city(city_name)
            cards.append(build_city_card_context(city_name, current_data))
        except requests.RequestException:
            continue
    return cards


@app.route("/")
def home():
    hero_cards = get_city_cards(SAVED_CITIES[:4])
    featured_cities = get_city_cards(SAVED_CITIES[2:6])
    photo_cards = [
        {"city": city, "description": "City atmosphere and live weather context",
            "photo_url": CITY_BACKGROUNDS[city]}
        for city in ["Manchester", "New York", "Tokyo"]
    ]
    return render_page(
        "Atmos · Home",
        "home",
        HOME_CONTENT,
        hero_cards=hero_cards,
        featured_cities=featured_cities,
        photo_cards=photo_cards,
    )


@app.route("/weather", methods=["GET", "POST"])
def weather_page():
    city = "Manchester"
    error = None
    weather = None
    forecast = []
    daily_summary = []

    if request.method == "POST":
        city = (request.form.get("city") or request.form.get(
            "saved_city") or "").strip()

    if city:
        if not API_KEY:
            error = "Missing API key. Set OPENWEATHER_API_KEY before starting Flask."
        else:
            try:
                coordinate_data = get_coordinates(city)
                if not coordinate_data:
                    error = "City not found. Try a more specific name."
                else:
                    lat = coordinate_data["lat"]
                    lon = coordinate_data["lon"]
                    current_data = get_current_weather(lat, lon)
                    forecast_data = get_forecast(lat, lon, count=8)
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

    return render_page(
        "Atmos · Weather",
        "weather",
        WEATHER_CONTENT,
        city=city,
        saved_cities=SAVED_CITIES,
        weather=weather,
        forecast=forecast,
        daily_summary=daily_summary,
        error=error,
    )


@app.route("/cities")
def cities_page():
    city_cards = get_city_cards(SAVED_CITIES)
    spotlight_cities = city_cards[:4]
    return render_page(
        "Atmos · Cities",
        "cities",
        CITIES_CONTENT,
        city_cards=city_cards,
        spotlight_cities=spotlight_cities,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
