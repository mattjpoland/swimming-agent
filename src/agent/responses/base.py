"""
Base response objects for consistent agent response handling.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional


class ActionResponse(ABC):
    """
    Base class for all agent response types.
    
    This provides a common interface for all responses, regardless of source,
    allowing the agent service to handle them consistently without type checking.
    """
    
    @property
    @abstractmethod
    def response_type(self) -> str:
        """The type of response, used for categorization and processing."""
        pass
    
    @property
    def requires_second_ai_call(self) -> bool:
        """
        Whether this response requires a second AI call.
        Default is True - most responses need formatting from AI.
        """
        return True
        
    @property
    def should_add_to_history(self) -> bool:
        """
        Whether this response should be added to conversation history.
        Default is True - most responses should be in history.
        """
        return True
    
    @abstractmethod
    def to_http_response(self) -> Tuple[Dict[str, Any], int]:
        """
        Convert this response to an HTTP response format.
        
        Returns:
            tuple: (response_dict, status_code)
        """
        pass
    
    @abstractmethod
    def to_string(self) -> str:
        """
        Convert this response to a string representation for AI context.
        
        Returns:
            str: String representation of the response
        """
        pass
        
    def set_metadata(self, key: str, value: Any) -> 'ActionResponse':
        """
        Set metadata on the response for additional context.
        
        Args:
            key: Metadata key
            value: Metadata value
            
        Returns:
            self: For method chaining
        """
        if not hasattr(self, '_metadata'):
            self._metadata = {}
        self._metadata[key] = value
        return self
        
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key."""
        if not hasattr(self, '_metadata'):
            return default
        return self._metadata.get(key, default)