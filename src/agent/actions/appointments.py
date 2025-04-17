from flask import jsonify, g
from src.agent.base import AgentAction
from src.agent.utils.date_resolver import validate_and_resolve_date
from datetime import datetime, timedelta
import logging
import pytz

class AppointmentsAction(AgentAction):
    @property
    def name(self):
        return "check_appointments"
    
    @property
    def description(self):
        return "Check user's swim lane appointments for a specific date or date range."
    
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string", 
                    "description": "A specific date to check for appointments (YYYY-MM-DD). Used for single day queries."
                },
                "start_date": {
                    "type": "string", 
                    "description": "The start date of the date range (YYYY-MM-DD)."
                },
                "end_date": {
                    "type": "string", 
                    "description": "The end date of the date range (YYYY-MM-DD)."
                }
            },
            "required": []  # At least one parameter should be provided
        }
    
    @property
    def prompt_instructions(self):
        return (
                "You can help users check their scheduled swim lane appointments. "
                "When a user asks about their appointments, use the check_appointments function. "
                "They can ask about appointments for a specific date (e.g., 'tomorrow', 'Monday') "
                "or for a date range (e.g., 'this week', 'next month'). "
                "When a user asks for appointments in natural language (e.g., 'this week', 'next month'), "
                "YOU should determine the appropriate start_date and end_date in YYYY-MM-DD format "
                "based on the current date and the user's request. "
                "If they don't specify a date or range, check for today's appointments. "
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
        """Execute the appointments check action."""
        try:
            # Import here to avoid circular imports
            from src.domain.services.appointmentService import get_appointments_schedule_action
            from src.domain.gateways.appointmentGateway import get_appointments_schedule
            from src.domain.gateways.loginGateway import login_via_context
            
            # Get today's date in Eastern Time
            eastern = pytz.timezone('US/Eastern')
            today = datetime.now(eastern)
            today_str = today.strftime("%Y-%m-%d")
            
            # Get arguments from the request
            date = arguments.get("date")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            
            # Case 1: Single date specified
            if date:
                # Validate and resolve the date
                date = validate_and_resolve_date(date, user_input)
                
                # Use the same date for both start and end (single day query)
                start_date = date
                end_date = date
            
            # Case 2: Date range specified
            elif start_date and end_date:
                # Validate and resolve the dates
                start_date = start_date
                end_date = end_date
                
                # Create date objects to ensure start_date is before end_date
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                
                if start_dt > end_dt:
                    return jsonify({
                        "message": "Start date must be before end date.",
                        "status": "error"
                    }), 400
            
            # Case 3: No dates specified, default to today
            else:
                start_date = today_str
                end_date = today_str
            
            # Get appointments using start_date and end_date
            response, status_code = get_appointments_schedule_action(
                start_date=start_date, 
                end_date=end_date, 
                context=context
            )
            
            if status_code != 200:
                return jsonify({
                    "message": f"I couldn't retrieve your appointments. {response.get('message', 'Please try again later.')}",
                    "status": "error"
                }), status_code
            
            # Check if appointments were found
            appointments = response.get("appointments", [])
            appointment_details = response.get("appointment_details", [])
            
            # If we received appointment_details, format them into a user-friendly message
            if appointment_details:
                # Convert start_date and end_date to datetime objects for friendly date formatting
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                date_range = self._get_friendly_date_range(start_dt, end_dt)
                
                # Format a message with the appointment details
                message = f"You have {len(appointment_details)} swim lane appointment(s) for {date_range}:\n\n"
                for appt in appointment_details:
                    message += f"- Date: {appt['date']}, Time: {appt['time']}\n"
                    message += f"  Pool: {appt['pool']}, Lane: {appt['lane']}\n" 
                    message += f"  Duration: {appt['duration']} minutes\n\n"
            else:
                # Use the message from the service if it exists, otherwise create a fallback message
                message = response.get("message")
                if not message:
                    # Convert dates to datetime objects for friendly date formatting
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    date_range = self._get_friendly_date_range(start_dt, end_dt)
                    message = f"No appointments found for {date_range}."
            
            return jsonify({"message": message, "appointment_details": appointment_details, "status": "success"}), 200
                
        except Exception as e:
            logging.exception(f"Error in check_appointments action: {str(e)}")
            return jsonify({"message": "I'm sorry, but I encountered an error while checking your appointments. Please try again later.", "status": "error"}), 500
    
    def _get_friendly_date_range(self, start_dt, end_dt):
        """Return a user-friendly description of the date range."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        # If start and end date are the same
        if start_dt.date() == end_dt.date():
            if start_dt.date() == today.date():
                return "today"
            elif start_dt.date() == tomorrow.date():
                return "tomorrow"
            else:
                return start_dt.strftime("%A, %B %d")
        
        # Check for this week
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        if start_dt.date() == start_of_week.date() and end_dt.date() == end_of_week.date():
            return "this week"
        
        # Check for next week
        next_week_start = start_of_week + timedelta(days=7)
        next_week_end = next_week_start + timedelta(days=6)
        if start_dt.date() == next_week_start.date() and end_dt.date() == next_week_end.date():
            return "next week"
        
        # Default to date range
        return f"{start_dt.strftime('%B %d')} to {end_dt.strftime('%B %d')}"
    
    def _format_appointments_message(self, appointments, date_range):
        """Format appointments into a user-friendly message."""
        if not appointments:
            return f"You don't have any scheduled swim lane appointments for {date_range}."
        
        # Create a clean bullet-point list that's easy for the LLM to format
        lines = []
        for appointment in appointments:
            pool_name = appointment.get("ClubName", "Unknown Pool")
            booked_resources = appointment.get("BookedResources", [])
            lane = booked_resources[0] if booked_resources else "Unknown Lane"
            
            # Parse and format date/time
            time_str = appointment.get("StartDateTime", "Unknown Time")
            try:
                appt_datetime = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                day_name = appt_datetime.strftime("%A")
                date = appt_datetime.strftime("%B %d")
                start_time = appt_datetime.strftime("%I:%M %p").lstrip("0")
                
                # Calculate end time based on duration
                duration = appointment.get("DurationInMinutes", 60)  # Fixed to use correct field
                end_datetime = appt_datetime + timedelta(minutes=duration)
                end_time = end_datetime.strftime("%I:%M %p").lstrip("0")
                
                # Create a formatted line
                lines.append(f"- On {day_name}, {date}, from {start_time} to {end_time} in {lane} at the {pool_name}.")
            except:
                lines.append(f"- Appointment with {lane} at {pool_name} (time details unavailable)")
        
        return f"You have the following swim lane appointments for {date_range}:\n\n" + "\n".join(lines)