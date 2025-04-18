from src.domain.services.weatherService import get_weather_for_zip  # Import the weather service function
from flask import jsonify  # Import Flask jsonify for standardized responses

class WeatherAction:
    @property
    def name(self):
        return "get_weather"

    @property
    def description(self):
        return "Fetch the current weather for the facility's location."

    @property
    def parameters(self):
        return {}

    @property
    def prompt_instructions(self):
        return (
            "You can provide the current weather for the facility's location. "
            "When a user asks about the weather, use the get_weather function. "
        )
        
    @property
    def response_format_instructions(self):
        return (
            "Format your response from a swimmer's perspective - focusing on how the weather will feel to someone "
            "in a swimsuit about to use an outdoor pool. Consider:\n"
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
            weather = get_weather_for_zip(zip_code, country_code)
            return jsonify({
                "message": f"The current weather in {weather['location']} is {weather['description']} with a temperature of {weather['temperature']}°F, humidity at {weather['humidity']}%, and wind speed of {weather['wind_speed']} mph.",
                "status": "success"
            }), 200
        except Exception as e:
            return jsonify({
                "message": f"Failed to fetch the current weather: {str(e)}",
                "status": "error"
            }), 500

