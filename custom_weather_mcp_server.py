# pip install mcp requests python-dotenv

import os
import logging

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not OPENWEATHER_API_KEY:
    raise RuntimeError(
        "OPENWEATHER_API_KEY is not set. Add it to your .env file before "
        "starting the weather MCP server."
    )

REQUEST_TIMEOUT = 10  # seconds

mcp = FastMCP("Weather Server")


@mcp.tool()
def get_current_weather(city: str):
    """Return current weather for a city, or an error dict on failure."""
    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.exception("Weather request failed for city=%s", city)
        return {"error": f"Request to OpenWeather failed: {exc}"}

    data = response.json()

    if response.status_code != 200:
        return {
            "error": data.get("message", "Unknown error from OpenWeather"),
            "status_code": response.status_code,
        }

    try:
        return {
            "city": data["name"],
            "temperature_c": data["main"]["temp"],
            "feels_like_c": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
        }
    except (KeyError, IndexError) as exc:
        logger.exception("Unexpected OpenWeather response shape")
        return {"error": f"Unexpected response format from OpenWeather: {exc}"}


@mcp.tool()
def get_forecast(city: str):
    """Return the next 5 forecast entries for a city, or an error dict."""
    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={
                "q": city,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.exception("Forecast request failed for city=%s", city)
        return {"error": f"Request to OpenWeather failed: {exc}"}

    data = response.json()

    if response.status_code != 200:
        return {
            "error": data.get("message", "Unknown error from OpenWeather"),
            "status_code": response.status_code,
        }

    forecast = []
    for item in data.get("list", [])[:5]:
        try:
            forecast.append(
                {
                    "datetime": item["dt_txt"],
                    "temperature": item["main"]["temp"],
                    "weather": item["weather"][0]["description"],
                }
            )
        except (KeyError, IndexError):
            #here we Skip a malformed entry rather than failing the whole call
            continue

    if not forecast:
        return {"error": "No forecast data returned for this city", "city": city}

    return {
        "city": city,
        "forecast": forecast,
    }


if __name__ == "__main__":
    mcp.run()