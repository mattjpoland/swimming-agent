"""
Tool-related response classes for the agent system.
"""
from typing import Dict, Any, Tuple, Optional, List
from src.agent.responses.base import ActionResponse


class ToolSelectionResponse(ActionResponse):
    """
    Response representing the selection of a tool by the AI.
    """
    
    def __init__(self, tool_call, messages: List[Dict[str, Any]], user_input: str):
        """
        Initialize a tool selection response.
        
        Args:
            tool_call: The OpenAI tool call object
            messages: Current conversation messages
            user_input: Original user input that triggered this tool
        """
        self.tool_call = tool_call
        self.function_name = tool_call.function.name
        self.arguments = tool_call.function.arguments
        self.messages = messages
        self.user_input = user_input
    
    @property
    def response_type(self) -> str:
        return "tool_selection"
    
    def to_http_response(self) -> Tuple[Dict[str, Any], int]:
        # This shouldn't be returned directly to HTTP
        raise NotImplementedError("ToolSelectionResponse cannot be converted directly to HTTP")
    
    def to_string(self) -> str:
        return f"Tool Selected: {self.function_name} with args: {self.arguments}"


class ToolExecutionResponse(ActionResponse):
    """
    Response representing the result of a tool execution.
    """
    
    def __init__(self, tool_call, action, result, messages: List[Dict[str, Any]]):
        """
        Initialize a tool execution response.
        
        Args:
            tool_call: The OpenAI tool call object
            action: The action that was executed
            result: The result from executing the action
            messages: Current conversation messages
        """
        self.tool_call = tool_call
        self.action = action
        self.result = result
        self.messages = messages
        
    @property
    def response_type(self) -> str:
        return "tool_execution"
        
    @property
    def requires_second_ai_call(self) -> bool:
        """
        Tool execution responses typically require a second AI call
        to formulate a natural language response from the tool result.
        """
        return True
    
    def to_http_response(self) -> Tuple[Dict[str, Any], int]:
        # This shouldn't be returned directly to HTTP
        raise NotImplementedError("ToolExecutionResponse cannot be converted directly to HTTP")
    
    def to_string(self) -> str:
        if hasattr(self.result, 'get_data') and callable(self.result.get_data):
            # Handle Flask Response objects
            try:
                return str(self.result.get_data(as_text=True))
            except:
                return f"[Binary response from {self.action.name}]"
        return str(self.result)