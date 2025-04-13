from abc import ABC, abstractmethod
from flask import jsonify

class AgentAction(ABC):
    """Base class for all agent actions."""
    
    @property
    @abstractmethod
    def name(self):
        """The name of the action, used in the function call."""
        pass
    
    @property
    @abstractmethod
    def description(self):
        """Description of what the action does."""
        pass
    
    @property
    @abstractmethod
    def parameters(self):
        """Parameters schema for the action."""
        pass
    

    @property
    @abstractmethod
    def prompt_instructions(self):
        """Prompt instructions for the Open AI API."""
        pass

    @abstractmethod
    def execute(self, arguments, context, user_input, **kwargs):
        """
        Execute the action with the given arguments.
        
        Args:
            arguments (dict): The arguments parsed from the function call
            context (dict): The context from g.context
            user_input (str): The original user input
            **kwargs: Additional keyword arguments
            
        Returns:
            tuple: (response, status_code)
        """
        pass
        
    def get_tool_definition(self):
        """Return the tool definition for OpenAI API."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def handle_error(self, error, friendly_message=None):
        """Handle exceptions in a consistent way."""
        import logging
        logging.error(f"Error in {self.name} action: {str(error)}")
        if friendly_message is None:
            friendly_message = f"I encountered an error while processing your request. Please try again later."
        return jsonify({"message": friendly_message, "status": "error"}), 500