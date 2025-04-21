from openai import OpenAI
import os
import json
import logging
from typing import List, Dict, Any, Optional

class OpenAIGateway:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        temperature: float = None
    ):
        """
        Raw completion call to OpenAI
        
        Args:
            messages: List of message objects for the conversation
            tools: Optional list of tool definitions for function calling
            tool_choice: How to select tools ("auto", "none", or specific tool)
            temperature: Controls randomness (lower=more deterministic)
                        If not specified, will be determined based on context:
                        - Tool selection: 0.2 (more deterministic)
                        - Chain evaluation: 0.1 (highly deterministic)
                        - Response generation: 0.7 (more creative)
                        - Default: 0.7
        """
        try:
            kwargs = {
                "model": "gpt-4.1-mini",
                "messages": messages
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice
                
            # Apply temperature logic - if not specified, determine from context
            if temperature is None:
                temperature = self._determine_temperature(messages, tools)
                
            kwargs["temperature"] = temperature

            response = self.client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            raise
            
    def _determine_temperature(self, messages: List[Dict], tools: Optional[List[Dict]]) -> float:
        """
        Intelligently determine appropriate temperature based on the request context
        
        Args:
            messages: The conversation messages
            tools: Optional tool definitions
            
        Returns:
            float: Appropriate temperature value
        """
        # If there are tools, this is likely a tool selection call
        if tools:
            return 0.2  # More deterministic for tool selection
            
        # Check if this is chain evaluation by looking at system message
        for msg in messages:
            if msg.get("role") == "system" and "agent coordinator" in msg.get("content", "").lower():
                return 0.1  # Very deterministic for tool chain evaluation
                
        # For final response formatting or direct responses
        return 0.7  # More creative for natural language responses