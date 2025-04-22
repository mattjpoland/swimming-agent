from src.agent.actions.availability import AvailabilityAction
from src.agent.actions.barcode import BarcodeAction
from src.agent.actions.booking import BookLaneAction
from src.agent.actions.appointments import AppointmentsAction
from src.agent.actions.cancellation import CancelAppointmentAction
from src.agent.actions.weather import WeatherAction
from src.agent.actions.weatherForecast import WeatherForecastAction
from src.agent.actions.information import InformationAction
from src.agent.actions.scheduling import ManageScheduleAction
from src.agent.gateways.openAIGateway import OpenAIGateway
from typing import Any, List, Dict
import logging


class AgentRegistry:
    def __init__(self):
        self._actions = {}
        self._admin_actions = {}  # New dictionary for admin-only actions
        self._register_actions()

    def _register_actions(self):
        """Register all available actions."""
        # Regular actions available to all authenticated users
        regular_actions = [
            AvailabilityAction(),
            BarcodeAction(),
            BookLaneAction(),
            AppointmentsAction(),
            CancelAppointmentAction(),
            WeatherAction(),
            WeatherForecastAction(),
            InformationAction(),
        ]
        
        # Admin-only actions
        admin_actions = [
            ManageScheduleAction()
        ]
        
        # Register regular actions
        for action in regular_actions:
            self._actions[action.name] = action
            
        # Register admin actions separately
        for action in admin_actions:
            self._admin_actions[action.name] = action

    def get_action(self, name, is_admin=False):
        """
        Get an action by name.
        Admin-only actions are only returned if is_admin is True.
        """
        # First check regular actions
        action = self._actions.get(name)
        if action:
            return action
            
        # Only check admin actions if user is an admin
        if is_admin and name in self._admin_actions:
            logging.info(f"Admin user accessing admin-only action: {name}")
            return self._admin_actions.get(name)
        elif name in self._admin_actions:
            logging.warning(f"Non-admin user attempted to access admin-only action: {name}")
            
        return None

    def get_all_actions(self, is_admin=False):
        """
        Get all registered actions.
        Admin-only actions are only included if is_admin is True.
        """
        if is_admin:
            # Combine regular and admin actions
            all_actions = list(self._actions.values()) + list(self._admin_actions.values())
            return all_actions
        else:
            # Return only regular actions
            return list(self._actions.values())

    def get_tools_for_openai(self, is_admin=False):
        """
        Get the tools array for OpenAI API.
        Admin-only tools are only included if is_admin is True.
        """
        return [action.get_tool_definition() for action in self.get_all_actions(is_admin)]

    def determine_action(self, user_input: str, is_admin: bool = False) -> Any:
        """
        Determine which action to use based on user input.
        Admin-only actions are only considered if is_admin is True.
        """
        # Get the appropriate action descriptions based on admin status
        action_descriptions = self._format_action_descriptions(is_admin)
        
        # Ask OpenAI to determine the appropriate action
        messages = [
            {"role": "system", "content": f"""
You are an action classifier for a swimming facility assistant. 
Analyze the user's input and determine which function to call:

Available functions:
{action_descriptions}

Select only ONE function name that best matches the user's intent.
Respond with ONLY the function name, nothing else.
"""},
            {"role": "user", "content": user_input}
        ]
        
        try:
            openai_gateway = OpenAIGateway()
            response = openai_gateway.get_completion(messages)
            action_name = response.choices[0].message.content.strip().lower()
            
            # Log the suggested action name for debugging
            logging.info(f"Action classifier suggested: {action_name}")
            
            # Check if the action exists in regular actions first
            action = self._actions.get(action_name)
            if action:
                return action
                
            # If not found in regular actions, check if it's potentially an admin action
            if action_name in self._admin_actions and not is_admin:
                # This is an admin-only action but the user is not an admin
                logging.warning(f"Non-admin user attempted to access admin-only action: {action_name}")
                
                # Return the information action with a special flag to inform the user about permission
                info_action = self._actions.get("get_pool_information")
                if hasattr(info_action, "set_admin_action_attempted"):
                    info_action.set_admin_action_attempted(action_name)
                return info_action
                
            # If user is admin, check admin actions
            if is_admin:
                admin_action = self._admin_actions.get(action_name)
                if admin_action:
                    return admin_action
            
            # Default to information action if no match
            return self._actions.get("get_pool_information")
            
        except Exception as e:
            # Log error and default to information action
            logging.error(f"Error determining action: {e}")
            return self._actions.get("get_pool_information")
    
    def _format_action_descriptions(self, is_admin: bool = False) -> str:
        """
        Format all registered actions and their descriptions for the classifier.
        Admin-only action descriptions are only included if is_admin is True.
        """
        descriptions = []
        for action in self.get_all_actions(is_admin):
            descriptions.append(f"- {action.name}: {action.description}")
        return "\n".join(descriptions)


# Create a singleton instance
registry = AgentRegistry()