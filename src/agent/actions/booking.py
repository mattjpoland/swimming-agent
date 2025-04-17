from flask import jsonify, g
from src.agent.base import AgentAction
from src.agent.utils.date_resolver import validate_and_resolve_date
from src.agent.utils.pool_resolver import normalize_pool_name
import logging
import inspect

class BookLaneAction(AgentAction):
    @property
    def name(self):
        return "book_lane"
    
    @property
    def description(self):
        return "Book a lane in one of the pools for a specific date and time."
    
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string", 
                    "description": "The date to book the lane (YYYY-MM-DD)."
                },
                "time": {
                    "type": "string", 
                    "description": "The starting time for the booking in 12-hour format with AM/PM (e.g., '6:00 AM', '7:30 PM')."
                },
                "duration": {
                    "type": "string", 
                    "description": "The duration of the booking in minutes ('30' or '60', default is '60')."
                },
                "location": {
                    "type": "string", 
                    "description": "The pool to book ('Indoor Pool' or 'Outdoor Pool')."
                },
                "lane": {
                    "type": "string", 
                    "description": "The lane number to book (e.g., '1', '2', '3')."
                }
            },
            "required": ["date", "time", "location", "lane"]
        }
    
    @property
    def prompt_instructions(self):
        return (
                "You can also help users book a lane in the pool. "
                "When a user wants to book a lane, use the book_lane function. "
                "They will need to specify which pool (Indoor or Outdoor), the date, starting time (in 12-hour format with AM/PM, e.g., '6:00 AM', '7:30 PM'), "
                "and lane number. The duration defaults to 60 minutes but can also be 30 minutes. "
                "If they don't provide all required information, ask for the missing details before making the booking. "
                "Remember that users can only book a specific pool (either 'Indoor Pool' or 'Outdoor Pool'), not 'Both Pools'. "
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
        """Execute the lane booking action."""
        try:
            # Extract parameters
            date = arguments.get("date")
            time = arguments.get("time")
            duration = arguments.get("duration", "60")
            location = arguments.get("location")
            lane = arguments.get("lane")
            
            # Validate and resolve the date
            date = validate_and_resolve_date(date, user_input)
            
            # Normalize location (pool name)
            location = normalize_pool_name(location)
            
            # Convert 24-hour time format to 12-hour if needed
            if ":" in time and ("AM" not in time.upper() and "PM" not in time.upper()):
                # Looks like 24-hour format, convert to 12-hour
                try:
                    hour, minute = map(int, time.split(':'))
                    if hour == 0:
                        time_slot = f"12:{minute:02d} AM"
                    elif hour < 12:
                        time_slot = f"{hour}:{minute:02d} AM"
                    elif hour == 12:
                        time_slot = f"12:{minute:02d} PM"
                    else:
                        time_slot = f"{hour-12}:{minute:02d} PM"
                except ValueError:
                    # If conversion fails, use the original time
                    time_slot = time
            else:
                # Assume it's already in 12-hour format or doesn't need conversion
                time_slot = time
            
            # Verify location is valid for booking (not "Both Pools")
            if location == "Both Pools":
                return jsonify({
                    "message": "I'm sorry, but you need to specify which pool (Indoor Pool or Outdoor Pool) you want to book. You can't book 'Both Pools' at once.",
                    "status": "error"
                }), 400
            
            # Format the lane number if needed
            if lane and str(lane).isdigit():
                lane_display = f"Lane {lane}"
            else:
                lane_display = lane
                
            # Format duration if needed
            if duration and str(duration).isdigit():
                duration_display = f"{duration} Min"
            else:
                duration_display = duration
            
            # Log the booking request
            logging.info(f"Agent booking request: date={date}, time={time_slot}, duration={duration}, location={location}, lane={lane}")
            
            # Import the function here to avoid circular imports
            from src.domain.services.bookingService import book_swim_lane_action
            
            # Call the booking service with the correct parameter names
            response, status_code = book_swim_lane_action(
                date=date,
                time_slot=time_slot,  # Use time_slot instead of time
                duration=duration_display,
                location=location,
                lane=lane_display,
                context=context
            )
            
            # Check if booking was successful
            if status_code == 200:
                # Create a friendly success message
                success_message = (
                    f"Great news! I've successfully booked {lane_display} at {location} for you.\n\n"
                    f"📅 Date: {date}\n"
                    f"⏰ Time: {time_slot}\n"
                    f"⏱️ Duration: {duration} minutes\n"
                )
                
                # Add confirmation info if available
                if "message" in response:
                    success_message += f"\n{response['message']}\n"
                    
                success_message += "\nYou can view this booking in your account dashboard."
                
                return jsonify({"message": success_message, "booking_details": response, "status": "success"}), 200
            else:
                # Get error details
                error_message = response.get("message", "Unknown error occurred during booking.")
                
                return jsonify({"message": f"I'm sorry, but I couldn't book this lane. {error_message}", "status": "error"}), status_code
                
        except Exception as e:
            logging.exception("Error in booking lane")
            return jsonify({"message": "I'm sorry, but I encountered an error while trying to book your lane. Please try again later.", "status": "error"}), 500