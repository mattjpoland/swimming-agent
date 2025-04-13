import os
import requests
import logging

def fetch_weather(zip_code, country_code):
    """
    Fetch weather data from OpenWeatherMap API.

    Args:
        zip_code (str): ZIP code for the location.
        country_code (str): Country code (e.g., 'us').

    Returns:
        dict: Parsed JSON response from the API.
    """
    # Get the API key from environment variables
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        raise RuntimeError("OpenWeatherMap API key is not set in environment variables.")

    # Construct the API URL
    url = f"http://api.openweathermap.org/data/2.5/weather?zip={zip_code},{country_code}&appid={api_key}&units=imperial"
    
    try:
        # Make the API request
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.exception(f"Error fetching weather data: {str(e)}")
        raise

def fetch_weather_forecast(zip_code, country_code):
    """
    Fetch weather forecast data from OpenWeatherMap API.

    Args:
        zip_code (str): ZIP code for the location.
        country_code (str): Country code (e.g., 'us').

    Returns:
        dict: Parsed JSON response from the API.
    """
    # Get the API key from environment variables
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        raise RuntimeError("OpenWeatherMap API key is not set in environment variables.")

    # Construct the API URL for the 5-day/3-hour forecast
    url = f"http://api.openweathermap.org/data/2.5/forecast?zip={zip_code},{country_code}&appid={api_key}&units=imperial"
    
    try:
        # Make the API request
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.exception(f"Error fetching weather forecast data: {str(e)}")
        raise