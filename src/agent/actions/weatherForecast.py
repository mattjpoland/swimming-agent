from src.domain.services.weatherService import get_weather_forecast_for_date  # Import the weather forecast service function
from flask import jsonify  # Import Flask jsonify for standardized responses

class WeatherForecastAction:
    @property
    def name(self):
        return "get_weather_forecast"

    @property
    def description(self):
        return "Fetch the weather forecast for a specific date."

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The date for the weather forecast in YYYY-MM-DD format."
                }
            },
            "required": ["date"]
        }

    @property
    def prompt_instructions(self):
        return (
            "You can provide the weather forecast for a specific date. "
            "When a user asks for the weather forecast, use the get_weather_forecast function. "
            "They need to specify the date in YYYY-MM-DD format. "
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

