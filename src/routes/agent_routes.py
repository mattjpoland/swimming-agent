from flask import Blueprint, request, jsonify, g
from openai import OpenAI
import os
import json
import logging
from src.decorators import require_api_key
from src.agent.registry import registry

# Define the Flask Blueprint
agent_bp = Blueprint("agent", __name__)

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    user_input = data["user_input"]
    response_format = data.get("response_format", "auto")  # Allow client to request specific format

    # Get tools and system prompt from registry
    tools = registry.get_tools_for_openai()
    system_prompt = registry.get_system_prompt()

    # Call GPT-4 with the user input and function definition
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            tools=tools,
            tool_choice="auto"
        )
    except Exception as e:
        return jsonify({"error": f"Error communicating with OpenAI: {str(e)}"}), 500

    # Check if GPT returned a tool call
    message = response.choices[0].message
    tool_calls = message.tool_calls

    if tool_calls:
        # Get the first tool call
        tool_call = tool_calls[0]
        function_name = tool_call.function.name
        
        # Get the corresponding action
        action = registry.get_action(function_name)
        
        if action:
            # Parse the arguments from JSON string
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                return jsonify({"error": "Failed to parse function arguments"}), 500
            
            # Execute the action
            return action.execute(
                arguments=arguments,
                context=g.context,
                user_input=user_input,
                response_format=response_format
            )
        else:
            return jsonify({"error": f"Unknown function: {function_name}"}), 400

    # If no tool calls or not a recognized action, return GPT's text response
    return jsonify({"message": message.content, "status": "success"})