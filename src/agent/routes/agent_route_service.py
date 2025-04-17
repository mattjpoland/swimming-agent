from typing import Dict, Any, List, Tuple, Union
from flask import Response
from src.agent.registry import registry
from src.agent.services.agentService import AgentService
import logging

class AgentRouteService:
    def __init__(self):
        self.agent_service = AgentService()

    def process_chat(self, user_input: str, context: Dict[str, Any] = None, 
                    response_format: str = "auto", is_siri: bool = False,
                    conversation_history: List[Dict] = None) -> Tuple[Union[Dict, Response], int]:
        """
        Process a chat request through the complete agent pipeline:
        REQUEST > SERVER > AGENT_ROUTE > AGENT_ROUTE_SERVICE > OPEN_AI_GATEWAY > AI > 
        TOOL_INSTRUCTION > REGISTRY > ACTIONS > TOOL_RESPONSE > AI > FINAL_RESPONSE > HTTP RESPONSE
        """
        try:
            # Use the AgentService to handle the complete flow
            response = self.agent_service.process_agent_request(
                user_input=user_input,
                context=context or {},
                response_format=response_format,
                is_siri=is_siri,
                conversation_history=conversation_history or []
            )
            
            # Handle different response types
            if isinstance(response, tuple):
                # Response already has a status code
                result, status_code = response
            elif isinstance(response, Response):
                # Flask Response object - return as is
                return response, 200
            else:
                # Regular dictionary response
                result = response
                status_code = 200
            
            # Log action used if available in dictionary response
            if isinstance(result, dict) and '_debug' in result:
                logging.info(f"Used action: {result['_debug'].get('action', 'unknown')}")
            
            return result, status_code
            
        except Exception as e:
            logging.error(f"Error in route service: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "Failed to process request",
                "content_type": "application/json"
            }, 500