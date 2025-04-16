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
#openai.verify_ssl(os.getenv("OPENAI_API_SSL_VERIFY", "true") == "true")

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
    response_format = data.get("response_format", "auto")
    is_siri = data.get("is_siri", False)
    
    # Get conversation history (if provided)
    conversation_history = data.get("conversation_history", [])
    
    # Build messages array with history
    system_prompt = registry.get_system_prompt()
    if is_siri:
        system_prompt += " Since your response will be read aloud by Siri, keep answers brief, clear, and suitable for voice."
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    for message in conversation_history:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role in ["user", "assistant"] and content:
            messages.append({"role": role, "content": content})
    
    # Add the current user message
    messages.append({"role": "user", "content": user_input})
    
    # Get tools from registry
    tools = registry.get_tools_for_openai()

    # Call GPT-4 with the messages and tools
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
    except Exception as e:
        return jsonify({
            "message": "I'm sorry, I encountered a problem while processing your request.", 
            "status": "error",
            "error": str(e),
            "content_type": "application/json"
        }), 500

    # Check if GPT returned a tool call
    message = response.choices[0].message
    tool_calls = message.tool_calls

    if tool_calls:
        # Get the first tool call
        tool_call = tool_calls[0]
        function_name = tool_call.function.name
        
        # Log the function call for debugging
        logging.info(f"Function call: {function_name} with arguments: {tool_call.function.arguments}")
        
        # Get the corresponding action
        action = registry.get_action(function_name)
        
        if action:
            # Parse the arguments from JSON string
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                return jsonify({
                    "message": "I couldn't understand how to process your request.",
                    "status": "error",
                    "content_type": "application/json"
                }), 500
            
            # Execute the action and get the response
            action_response = action.execute(
                arguments=arguments,
                context=g.context,
                user_input=user_input,
                response_format=response_format,
                is_siri=is_siri
            )
            
            # Special handling for availability with Siri
            if is_siri and function_name == "check_lane_availability":
                # Only intercept streamed responses for Siri
                from flask import Response
                if isinstance(action_response, tuple) and len(action_response) == 2:
                    resp, status = action_response
                    if isinstance(resp, Response) and resp.is_streamed:
                        # Convert to Siri-friendly response
                        return jsonify({
                            "message": "I've checked the lane availability. There are various times available. For a detailed schedule, please check on your device.",
                            "status": "success",
                            "content_type": "application/json"
                        })
            
            # Return the action response as-is
            # This preserves the original behavior for all responses including streamed HTML and images
            return action_response
        else:
            return jsonify({
                "message": f"I don't know how to {function_name} yet.",
                "status": "error",
                "content_type": "application/json"
            }), 400

    # If no tool calls or not a recognized action, return GPT's text response
    response_message = message.content
    is_conversation_over = False

    # Check if the message content contains JSON with is_conversation_over
    try:
        # Check for JSON in the content
        if response_message.strip().startswith('{') and response_message.strip().endswith('}'):
            # Try to parse it as JSON
            response_json = json.loads(response_message)
            if 'is_conversation_over' in response_json:
                is_conversation_over = response_json.get('is_conversation_over', False)
                # If it's a valid JSON, use the message field if available
                response_message = response_json.get('message', response_message)
    except:
        # If parsing fails, just use the original message
        pass

    return jsonify({
        "message": response_message,
        "status": "success",
        "content_type": "application/json",
        "is_conversation_over": is_conversation_over
    })