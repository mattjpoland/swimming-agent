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
                "date_range": {
                    "type": "string", 
                    "description": "A string specifying a date range like 'today', 'tomorrow', 'this week', 'next week', etc. Used for date range queries."
                }
            },
            "required": []  # At least one of date or date_range should be provided
        }
    
    def execute(self, arguments, context, user_input, **kwargs):
        """Execute the appointments check action."""
        try:
            # Import here to avoid circular imports
            from src.api.logic.appointmentService import get_appointments_schedule_action
            from src.api.gateways.appointmentGateway import get_appointments_schedule
            from src.api.gateways.loginGateway import login_via_context
            
            # Get today's date in Eastern Time
            eastern = pytz.timezone('US/Eastern')
            today = datetime.now(eastern)
            
            # Determine if we're checking a single date or a range
            date = arguments.get("date")
            date_range = arguments.get("date_range", "").lower()
            
            # If neither is provided, default to today
            if not date and not date_range:
                date = today.strftime("%Y-%m-%d")
                date_range = "today"
            
            # If a specific date is provided
            if date:
                # Validate and resolve the date
                date = validate_and_resolve_date(date, user_input)
                
                # Get appointments for the single date
                response, status_code = get_appointments_schedule_action(date, context)
                
                if status_code != 200:
                    return jsonify({
                        "message": f"I couldn't retrieve your appointments. {response.get('message', 'Please try again later.')}",
                        "status": "error"
                    }), status_code
                
                # Return the message from get_appointments_schedule_action
                return jsonify({
                    "message": response.get("message", f"No appointments found for {date}."),
                    "appointments": response.get("appointments", []),
                    "status": "success"
                })
            
            # If a date range is provided
            elif date_range:
                # Calculate start and end dates based on the range
                start_date, end_date = self._calculate_date_range(date_range, today)
                
                # Format dates as ISO 8601 strings
                start_date_str = start_date.isoformat(timespec='seconds')
                end_date_str = end_date.isoformat(timespec='seconds')
                
                # Get auth token
                token = login_via_context(context)
                if not token:
                    return jsonify({"error": "Authentication failed"}), 401
                
                # Fetch appointments for the date range
                appointments, status_code = get_appointments_schedule(token, start_date_str, end_date_str, context)
                
                if status_code != 200 or not appointments:
                    return jsonify({
                        "message": f"I couldn't find any appointments for {date_range}.",
                        "status": "error" if status_code != 200 else "success"
                    }), 200
                
                # Format the appointments into a user-friendly message
                formatted_appointments = self._format_appointments_message(appointments, date_range)
                
                return jsonify({
                    "message": formatted_appointments,
                    "appointments": appointments,
                    "status": "success"
                })
                
        except Exception as e:
            logging.exception(f"Error in check_appointments action: {str(e)}")
            return self.handle_error(e, "I'm sorry, but I encountered an error while checking your appointments. Please try again later.")
    
    def _calculate_date_range(self, date_range, today):
        """Calculate start and end dates based on a date range string."""
        # Default to today
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        if date_range in ["today", "now"]:
            # Already set to today
            pass
        
        elif date_range == "tomorrow":
            start_date = start_date + timedelta(days=1)
            end_date = end_date + timedelta(days=1)
        
        elif date_range in ["this week", "current week"]:
            # Start of week (Monday)
            days_since_monday = today.weekday()
            start_date = start_date - timedelta(days=days_since_monday)
            # End of week (Sunday)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        elif date_range in ["next week", "upcoming week"]:
            # Start of next week (next Monday)
            days_until_next_monday = 7 - today.weekday()
            start_date = start_date + timedelta(days=days_until_next_monday)
            # End of next week (next Sunday)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        elif date_range in ["this weekend", "upcoming weekend"]:
            # Start of weekend (Saturday)
            days_until_saturday = (5 - today.weekday()) % 7
            start_date = start_date + timedelta(days=days_until_saturday)
            # End of weekend (Sunday)
            end_date = start_date + timedelta(days=1, hours=23, minutes=59, seconds=59)
        
        elif date_range in ["next weekend"]:
            # Start of next weekend (Saturday after next)
            days_until_next_saturday = (5 - today.weekday()) % 7 + 7
            start_date = start_date + timedelta(days=days_until_next_saturday)
            # End of next weekend (Sunday after next)
            end_date = start_date + timedelta(days=1, hours=23, minutes=59, seconds=59)
        
        elif date_range in ["this month", "current month"]:
            # Start of month
            start_date = start_date.replace(day=1)
            # End of month - go to first of next month and subtract one day
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        elif date_range in ["next month", "upcoming month"]:
            # Start of next month
            if today.month == 12:
                start_date = start_date.replace(year=today.year + 1, month=1, day=1)
            else:
                start_date = start_date.replace(month=today.month + 1, day=1)
            # End of next month
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return start_date, end_date
    
    def _format_appointments_message(self, appointments, date_range):
        """Format appointments into a user-friendly message."""
        if not appointments:
            return f"You don't have any scheduled swim lane appointments for {date_range}."
        
        # Start building the message
        if len(appointments) == 1:
            message = f"You have 1 scheduled swim lane appointment for {date_range}:\n\n"
        else:
            message = f"You have {len(appointments)} scheduled swim lane appointments for {date_range}:\n\n"
        
        # Format each appointment
        for i, appointment in enumerate(appointments, 1):
            pool_name = appointment.get("ClubName", "Unknown Pool")
            booked_resources = appointment.get("BookedResources", [])
            lane = booked_resources[0] if booked_resources else "Unknown Lane"
            
            # Parse and format the date and time
            time_str = appointment.get("StartDateTime", "Unknown Time")
            try:
                appointment_datetime = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                date_formatted = appointment_datetime.strftime("%A, %B %d, %Y")
                time_formatted = appointment_datetime.strftime("%I:%M %p")
            except (ValueError, TypeError):
                date_formatted = "Unknown Date"
                time_formatted = "Unknown Time"
            
            # Extract the actual duration from the appointment data
            duration = appointment.get("DurationInMinutes", appointment.get("Duration", 60))
            
            # Add to message
            message += f"📅 Appointment {i}:\n"
            message += f"   Date: {date_formatted}\n"
            message += f"   Time: {time_formatted}\n"
            message += f"   Lane: {lane}\n"
            message += f"   Duration: {duration} minutes\n\n"
        
        return message