from src.agent.actions.availability import AvailabilityAction
from src.agent.actions.barcode import BarcodeAction
from src.agent.actions.booking import BookLaneAction
from src.agent.actions.appointments import AppointmentsAction
from src.agent.actions.cancellation import CancelAppointmentAction  # Add import
from src.agent.actions.weather import WeatherAction  # Add import
from src.agent.actions.weatherForecast import WeatherForecastAction  # Add import
from src.agent.utils.date_resolver import get_current_dates
from src.api.logic.weatherService import get_weather_for_zip, get_weather_forecast_for_date
from datetime import datetime, timedelta
import pytz


class AgentRegistry:
    def __init__(self):
        self._actions = {}
        self._register_actions()

    def _register_actions(self):
        """Register all available actions."""
        actions = [
            AvailabilityAction(),
            BarcodeAction(),
            BookLaneAction(),
            AppointmentsAction(),
            CancelAppointmentAction(),
            WeatherAction(),
            WeatherForecastAction()
        ]
        
        for action in actions:
            self._actions[action.name] = action

    def get_action(self, name):
        """Get an action by name."""
        return self._actions.get(name)

    def get_all_actions(self):
        """Get all registered actions."""
        return list(self._actions.values())

    def get_tools_for_openai(self):
        """Get the tools array for OpenAI API."""
        return [action.get_tool_definition() for action in self._actions.values()]

    def get_system_prompt(self):
        """Generate a system prompt based on registered actions."""
        # Use Eastern timezone
        eastern_tz = pytz.timezone('US/Eastern')
        now = datetime.now(eastern_tz)

        # Get today and tomorrow dates in YYYY-MM-DD format
        today_date = now.strftime("%Y-%m-%d")
        tomorrow_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        # Current day name and tomorrow's day name
        current_day_of_week = now.strftime("%A")
        tomorrow_day_of_week = (now + timedelta(days=1)).strftime("%A")

        # Start with basic information
        prompt = (
            f"You are a helpful assistant for a swimming facility. "
            f"The current date is {today_date}. "
            "You can assist users with checking swim lane availability, booking lanes, canceling appointments, "
            "and providing weather information.\n\n"
            "For weather-related queries:\n"
            "- Use the 'get_weather' action to fetch the current weather.\n"
            "- Use the 'get_weather_forecast' action to fetch the weather forecast for a specific date.\n"
            "When responding, include natural language descriptions of the weather, such as 'clear sky' or 'light rain'.\n"
        )
        
        # Calculate the dates for the next 7 days with their day names
        next_days = []
        for i in range(2, 8):  # Start from 2 because 0 is today and 1 is tomorrow
            next_day = (now + timedelta(days=i))
            next_days.append({
                "date": next_day.strftime("%Y-%m-%d"),
                "day": next_day.strftime("%A")
            })

        # Add detailed date and timezone information
        prompt += (
            f"The current date and time in Eastern Time (ET) is {now.strftime('%Y-%m-%d %H:%M %Z')}. "
            f"Today is {current_day_of_week}, {today_date}. "
            f"Tomorrow is {tomorrow_day_of_week}, {tomorrow_date}. "
        )

        # Add next days information
        prompt += "Here are the dates for the upcoming week: "
        for day_info in next_days:
            prompt += f"{day_info['day']} is {day_info['date']}, "
        prompt = prompt.rstrip(", ") + ". "

        # Add action-specific instructions
        for action in self._actions.values():
            if hasattr(action, "prompt_instructions"):
                prompt += action.prompt_instructions

        # Add any other general instructions
        prompt += "Always try to be helpful and provide clear information to the user."

        prompt += (
            "\n\nVERY IMPORTANT - CONVERSATION MANAGEMENT INSTRUCTIONS:\n"
            "For any response that doesn't call a function you must include \"is_conversation_over\" element in the response JSON.\n"
            "Follow these specific rules to determine the value of \"is_conversation_over\":\n"
            "1. If the user's message indicates they are done with the conversation or their needs are met (examples: \"thanks, that's all\", \"goodbye\", \"exit\", \"that's all I needed\", \"I'm done\", \"bye\", \"I'm all set.\", etc.), set \"is_conversation_over\" to true.\n"
            "2. For all other responses, set \"is_conversation_over\" to false.\n"
            "\n"
            "When \"is_conversation_over\" is true, make your response message brief and include a closing phrase like \"You're welcome!\" or \"Happy to help. Have a great day!\".\n"
            "\n"
        )

        # Then return the updated prompt
        return prompt

# Create a singleton instance
registry = AgentRegistry()