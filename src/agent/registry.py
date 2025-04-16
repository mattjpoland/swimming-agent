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
            "When responding to the user after checking appointments, always include the specific appointment details "
            "such as dates, times, and lane information from the data. Do not just acknowledge appointments exist without "
            "listing them. Always show the complete list of appointments contained in the response if any are found.  "
            "Make sure to use humanized dates formats."
            "Instead of 'MM/DD/YYYY' use: 'today', 'tomorrow', 'yesterday' when appropriate; 'Monday', 'next Tuesday', etc. for dates within a week or so; 'the 5th', 'May 5th' if slightly farther out;"
        )

        prompt += (
            "When responding to the user after checking appointments, you MUST only list the exact appointments provided "
            "in the tool response. DO NOT invent or generate any fictional appointments. If the tool response says "
            "there are 4 appointments on specific dates, you must list exactly those 4 appointments with their correct "
            "details (dates, times, lanes, duration)."
        )

        prompt += (
            "\n\nVERY IMPORTANT - CONVERSATION MANAGEMENT INSTRUCTIONS:\n"
            "Always format your response as a JSON object with these fields:\n"
            "{\n"
            "  \"is_conversation_over\": boolean,\n"
            "  \"message\": \"Your natural language response here\"\n"
            "}\n\n"
            "Follow these specific rules to determine the value of \"is_conversation_over\":\n"
            "1. Set to true only when user indicates they're finished (thanks, bye, that's all).\n"
            "2. For all other responses, set to false.\n"
            "\n"
            "For appointment listings, format them clearly with dates, times, and lane information in the message field:\n"
            "- On Thursday at 6:00 PM you have Indoor lane 3 for 30 minutes.\n"
            "- On Saturday at 8:00 AM you have Outdoor lane 1 for 60 minutes.\n"
            "Do not mention the 'Michigan Athletic Club' because its already implied.\n"
        )

        # Then return the updated prompt
        return prompt

# Create a singleton instance
registry = AgentRegistry()