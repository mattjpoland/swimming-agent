from src.domain.services.weatherService import get_weather_forecast_for_date  # Import the weather forecast service function
from flask import jsonify  # Import Flask jsonify for standardized responses
from datetime import datetime, timedelta  # Import datetime and timedelta for date calculations

class WeatherForecastAction:
    @property
    def name(self):
        return "get_weather_forecast"

    @property
    def description(self):
        return "Fetch the weather forecast for a specific date."

    @property
    def parameters(self):
        today = datetime.now()
        tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The date for the weather forecast in YYYY-MM-DD format.",
                    "default": tomorrow
                }
            },
            "required": []
        }

    @property
    def prompt_instructions(self):
        return (
            "You can provide the weather forecast for a specific date. "
            "When a user asks about weather for any future time period or date - including simple queries like 'Tomorrow?' - use the get_weather_forecast function. "
            "For the date parameter, convert relative time references (tomorrow, next Monday, etc.) to YYYY-MM-DD format based on the current date in Eastern Time. "
            "When the user follows up a weather query with a time reference, always interpret this as a request for a forecast rather than current conditions."
        )
        
    @property
    def response_format_instructions(self):
        return (
            "Format your response from a swimmer's perspective - focusing on how the forecast conditions will feel "
            "to someone planning to use an outdoor pool. Consider:\n"
            "1. How the predicted temperatures and wind will feel on wet skin when getting out of the water\n"
            "2. The best times during the day for comfortable swimming\n"
            "Make your response practical and specifically relevant for swimmers planning pool visits.\n"
            "Try to keep it to no more than 3 sentences."
        )

    def get_tool_definition(self):
        return {
            "type": "function",  # Add this line
            "function": {        # Wrap in function object
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def execute(self, arguments, context, user_input, **kwargs):
        try:
            zip_code = "48823"
            country_code = "us"
            target_date = arguments.get("date")
            forecast = get_weather_forecast_for_date(zip_code, country_code, target_date)

            forecast_message = f"The weather forecast for {forecast['date']} includes:\n"
            for entry in forecast["forecasts"]:
                forecast_message += (
                    f"- At {entry['datetime']}, expect {entry['description']} with a temperature of {entry['temperature']}°F, "
                    f"humidity at {entry['humidity']}%, and wind speed of {entry['wind_speed']} mph.\n"
                )

            return jsonify({"message": forecast_message.strip(), "status": "success"}), 200
        except Exception as e:
            return jsonify({"message": f"Failed to fetch the weather forecast: {str(e)}", "status": "error"}), 500

