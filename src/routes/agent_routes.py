from flask import Blueprint, request, jsonify, g
from src.agent.logic.agentService import AgentService
from src.decorators import require_api_key

# Define the Flask Blueprint
agent_bp = Blueprint("agent", __name__)
agent_service = AgentService()

@agent_bp.route("/chat", methods=["POST"])
@require_api_key
def handle_agent_request():
    """
    Handle agent requests by processing the user input and integrating GPT-4 function calling.
    Returns appropriate responses based on the action type (visualization, barcode, text).
    """
    # Parse JSON body
    data = request.get_json()
    if not data or "user_input" not in data:
        return jsonify({"error": "User input is required"}), 400

    # Extract request parameters
    user_input = data["user_input"]
    response_format = data.get("response_format", "auto")
    is_siri = data.get("is_siri", False)
    conversation_history = data.get("conversation_history", [])
    
    # Delegate to service layer
    response, status_code = agent_service.process_agent_request(
        user_input=user_input,
        response_format=response_format,
        is_siri=is_siri,
        conversation_history=conversation_history
    )
    
    # Handle special response types (like images)
    from flask import Response
    if isinstance(response, Response):
        return response, status_code
        
    return jsonify(response), status_code