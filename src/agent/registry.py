from src.agent.actions.availability import AvailabilityAction
from src.agent.actions.barcode import BarcodeAction
from src.agent.actions.booking import BookLaneAction
from src.agent.actions.appointments import AppointmentsAction
from src.agent.actions.cancellation import CancelAppointmentAction
from src.agent.actions.weather import WeatherAction
from src.agent.actions.weatherForecast import WeatherForecastAction
from src.agent.actions.information import InformationAction
from src.agent.gateways.openAIGateway import OpenAIGateway
from typing import Any, List, Dict
import logging


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
            WeatherForecastAction(),
            InformationAction()
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

    def determine_action(self, user_input: str) -> Any:
        """Determine which action to use based on user input"""
        # Ask OpenAI to determine the appropriate action
        messages = [
            {"role": "system", "content": f"""
You are an action classifier for a swimming facility assistant. 
Analyze the user's input and determine which function to call:

Available functions:
{self._format_action_descriptions()}

Select only ONE function name that best matches the user's intent.
Respond with ONLY the function name, nothing else.
"""},
            {"role": "user", "content": user_input}
        ]
        
        try:
            openai_gateway = OpenAIGateway()
            response = openai_gateway.get_completion(messages)
            action_name = response.choices[0].message.content.strip().lower()
            
            # Try to get the action by name
            for action in self.get_all_actions():
                if action.name.lower() == action_name:
                    return action
            
            # Default to information action if no match
            return self.get_action("get_pool_information")
            
        except Exception as e:
            # Log error and default to information action
            logging.error(f"Error determining action: {e}")
            return self.get_action("get_pool_information")
    
    def _format_action_descriptions(self) -> str:
        """Format all registered actions and their descriptions for the classifier"""
        descriptions = []
        for action in self.get_all_actions():
            descriptions.append(f"- {action.name}: {action.description}")
        return "\n".join(descriptions)


# Create a singleton instance
registry = AgentRegistry()