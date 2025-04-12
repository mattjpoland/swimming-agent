from flask import jsonify, g
from src.agent.base import AgentAction
from src.agent.utils.date_resolver import validate_and_resolve_date
import logging
import datetime
import pytz

class CancelAppointmentAction(AgentAction):
    @property
    def name(self):
        return "cancel_appointment"
    
    @property
    def description(self):
        return "Cancel a scheduled swim lane appointment for a specific date."
    
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string", 
                    "description": "The date of the appointment to cancel (YYYY-MM-DD)."
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Confirmation from the user that they want to cancel the appointment. Should be set to true."
                }
            },
            "required": ["date", "confirm"]
        }
    
    def execute(self, arguments, context, user_input, **kwargs):
        """Execute the appointment cancellation action."""
        try:
            # Extract parameters
            date = arguments.get("date")
            confirm = arguments.get("confirm", False)
            
            # Log the parameters for debugging
            logging.info(f"Cancel appointment parameters: date={date}, confirm={confirm}")
            
            # Validate and resolve the date
            date = validate_and_resolve_date(date, user_input)
            
            # Log the resolved date
            logging.info(f"Resolved date for cancellation: {date}")
            
            # Check if the user has confirmed the cancellation
            if not confirm:
                return jsonify({
                    "message": "For safety reasons, I need you to confirm that you want to cancel this appointment. Please confirm if you want to proceed with cancellation.",
                    "status": "needs_confirmation"
                }), 200
            
            # Import the function here to avoid circular imports
            from src.api.logic.cancellationService import cancel_appointment_action
            from src.api.logic.appointmentService import get_appointments_schedule_action
            
            # First, check if there's actually an appointment for this date
            appointment_response, appointment_status = get_appointments_schedule_action(date, context)
            
            if appointment_status != 200:
                return jsonify({
                    "message": f"I couldn't check if you have an appointment on {date}. Please try again later.",
                    "status": "error"
                }), appointment_status
            
            appointments = appointment_response.get("appointments", [])
            
            if not appointments:
                return jsonify({
                    "message": f"You don't have any appointments scheduled for {date} that can be cancelled.",
                    "status": "error"
                }), 400
            
            # Format appointment details for the confirmation message
            appointment_details = self._format_appointment_details(appointments[0], date)
            
            # Call the cancellation service
            response, status_code = cancel_appointment_action(date, context)
            
            if status_code != 200:
                return jsonify({
                    "message": f"I couldn't cancel your appointment. {response.get('message', 'Please try again later.')}",
                    "status": "error"
                }), status_code
            
            # Create a success message
            success_message = f"✅ Success! I've cancelled your appointment for {date}.\n\nDetails of the cancelled appointment:\n{appointment_details}"
            
            return jsonify({
                "message": success_message,
                "status": "success"
            })
                
        except Exception as e:
            logging.exception(f"Error in cancel_appointment action: {str(e)}")
            return self.handle_error(e, "I'm sorry, but I encountered an error while trying to cancel your appointment. Please try again later.")
    
    def _format_appointment_details(self, appointment, date_str):
        """Format an appointment into a readable string."""
        try:
            # Extract appointment details
            booked_resources = appointment.get("BookedResources", [])
            lane = booked_resources[0] if booked_resources else "Unknown Lane"
            
            # Parse and format the date and time
            time_str = appointment.get("StartDateTime", "Unknown Time")
            try:
                # Convert to datetime object
                appointment_datetime = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                time_formatted = appointment_datetime.strftime("%I:%M %p")
                date_formatted = appointment_datetime.strftime("%A, %B %d, %Y")
            except (ValueError, TypeError):
                time_formatted = "Unknown Time"
                date_formatted = date_str
            
            # Get duration
            duration = appointment.get("DurationInMinutes", appointment.get("Duration", 60))
            
            # Format message
            details = f"📅 Date: {date_formatted}\n"
            details += f"⏰ Time: {time_formatted}\n"
            details += f"🏊 Lane: {lane}\n"
            details += f"⏱️ Duration: {duration} minutes"
            
            return details
            
        except Exception as e:
            logging.exception(f"Error formatting appointment details: {str(e)}")
            return f"Appointment details not available. Date: {date_str}"