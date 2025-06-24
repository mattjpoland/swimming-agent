from flask import jsonify, g, send_file
from src.agent.base import AgentAction
from src.agent.utils.date_resolver import validate_and_resolve_date
from src.agent.utils.pool_resolver import normalize_pool_name
from src.domain.services.availabilityService import get_availability
from src.domain.services.appointmentService import get_appointment_data
from src.domain.drawing.availabilityVisualGenerator import generate_visualization, combine_visualizations
import logging

class AvailabilityAction(AgentAction):
    @property
    def name(self):
        return "check_lane_availability"
    
    @property
    def description(self):
        return "Check swim lane availability for a specific pool and date. If pool name is not specified, checks both Indoor and Outdoor pools."
    
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "The name of the pool (e.g., 'Indoor Pool', 'Outdoor Pool', 'Both Pools'). If not specified, defaults to 'Both Pools'."},
                "date": {"type": "string", "description": "The date to check availability (YYYY-MM-DD)."},
                "format": {"type": "string", "enum": ["visual", "text"], "description": "Response format, either 'visual' (default) for a visualization or 'text' for a text description. Use 'text' for specific queries about times or lanes."}
            },
            "required": ["date"]  # Only date is required, pool_name and format are optional
        }
    
    @property
    def prompt_instructions(self):
        return (
                "You can help with checking pool availability. "
                "Use the check_lane_availability function when asked about pool availability. "
                "If the user doesn't specify which pool, assume they want to check 'Both Pools'. "
                "For date parameters, use the YYYY-MM-DD format. "
                "When calculating dates from day names (like 'Sunday' or 'Monday'), always refer to the date information provided above. "
                "By default, use the 'visual' format for general availability queries. "
                "Use the 'text' format instead when: "
                "1. The user asks about specific time slots or specific lanes "
                "2. The user is trying to find alternative times for a booked lane "
                "3. The user is trying to find alternative lanes for a booked time "
                "4. The user explicitly asks for availability information without visualization "
        )
    
    @property
    def response_format_instructions(self):
        return (
            "Format your availability response following these guidelines:\n"
            "1. Begin with a clear summary of the overall availability\n"
            "2. Group availability by time slots for easy scanning\n"
            "3. When multiple lanes are available at the same time, use a concise format: '6:00 PM: Lanes 2, 3, 5'\n"
            "4. Highlight peak times with good availability and mention times with limited availability\n"
            "5. For both pools, clearly separate the Indoor and Outdoor pool sections\n"
            "6. Format dates in a conversational way (e.g., 'today', 'tomorrow', 'Monday', etc.)\n"
            "7. If there's no availability for a specific time or pool, state that clearly\n"
            "8. Keep the response concise and scannable"
        )
    
    def get_tool_definition(self):
        """
        Get the tool definition for OpenAI API.
        This is required for the function calling API.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def execute(self, arguments, context, user_input, **kwargs):
        """Execute the availability check action."""
        try:
            # Extract and normalize parameters
            pool_name = arguments.get("pool_name", "")  # Default to empty string if missing
            date = arguments.get("date")
            format_type = arguments.get("format", "visual")  # Default to visual if not specified
            
            # Validate and resolve the date
            date = validate_and_resolve_date(date, user_input)
            
            # Normalize pool name, defaulting to "Both Pools" if not specified
            pool_name = normalize_pool_name(pool_name)
            
            # Handle different response formats
            if format_type == "text":
                return jsonify(self._generate_text_response(pool_name, date, context))
            else:
                return self._generate_visualization(pool_name, date, context)
        except Exception as e:
            logging.error(f"Error checking availability: {str(e)}", exc_info=True)
            return jsonify({"message": "I couldn't check availability at this time. Please try again later.", "status": "error"}), 500
    
    def _generate_text_response(self, pool_name, date, context):
        """Generate text-based availability response."""
        if pool_name == "Both Pools":
            indoor_pool_name = "Indoor Pool"
            outdoor_pool_name = "Outdoor Pool"

            if "ITEMS" not in context:
                return jsonify({"error": "Context missing ITEMS"}), 500
            
            indoor_item_id = context["ITEMS"].get(indoor_pool_name)
            outdoor_item_id = context["ITEMS"].get(outdoor_pool_name)
            
            if not indoor_item_id or not outdoor_item_id:
                return jsonify({"error": "Invalid pool configuration"}), 500

            indoor_availability = get_availability(indoor_item_id, date, context)
            outdoor_availability = get_availability(outdoor_item_id, date, context)
            
            # Format text response
            availability_message = f"Availability for pools on {date}:\n\n"
            availability_message += f"INDOOR POOL:\n"
            for time_slot, lanes in indoor_availability.items():
                if lanes:  # Only show time slots with available lanes
                    availability_message += f"{time_slot}: Lanes {', '.join(map(str, lanes))}\n"
            
            availability_message += f"\nOUTDOOR POOL:\n"
            for time_slot, lanes in outdoor_availability.items():
                if lanes:  # Only show time slots with available lanes
                    availability_message += f"{time_slot}: Lanes {', '.join(map(str, lanes))}\n"
            
            return {"message": availability_message, "status": "success"}
        else:
            # Validate pool_name
            if "ITEMS" not in context or pool_name not in context["ITEMS"]:
                return {"error": f"Invalid pool name: {pool_name}"}, 400

            # Get item_id and check availability
            item_id = context["ITEMS"][pool_name]
            availability = get_availability(item_id, date, context)
            
            # Log the raw availability data for debugging
            logging.info(f"🔍 Raw availability data for {pool_name} on {date}: {availability}")

            # Format text response
            availability_message = f"Availability for {pool_name} on {date}:\n"
            available_count = 0
            for time_slot, lanes in availability.items():
                if lanes:  # Only show time slots with available lanes
                    availability_message += f"{time_slot}: Lanes {', '.join(map(str, lanes))}\n"
                    available_count += len(lanes)
            
            # Log summary for debugging
            logging.info(f"🔍 Availability summary for {pool_name}: {available_count} total lane slots available")
            logging.info(f"🔍 Formatted availability message: {availability_message}")

            return {"message": availability_message, "status": "success"}
    
    def _generate_visualization(self, pool_name, date, context):
        """Generate visual availability response."""
        try:
            if pool_name == "Both Pools":
                indoor_pool_name = "Indoor Pool"
                outdoor_pool_name = "Outdoor Pool"

                if "ITEMS" not in context:
                    return jsonify({"error": "Context missing ITEMS"}), 500
                
                indoor_item_id = context["ITEMS"].get(indoor_pool_name)
                outdoor_item_id = context["ITEMS"].get(outdoor_pool_name)
                
                if not indoor_item_id or not outdoor_item_id:
                    return jsonify({"error": "Invalid pool configuration"}), 500

                indoor_availability = get_availability(indoor_item_id, date, context)
                outdoor_availability = get_availability(outdoor_item_id, date, context)

                indoor_appt = get_appointment_data(date, date, context)
                outdoor_appt = get_appointment_data(date, date, context)

                indoor_img = generate_visualization(indoor_availability, indoor_pool_name, date, indoor_appt, context)
                outdoor_img = generate_visualization(outdoor_availability, outdoor_pool_name, date, outdoor_appt, context)

                combined_img_io = combine_visualizations(indoor_img, outdoor_img)
                
                # Return the visualization with an explanatory message in the headers
                response = send_file(combined_img_io, mimetype="image/png")
                response.headers["X-Availability-Date"] = date
                response.headers["X-Pool-Name"] = "Both Pools"
                response.headers["X-Response-Type"] = "availability"
                return response
            else:
                # Validate pool_name
                if "ITEMS" not in context or pool_name not in context["ITEMS"]:
                    return jsonify({"error": f"Invalid pool name: {pool_name}"}), 400

                # Get item_id and check availability
                item_id = context["ITEMS"][pool_name]
                availability = get_availability(item_id, date, context)
                appt = get_appointment_data(date, date, context)

                img_io = generate_visualization(availability, pool_name, date, appt, context)
                
                # Return the visualization with an explanatory message in the headers
                response = send_file(img_io, mimetype="image/png")
                response.headers["X-Availability-Date"] = date
                response.headers["X-Pool-Name"] = pool_name
                response.headers["X-Response-Type"] = "availability"
                return response
        except Exception as e:
            logging.error(f"Error generating visualization: {str(e)}")
            # Fall back to text response if visualization fails
            return jsonify(self._generate_text_response(pool_name, date, context))