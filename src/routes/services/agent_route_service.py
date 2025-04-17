from typing import Dict, Any, List, Tuple
from src.agent.registry import registry
from src.agent.logic.agentService import AgentService
import logging

class AgentRouteService:
    def __init__(self):
        self.agent_service = AgentService()

    def process_chat(self, user_input: str, context: Dict[str, Any] = None, 
                    response_format: str = "auto", is_siri: bool = False,
                    conversation_history: List[Dict] = None) -> Tuple[Dict, int]:
        """
        Process a chat request through the complete agent pipeline:
        REQUEST > SERVER > AGENT_ROUTE > AGENT_ROUTE_SERVICE > OPEN_AI_GATEWAY > AI > 
        TOOL_INSTRUCTION > REGISTRY > ACTIONS > TOOL_RESPONSE > AI > FINAL_RESPONSE > HTTP RESPONSE
        """
        try:
            # Use the AgentService to handle the complete flow
            response, status_code = self.agent_service.process_agent_request(
                user_input=user_input,
                response_format=response_format,
                is_siri=is_siri,
                conversation_history=conversation_history or []
            )
            
            # Log the action that was used
            if status_code == 200 and '_debug' in response:
                logging.info(f"Used action: {response['_debug'].get('action', 'unknown')}")
            
            return response, status_code
            
        except Exception as e:
            logging.error(f"Error in route service: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "Failed to process request",
                "content_type": "application/json"
            }, 500