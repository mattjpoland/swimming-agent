from datetime import datetime
from src.domain.gateways.weatherGateway import fetch_weather, fetch_weather_forecast

def get_weather_for_zip(zip_code, country_code):
    """
    Get formatted weather data for a specific ZIP code.

    Args:
        zip_code (str): ZIP code for the location.
        country_code (str): Country code (e.g., 'us').

    Returns:
        dict: Formatted weather data.
    """
    try:
        # Fetch raw weather data from the gateway
        raw_weather_data = fetch_weather(zip_code, country_code)

        # Extract and format relevant weather information
        weather = {
            "location": raw_weather_data.get("name", "Unknown Location"),
            "temperature": raw_weather_data["main"]["temp"],
            "description": raw_weather_data["weather"][0]["description"].capitalize(),
            "humidity": raw_weather_data["main"]["humidity"],
            "wind_speed": raw_weather_data["wind"]["speed"],
        }

        return weather
    except Exception as e:
        # Log and re-raise the exception for the route to handle
        raise RuntimeError(f"Failed to retrieve weather data: {str(e)}") from e

def get_weather_forecast_for_date(zip_code, country_code, target_date):
    """
    Get formatted weather forecast data for a specific future date.

    Args:
        zip_code (str): ZIP code for the location.
        country_code (str): Country code (e.g., 'us').
        target_date (str): Target date in YYYY-MM-DD format.

    Returns:
        dict: Formatted weather forecast data for the target date.
    """
    try:
        # Parse the target date
        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        
        # Check if the target date is within the forecast window (typically 5 days for free API)
        today = datetime.now().date()
        days_ahead = (target_date_obj - today).days
        
        # OpenWeatherMap free API only provides forecasts for about 5 days ahead
        if days_ahead > 5:
            return {
                "date": target_date,
                "message": f"Weather forecast not available for {target_date}. Forecasts are only available up to 5 days ahead.",
                "forecasts": []
            }
        
        # Fetch raw forecast data from the gateway
        raw_forecast_data = fetch_weather_forecast(zip_code, country_code)

        # Filter the forecast data for the target date
        forecast_list = raw_forecast_data.get("list", [])
        daily_forecast = [
            {
                "datetime": forecast["dt_txt"],
                "temperature": forecast["main"]["temp"],
                "description": forecast["weather"][0]["description"].capitalize(),
                "humidity": forecast["main"]["humidity"],
                "wind_speed": forecast["wind"]["speed"],
            }
            for forecast in forecast_list
            if datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S").date() == target_date_obj
        ]

        if not daily_forecast:
            # Return a valid response with an informational message instead of raising an error
            return {
                "date": target_date,
                "message": f"No forecast data available for {target_date}.",
                "forecasts": []
            }

        return {
            "date": target_date,
            "forecasts": daily_forecast,
        }
    except Exception as e:
        # Log and re-raise the exception for the route to handle
        raise RuntimeError(f"Failed to retrieve weather forecast data: {str(e)}") from e