from flask import jsonify, g, Response
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
    
    @property
    def prompt_instructions(self):
        return (
                "You can help users cancel their scheduled swim lane appointments. "
                "When a user asks to cancel an appointment, use the cancel_appointment function with the date parameter. "
                "If they specify a day like 'Monday' or 'tomorrow', convert it to the appropriate date (YYYY-MM-DD) using the date reference information provided above. "
                "If they've clearly expressed intent to cancel (phrases like 'cancel my lane', 'cancel my appointment', etc.), set the 'confirm' parameter to true. "
                "Only ask for confirmation if their intent seems ambiguous or they're just asking about the cancellation process. "
                "Be proactive - when a user clearly wants to cancel for a specific day, directly use the cancel_appointment function rather than asking for more information. "
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
                return Response(
                    jsonify({
                        "message": "For safety reasons, I need you to confirm that you want to cancel this appointment. Please confirm if you want to proceed with cancellation.",
                        "status": "needs_confirmation"
                    }),
                    status=200,
                    mimetype="application/json"
                )
            
            # Import the function here to avoid circular imports
            from src.domain.services.cancellationService import cancel_appointment_action
            from src.domain.services.appointmentService import get_appointments_schedule_action
            
            # First, check if there's actually an appointment for this date
            appointment_response, appointment_status = get_appointments_schedule_action(date, date, context)
            
            if appointment_status != 200:
                return Response(
                    jsonify({
                        "message": f"I couldn't check if you have an appointment on {date}. Please try again later.",
                        "status": "error"
                    }),
                    status=appointment_status,
                    mimetype="application/json"
                )
            
            appointments = appointment_response.get("appointments", [])
            
            if not appointments:
                return Response(
                    jsonify({
                        "message": f"You don't have any appointments scheduled for {date} that can be cancelled.",
                        "status": "error"
                    }),
                    status=400,
                    mimetype="application/json"
                )
            
            # Format appointment details for the confirmation message
            appointment_details = self._format_appointment_details(appointments[0], date)
            
            # Call the cancellation service
            response, status_code = cancel_appointment_action(date, context)
            
            if status_code != 200:
                return Response(
                    jsonify({
                        "message": f"I couldn't cancel your appointment. {response.get('message', 'Please try again later.')}",
                        "status": "error"
                    }),
                    status=status_code,
                    mimetype="application/json"
                )
            
            # Create a success message
            success_message = f"✅ Success! I've cancelled your appointment for {date}.\n\nDetails of the cancelled appointment:\n{appointment_details}"

            return jsonify({
                "message": success_message,
                "status": "success"
            }), 200
                
        except Exception as e:
            logging.exception(f"Error in cancel_appointment action: {str(e)}")
            return Response(
                jsonify({
                    "message": "I'm sorry, but I encountered an error while trying to cancel your appointment. Please try again later.",
                    "status": "error"
                }),
                status=500,
                mimetype="application/json"
            )
    
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