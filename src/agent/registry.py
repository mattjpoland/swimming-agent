from src.agent.actions.availability import AvailabilityAction
from src.agent.actions.barcode import BarcodeAction
from src.agent.utils.date_resolver import get_current_dates

class AgentRegistry:
    def __init__(self):
        self._actions = {}
        self._register_actions()
    
    def _register_actions(self):
        """Register all available actions."""
        # Add more actions here as they are created
        actions = [
            AvailabilityAction(),
            BarcodeAction()
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
        # Get detailed date information with day of week and timezone
        from datetime import datetime, timedelta
        import pytz
        
        # Use Eastern timezone
        eastern_tz = pytz.timezone('US/Eastern')
        now = datetime.now(eastern_tz)
        
        current_date = now.strftime("%Y-%m-%d")
        current_day_of_week = now.strftime("%A")
        tomorrow = (now + timedelta(days=1))
        tomorrow_date = tomorrow.strftime("%Y-%m-%d")
        tomorrow_day_of_week = tomorrow.strftime("%A")
        
        # Calculate the dates for the next 7 days with their day names
        next_days = []
        for i in range(2, 8):  # Start from 2 because 0 is today and 1 is tomorrow
            next_day = (now + timedelta(days=i))
            next_days.append({
                "date": next_day.strftime("%Y-%m-%d"),
                "day": next_day.strftime("%A")
            })
        
        # Start with basic information including detailed date and timezone
        prompt = (
            f"You are a helpful assistant for a swimming facility. "
            f"The current date and time in Eastern Time (ET) is {now.strftime('%Y-%m-%d %H:%M %Z')}. "
            f"Today is {current_day_of_week}, {current_date}. "
            f"Tomorrow is {tomorrow_day_of_week}, {tomorrow_date}. "
        )
        
        # Add next days information
        prompt += "Here are the dates for the upcoming week: "
        for day_info in next_days:
            prompt += f"{day_info['day']} is {day_info['date']}, "
        prompt = prompt.rstrip(", ") + ". "
        
        # Add information about each action
        if "check_lane_availability" in self._actions:
            prompt += (
                "You can help with checking pool availability. "
                "Use the check_lane_availability function when asked about pool availability. "
                "If the user doesn't specify which pool, assume they want to check 'Both Pools'. "
                "For date parameters, use the YYYY-MM-DD format. "
                "When calculating dates from day names (like 'Sunday' or 'Monday'), always refer to the date information provided above. "
            )
        
        if "get_membership_barcode" in self._actions:
            prompt += (
                "If the user asks for their membership barcode or anything related to "
                "accessing the facility with their membership, use the get_membership_barcode function. "
            )
            
        # Add any other general instructions
        prompt += "Always try to be helpful and provide clear information to the user."
        
        return prompt

# Create a singleton instance
registry = AgentRegistry()