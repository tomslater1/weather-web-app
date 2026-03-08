import os
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import requests
from flask import Flask, redirect, render_template, request, url_for

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

CITY_BACKGROUNDS = {
    "Manchester": "https://source.unsplash.com/1600x1000/?manchester,city,skyline&sig=11",
    "London": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1600&q=80",
    "Edinburgh": "https://images.unsplash.com/photo-1506377247377-2a5b3b417ebb?auto=format&fit=crop&w=1600&q=80",
    "Montreal": "https://images.unsplash.com/photo-1519178614-68673b201f36?auto=format&fit=crop&w=1600&q=80",
    "Dublin": "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1600&q=80",
    "New York": "https://images.unsplash.com/photo-1499092346589-b9b6be3e94b2?auto=format&fit=crop&w=1600&q=80",
    "Paris": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1600&q=80",
    "Tokyo": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=1600&q=80",
    "Barcelona": "https://images.unsplash.com/photo-1583422409516-2895a77efded?auto=format&fit=crop&w=1600&q=80",
    "Singapore": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=1600&q=80",
    "Sydney": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?auto=format&fit=crop&w=1600&q=80",
    "Dubai": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1600&q=80",
    "Amsterdam": "https://source.unsplash.com/1600x1000/?amsterdam,city,canal&sig=12",
    "Berlin": "https://source.unsplash.com/1600x1000/?berlin,city,skyline&sig=13",
    "Rome": "https://source.unsplash.com/1600x1000/?rome,city,italy&sig=14",
    "Madrid": "https://source.unsplash.com/1600x1000/?madrid,city,spain&sig=15",
    "Los Angeles": "https://source.unsplash.com/1600x1000/?los-angeles,city,skyline&sig=16",
    "Toronto": "https://source.unsplash.com/1600x1000/?toronto,city,skyline&sig=17",
    "San Francisco": "https://source.unsplash.com/1600x1000/?san-francisco,city,bridge&sig=18",
    "Hong Kong": "https://source.unsplash.com/1600x1000/?hong-kong,city,skyline&sig=19",
    "Seoul": "https://source.unsplash.com/1600x1000/?seoul,city,night&sig=20",
    "Cape Town": "https://source.unsplash.com/1600x1000/?cape-town,city,mountain&sig=21",
}

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
    if not city_name:
        return ""
    for mapped_city, image_url in CITY_BACKGROUNDS.items():
        if mapped_city.lower() == city_name.lower():
            return image_url
    query = quote_plus(f"{city_name} skyline night")
    return f"https://source.unsplash.com/1600x1000/?{query}"


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


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
