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
        tool_choice: str = "auto"
    ):
        """Raw completion call to OpenAI"""
        try:
            kwargs = {
                "model": "gpt-4.1-mini",
                "messages": messages
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice

            response = self.client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            raise