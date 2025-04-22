"""
Text-based response objects for the agent system.
"""
from typing import Dict, Any, Tuple, Optional
import json
import logging
from src.agent.responses.base import ActionResponse


class TextResponse(ActionResponse):
    """
    Standard text response from the agent.
    """
    
    def __init__(self, message: str, status: str = "success", status_code: int = 200, 
                is_conversation_over: bool = False):
        """
        Initialize a text response.
        
        Args:
            message: The text message to return
            status: Status string (success, error, etc)
            status_code: HTTP status code
            is_conversation_over: Flag indicating if the conversation should end
        """
        self.message = message
        self.status = status
        self.status_code = status_code
        self.content_type = "application/json"
        self.is_conversation_over = is_conversation_over
    
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
    
    This class specifically handles responses when no tool is selected,
    and parses the JSON format with "is_conversation_over" and "message" fields.
    """
    
    def __init__(self, content: str):
        """
        Initialize a direct response, parsing JSON if present.
        
        Args:
            content: The response content, potentially in JSON format
        """
        self.original_content = content
        parsed_conversation_over = False
        
        # Log the raw content for debugging
        logging.debug(f"DirectResponse raw content: {content}")
        
        # Try to parse JSON format if present
        message = content
        if content and content.strip().startswith('{') and content.strip().endswith('}'):
            try:
                parsed_json = json.loads(content)
                
                if isinstance(parsed_json, dict):
                    if 'message' in parsed_json:
                        message = parsed_json.get('message')
                        logging.debug(f"Extracted message from JSON: {message}")
                    
                    if 'is_conversation_over' in parsed_json:
                        parsed_conversation_over = bool(parsed_json.get('is_conversation_over'))
                        logging.info(f"Set conversation_over flag to: {parsed_conversation_over}")
                    else:
                        logging.warning("JSON missing 'is_conversation_over' field")
            except json.JSONDecodeError as e:
                logging.warning(f"Failed to parse direct response as JSON: {e}")
                # Log the problematic content for debugging
                logging.warning(f"Problem content: {content}")
        else:
            logging.debug("Direct response content is not in JSON format")
        
        # IMPORTANT: Pass the parsed conversation flag to the parent constructor
        # This ensures it won't get overwritten by the default False value
        super().__init__(message, is_conversation_over=parsed_conversation_over)
        
        # Log to confirm the final state after parent initialization 
        logging.info(f"DirectResponse final conversation_over state: {self.is_conversation_over}")
        
    @property
    def requires_second_ai_call(self) -> bool:
        """Direct responses don't need a second AI call."""
        return False
        
    def to_http_response(self) -> Tuple[Dict[str, Any], int]:
        """Override to include is_conversation_over flag"""
        response = {
            "message": self.message,
            "status": self.status,
            "content_type": self.content_type,
            "is_conversation_over": self.is_conversation_over
        }
        
        # Log the final response for debugging
        logging.debug(f"DirectResponse final HTTP response: {response}")
        
        return response, self.status_code