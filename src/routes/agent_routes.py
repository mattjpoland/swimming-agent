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

            # Check if this is a non-text response (image, stream, etc.)
            is_special_response = False
            content_type = "application/json"

            # FIRST check for direct Response objects (like the image from _generate_visualization)
            from flask import Response
            if isinstance(action_response, Response) and action_response.mimetype == "image/png":
                return action_response

            # Handle tuple responses (e.g., (response, status_code))
            if isinstance(action_response, tuple) and len(action_response) == 2:
                response, status_code = action_response
                if isinstance(response, dict):
                    # If the response is a JSON object, process it for the LLM
                    tool_result = response.get("message", json.dumps(response))
                    messages.append({
                        "role": "tool",
                        "content": tool_result
                    })
                    final_response = client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=messages
                    )
                    return jsonify({
                        "message": final_response.choices[0].message.content.strip(),
                        "status": "success",
                        "content_type": "application/json"
                    }), 200
                elif isinstance(response, Response) and response.mimetype == "image/png":
                    # If the response is a Flask Response object with image/png, return it directly
                    return response, status_code

            # Directly return Flask Response objects with image/png
            if isinstance(action_response, Response) and action_response.mimetype == "image/png":
                return action_response

            # For text/JSON responses, send the tool result back to the model for rephrasing
            try:
                # Convert action response to string for the model
                tool_result = ""  # Initialize with a default value
                
                # Handle Flask Response objects
                from flask import Response
                if isinstance(action_response, Response):
                    # Extract the data from the Response object
                    try:
                        response_data = action_response.get_data(as_text=True)
                        # Try to parse as JSON if it looks like JSON
                        if response_data.strip().startswith('{') and response_data.strip().endswith('}'):
                            try:
                                json_data = json.loads(response_data)
                                # Prefer message field if available
                                if "message" in json_data:
                                    tool_result = json_data["message"]
                                else:
                                    tool_result = response_data
                            except json.JSONDecodeError:
                                tool_result = response_data
                        else:
                            tool_result = response_data
                    except Exception as e:
                        logging.error(f"Error extracting data from Response object: {e}")
                        tool_result = "Error retrieving data from response"
                
                # Handle tuple responses (typical jsonify returns)
                elif isinstance(action_response, tuple) and len(action_response) == 2:
                    response_obj = action_response[0]
                    if isinstance(response_obj, dict):
                        # Special case for appointments to ensure data accuracy
                        if "message" in response_obj and function_name == "check_appointments":
                            # Make it explicit that this is the actual data and format preferences:
                            messages.append({
                                "role": "system",
                                "content": "The following is the accurate appointment data. Format your response following these rules:\n" +
                                           "1. Your response MUST only include these appointments, DO NOT generate or invent any other appointments\n" +
                                           "2. Format appointments in a concise bullet point list\n" +
                                           "3. Use the day of week (e.g., 'Monday' or 'Tuesday') instead of the full date (no month/date needed)\n" +
                                           "4. Include the time, lane information, and duration\n" + 
                                           "5. Do not say 'at Michigan Athletic Club' or 'in the Michigan Athletic Club'\n" +
                                           "6. Make the response brief and suitable for quick text-to-speech reading"
                            })
                            tool_result = response_obj["message"]
                        else:
                            # For other responses
                            tool_result = json.dumps(response_obj)
                    elif isinstance(response_obj, Response):
                        # Handle Flask Response objects within tuples
                        try:
                            response_data = response_obj.get_data(as_text=True)
                            # Try to parse as JSON
                            if response_data.strip().startswith('{'):
                                try:
                                    json_data = json.loads(response_data)
                                    if "message" in json_data:
                                        tool_result = json_data["message"]
                                    else:
                                        tool_result = response_data
                                except json.JSONDecodeError:
                                    tool_result = response_data
                            else:
                                tool_result = response_data
                        except Exception as e:
                            logging.error(f"Error extracting data from Response in tuple: {e}")
                            tool_result = "Error retrieving data from response"
                    else:
                        # Handle non-dict, non-Response objects
                        tool_result = str(response_obj)
                else:
                    # Handle non-tuple, non-Response responses
                    tool_result = str(action_response)
                
                # Add the tool response to messages
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                    ]
                })
                
                # Add the tool response
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result)
                })
                
                # Get a human-friendly response that incorporates the tool result
                final_response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages
                )
                
                # After getting the LLM response
                try:
                    # Parse the LLM response for structured fields
                    ai_response = final_response.choices[0].message.content.strip()
                    
                    # Try to parse as JSON if it looks like valid JSON
                    if ai_response.startswith('{') and ai_response.endswith('}'):
                        try:
                            response_data = json.loads(ai_response)
                            is_conversation_over = response_data.get('is_conversation_over', False)
                            message = response_data.get('message', ai_response)
                        except json.JSONDecodeError:
                            # If it's not valid JSON, use the whole text as message
                            message = ai_response
                            is_conversation_over = False
                    else:
                        # Not JSON-formatted, use as-is
                        message = ai_response
                        is_conversation_over = False
                    
                    # Add your additional fields
                    return jsonify({
                        "message": message,
                        "is_conversation_over": is_conversation_over,
                        "content_type": "application/json",
                        "status": "success"
                    })
                except Exception as e:
                    logging.error(f"Error in response processing: {e}")
                    return jsonify({
                        "message": ai_response if 'ai_response' in locals() else "Error processing response",
                        "is_conversation_over": False,
                        "content_type": "application/json",
                        "status": "error"
                    })

            except Exception as e:
                logging.error(f"Error in rephrasing: {e}")
                # Fall back to original response if rephrasing fails
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