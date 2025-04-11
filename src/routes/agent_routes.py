from flask import Blueprint, request, jsonify, g
from openai import OpenAI
import os
import json
from src.api.logic.availabilityService import get_availability
from src.decorators import require_api_key  # Import the decorator

# Define the Flask Blueprint
agent_bp = Blueprint("agent", __name__)

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@agent_bp.route("/agent", methods=["POST"])
@require_api_key  # Add this decorator to ensure g.context is available
def handle_agent_request():
    """
    Handle agent requests by processing the user input and integrating GPT-4 function calling.

    Returns:
        dict: A response indicating the result of processing the user input.
    """
    # Parse JSON body
    data = request.get_json()
    if not data or "user_input" not in data:
        return jsonify({"error": "User input is required"}), 400

    user_input = data["user_input"]

    # Define the GPT tool/function as a tool in v1.0.0
    tools = [
        {
            "type": "function",
            "function": {
                "name": "check_lane_availability",
                "description": "Check swim lane availability for a specific pool and date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pool_name": {"type": "string", "description": "The name of the pool (e.g., 'Indoor Pool', 'Outdoor Pool')."},
                        "date": {"type": "string", "description": "The date to check availability (YYYY-MM-DD)."}
                    },
                    "required": ["pool_name", "date"]
                }
            }
        }
    ]

    # Call GPT-4 with the user input and function definition
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that checks swim lane availability."},
                {"role": "user", "content": user_input}
            ],
            tools=tools,
            tool_choice="auto"
        )
    except Exception as e:
        return jsonify({"error": f"Error communicating with OpenAI: {str(e)}"}), 500

    # Check if GPT returned a tool call (function call in v1.0.0)
    message = response.choices[0].message
    tool_calls = message.tool_calls

    if tool_calls:
        # Get the first tool call
        tool_call = tool_calls[0]
        function_name = tool_call.function.name
        
        # Parse the arguments from JSON string
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            return jsonify({"error": "Failed to parse function arguments"}), 500

        if function_name == "check_lane_availability":
            # Extract arguments
            pool_name = arguments.get("pool_name")
            date = arguments.get("date")

            # Validate pool_name
            if "ITEMS" not in g.context or pool_name not in g.context["ITEMS"]:
                return jsonify({"error": f"Invalid pool name: {pool_name}"}), 400

            # Get item_id and check availability
            item_id = g.context["ITEMS"][pool_name]
            availability = get_availability(item_id, date, g.context)

            # Format the availability response
            availability_message = f"Availability for {pool_name} on {date}:\n"
            for time_slot, lanes in availability.items():
                availability_message += f"{time_slot}: Lanes {', '.join(map(str, lanes))}\n"

            # Return the formatted availability message
            return jsonify({"message": availability_message, "status": "success"})

    # If no tool calls, return GPT's response
    return jsonify({"message": message.content, "status": "success"})