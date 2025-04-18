"""
Text-based response objects for the agent system.
"""
from typing import Dict, Any, Tuple, Optional
from src.agent.responses.base import ActionResponse


class TextResponse(ActionResponse):
    """
    Standard text response from the agent.
    """
    
    def __init__(self, message: str, status: str = "success", status_code: int = 200):
        """
        Initialize a text response.
        
        Args:
            message: The text message to return
            status: Status string (success, error, etc)
            status_code: HTTP status code
        """
        self.message = message
        self.status = status
        self.status_code = status_code
        self.content_type = "application/json"
        self.is_conversation_over = False
    
    @property
    def response_type(self) -> str:
        return "text"
    
    def to_http_response(self) -> Tuple[Dict[str, Any], int]:
        return {
            "message": self.message,
            "status": self.status,
            "content_type": self.content_type,
            "is_conversation_over": self.is_conversation_over
        }, self.status_code
    
    def to_string(self) -> str:
        return self.message
        
    def mark_conversation_over(self):
        """Mark this response as ending the conversation."""
        self.is_conversation_over = True
        return self


class ErrorResponse(TextResponse):
    """
    Error response for handling failures.
    """
    
    def __init__(self, message: str, error_detail: Optional[str] = None, status_code: int = 500):
        """
        Initialize an error response.
        
        Args:
            message: User-friendly error message
            error_detail: Technical error details (not shown to user)
            status_code: HTTP status code
        """
        super().__init__(message, status="error", status_code=status_code)
        self.error_detail = error_detail
    
    @property
    def response_type(self) -> str:
        return "error"
        
    def to_http_response(self) -> Tuple[Dict[str, Any], int]:
        response = {
            "message": self.message,
            "status": self.status,
            "content_type": self.content_type
        }
        
        if self.error_detail:
            response["error"] = self.error_detail
            
        return response, self.status_code


class DirectResponse(TextResponse):
    """
    Direct text response that bypasses the second AI call.
    """
    
    @property
    def requires_second_ai_call(self) -> bool:
        """Direct responses don't need a second AI call."""
        return False