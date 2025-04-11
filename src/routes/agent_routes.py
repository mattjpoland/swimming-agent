from flask import Blueprint, request, jsonify, g
import openai
import os
from src.api.logic.availabilityService import get_availability  # Correct import

# Define the Flask Blueprint
agent_bp = Blueprint("agent", __name__)

# Set OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

@agent_bp.route("/agent", methods=["POST"])
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

    # Define the GPT tool/function
    functions = [
        {
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
    ]

    # Call GPT-4 with the user input and function definition
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that checks swim lane availability."},
                {"role": "user", "content": user_input}
            ],
            functions=functions,
            function_call="auto"
        )
    except openai.OpenAIError as e:  # Correct exception handling
        return jsonify({"error": f"Error communicating with OpenAI: {str(e)}"}), 500

    # Check if GPT returned a function call
    function_call = response.choices[0].message.get("function_call")
    if function_call:
        function_name = function_call["name"]
        arguments = function_call["arguments"]

        if function_name == "check_lane_availability":
            # Extract arguments
            pool_name = arguments.get("pool_name")
            date = arguments.get("date")

            # Validate pool_name
            if pool_name not in g.context["ITEMS"]:
                return jsonify({"error": f"Invalid pool name: {pool_name}"}), 400

            # Get item_id and check availability
            item_id = g.context["ITEMS"][pool_name]
            availability = get_availability(item_id, date, g.context)

            # Format the availability response
            availability_message = f"Availability for {pool_name} on {date}:\n"
            for time_slot, lanes in availability.items():
                availability_message += f"{time_slot}: Lanes {', '.join(map(str, lanes))}\n"

            # Return GPT's final message
            return jsonify({"message": availability_message, "status": "success"})

    # If no function call, return GPT's response
    return jsonify({"message": response.choices[0].message["content"], "status": "success"})