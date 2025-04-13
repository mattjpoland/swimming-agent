from src.api.logic.weatherService import get_weather_for_zip  # Import the weather service function

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
            return {
                "message": f"The current weather in {weather['location']} is {weather['description']} with a temperature of {weather['temperature']}°F, humidity at {weather['humidity']}%, and wind speed of {weather['wind_speed']} mph.",
                "status": "success"
            }, 200
        except Exception as e:
            return {
                "message": f"Failed to fetch the current weather: {str(e)}",
                "status": "error"
            }, 500

