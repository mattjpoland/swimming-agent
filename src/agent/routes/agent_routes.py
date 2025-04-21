from flask import Blueprint, request, jsonify, g, Response
from src.agent.services.agentService import AgentService
from src.decorators import require_api_key
import logging
import os
import json

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
        
        # Standardize conversation history format
        conversation_history = standardize_conversation_history(data.get('conversation_history', []))
        
        # Get context from Flask g if available
        context = getattr(g, 'context', {})
        
        # Log the incoming request
        logging.info(f"Processing agent request: '{user_input[:50]}{'...' if len(user_input) > 50 else ''}'")
        
        # Process the request through the service layer directly
        result, status_code, updated_history = agent_service.process_chat(
            user_input=user_input,
            context=context,
            response_format=response_format,
            conversation_history=conversation_history
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
                if 'conversation_history' in response_dict:
                    response_dict['conversation_history'] = f"[{len(response_dict.get('conversation_history', []))} items]"
                logging.info(f"RAW RESPONSE: {json.dumps(response_dict)}")
            else:
                # For other types just convert to string
                logging.info(f"RAW RESPONSE: {str(result)}")
        
        # Check if the result is a Flask Response object
        if isinstance(result, Response):
            response = result
        else:
            # Add conversation_history to the response
            if isinstance(result, dict):
                result['conversation_history'] = updated_history
            
            # Otherwise, jsonify the dictionary result
            response = jsonify(result)
        
        # Return the response
        return response, status_code
    
    except Exception as e:
        logging.error(f"Error in agent route: {e}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": "An error occurred while processing your request",
            "content_type": "application/json"
        }), 500

def standardize_conversation_history(conversation_history):
    """
    Standardizes conversation history to always be an array of message objects.
    Handles different input formats from various clients.
    
    Args:
        conversation_history: The conversation history from the request, could be:
            - None
            - Empty string
            - JSON string (from iOS Shortcuts)
            - Newline-delimited JSON strings (from iOS Shortcuts)
            - Array of message objects
            - Single message object
            
    Returns:
        List: A standardized array of message objects
    """
    # Handle None or empty values
    if not conversation_history:
        return []
        
    # Handle string input (common from iOS Shortcuts)
    if isinstance(conversation_history, str):
        # Empty string
        if not conversation_history.strip():
            return []
            
        # Check for newline-delimited JSON objects from iOS Shortcuts
        if '\n' in conversation_history and conversation_history.strip().startswith('{'):
            try:
                result = []
                # Split by newlines and parse each JSON object
                for line in conversation_history.strip().split('\n'):
                    if line.strip():  # Skip empty lines
                        obj = json.loads(line.strip())
                        if isinstance(obj, dict) and ('content' in obj or 'role' in obj):
                            result.append(obj)
                
                if result:
                    logging.info(f"Successfully parsed {len(result)} message(s) from newline-delimited JSON")
                    return result
            except json.JSONDecodeError as e:
                logging.warning(f"Failed to parse newline-delimited JSON: {str(e)}")
                # Continue to try other parsing methods
        
        # Try to parse as single JSON object or array
        try:
            parsed = json.loads(conversation_history)
            # Single message object
            if isinstance(parsed, dict) and ('content' in parsed or 'role' in parsed):
                return [parsed]
            # Array of messages
            elif isinstance(parsed, list):
                return parsed
            # Unknown format
            else:
                logging.warning(f"Unrecognized JSON format for conversation history: {conversation_history}")
                return []
        except json.JSONDecodeError:
            logging.warning(f"Failed to parse conversation history as JSON: {conversation_history}")
            return []
    
    # Handle dict input (single message)
    if isinstance(conversation_history, dict) and ('content' in conversation_history or 'role' in conversation_history):
        return [conversation_history]
        
    # Handle list input (already correct format)
    if isinstance(conversation_history, list):
        return conversation_history
        
    # Fallback for unexpected types
    logging.warning(f"Unexpected conversation_history type: {type(conversation_history)}")
    return []