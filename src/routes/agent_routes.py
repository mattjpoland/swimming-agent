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
    response_format = data.get("response_format", "auto")
    is_siri = data.get("is_siri", False)  # Check if request is from Siri
    
    # Get conversation history (if provided)
    conversation_history = data.get("conversation_history", [])
    
    # Build system prompt, optionally enhanced for voice
    system_prompt = registry.get_system_prompt()
    if is_siri:
        system_prompt += " Since your response will be read aloud by Siri, keep answers brief, clear, and suitable for voice. Avoid visual elements like tables or charts in your responses."
    
    # Build messages array with history
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
            model="gpt-4",
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
            
            # Execute the action
            action_response = action.execute(
                arguments=arguments,
                context=g.context,
                user_input=user_input,
                response_format=response_format
            )
            
            # Check if the response is a tuple (response, status_code)
            if isinstance(action_response, tuple) and len(action_response) == 2:
                response_body, status_code = action_response
                
                # If it's a Flask response object (like from send_file)
                if hasattr(response_body, 'headers') and hasattr(response_body, 'data'):
                    # For file responses (like barcodes)
                    content_type = response_body.headers.get('Content-Type', 'application/octet-stream')
                    
                    # For Siri requests, we convert file responses to a special format
                    if is_siri and 'image' in content_type:
                        import base64
                        # Get the file data
                        file_data = response_body.data
                        # Convert to base64
                        encoded_data = base64.b64encode(file_data).decode('utf-8')
                        
                        # Create a JSON response with embedded image data
                        return jsonify({
                            "message": "I've generated your barcode. Here it is.",
                            "status": "success",
                            "content_type": content_type,
                            "is_file": True,
                            "file_data": encoded_data,
                            "file_name": response_body.headers.get('X-Barcode-ID', 'barcode') + ".png"
                        })
                    
                    # Return the original file response for non-Siri requests
                    return response_body
                
                # For JSON responses, add content_type
                if isinstance(response_body, dict):
                    response_body["content_type"] = "application/json"
                    
                return jsonify(response_body), status_code
            
            # For direct responses, add content_type
            return jsonify({
                "message": str(action_response),
                "status": "success",
                "content_type": "application/json"
            })
            
        else:
            return jsonify({
                "message": f"I don't know how to {function_name} yet.",
                "status": "error",
                "content_type": "application/json"
            }), 400

    # If no tool calls or not a recognized action, return GPT's text response
    return jsonify({
        "message": message.content,
        "status": "success",
        "content_type": "application/json"
    })