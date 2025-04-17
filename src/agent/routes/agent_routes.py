from flask import Blueprint, request, jsonify, g, Response
from .agent_route_service import AgentRouteService
from src.decorators import require_api_key
import logging

agent_bp = Blueprint('agent', __name__)
route_service = AgentRouteService()

@agent_bp.route('/chat', methods=['POST'])
@require_api_key
def chat():
    try:
        data = request.get_json()
        user_input = data.get('user_input')
        
        if not user_input:
            return jsonify({"error": "No user input provided"}), 400
        
        # Extract optional parameters
        response_format = data.get('response_format', 'auto')
        is_siri = data.get('is_siri', False)
        conversation_history = data.get('conversation_history', [])
        
        # Get context from Flask g if available
        context = getattr(g, 'context', {})
        
        # Log the incoming request
        logging.info(f"Processing agent request: '{user_input[:50]}{'...' if len(user_input) > 50 else ''}'")
        
        # Process the request through the service layer
        result, status_code = route_service.process_chat(
            user_input=user_input,
            context=context,
            response_format=response_format,
            is_siri=is_siri,
            conversation_history=conversation_history
        )
        
        # Check if the result is a Flask Response object
        if isinstance(result, Response):
            return result
        else:
            # Otherwise, jsonify the dictionary result
            return jsonify(result), status_code
    
    except Exception as e:
        logging.error(f"Error in agent route: {e}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": "An error occurred while processing your request",
            "content_type": "application/json"
        }), 500