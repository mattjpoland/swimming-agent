from flask import Blueprint, request, jsonify, g, Response
from src.agent.services.agentService import AgentService
from src.decorators import require_api_key
import logging
import os
import json
import uuid

agent_bp = Blueprint('agent', __name__)
agent_service = AgentService()

@agent_bp.route('/chat', methods=['POST'])
@require_api_key
def chat():
    try:
        data = request.get_json()
        user_input = data.get('user_input')
        
        # Log raw request body if REQUEST_LOGGING is enabled
        if os.getenv('REQUEST_LOGGING', 'false').lower() == 'true' or g.context.get('REQUEST_LOGGING', False):
            logging.info(f"RAW REQUEST: {json.dumps(data)}")
        
        if not user_input:
            return jsonify({"error": "No user input provided"}), 400
        
        # Extract optional parameters
        response_format = data.get('response_format', 'auto')
        
        # Get session_id or generate a new one
        session_id = data.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            logging.info(f"Generated new session ID: {session_id}")
        
        # Get context from Flask g if available
        context = getattr(g, 'context', {})
        
        # Log the incoming request
        logging.info(f"Processing agent request: '{user_input[:50]}{'...' if len(user_input) > 50 else ''}' with session ID: {session_id}")
        
        # Process the request through the service layer
        result, status_code = agent_service.process_chat(
            user_input=user_input,
            context=context,
            response_format=response_format,
            session_id=session_id
        )
        
        # Prepare and log response safely
        if os.getenv('REQUEST_LOGGING', 'false').lower() == 'true' or g.context.get('REQUEST_LOGGING', False):
            # Handle different response types for logging
            if isinstance(result, Response):
                # Safely log Response objects without trying to access content
                logging.info(f"RAW RESPONSE: [Flask Response Object] Content-Type: {result.content_type}, Status: {status_code}")
            elif isinstance(result, dict):
                # For dictionaries, we can safely log the JSON
                response_dict = result.copy()
                logging.info(f"RAW RESPONSE: {json.dumps(response_dict)}")
            else:
                # For other types just convert to string
                logging.info(f"RAW RESPONSE: {str(result)}")
        
        # Check if the result is a Flask Response object
        if isinstance(result, Response):
            response = result
        else:
            # Add session_id to the response
            if isinstance(result, dict):
                logging.info(f"Adding session_id {session_id} to response dict")
                result['session_id'] = session_id
                logging.info(f"Response dict after adding session_id: {result}")
            else:
                logging.warning(f"Result is not a dict, it's a {type(result)}: {result}")
            
            # Otherwise, jsonify the dictionary result
            response = jsonify(result)
            logging.info(f"Final response object: {response}")
        
        # Return the response
        return response, status_code
    
    except Exception as e:
        logging.error(f"Error in agent route: {e}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": "An error occurred while processing your request",
            "content_type": "application/json"
        }), 500