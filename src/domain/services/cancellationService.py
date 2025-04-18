from src.domain.gateways.loginGateway import login_via_context
from src.domain.gateways.appointmentGateway import cancel_appointment, get_appointments_schedule
import datetime
import pytz
import logging

def cancel_appointment_action(appointment_date, context):
    """
    Cancel an existing swim lane appointment on a given date.
    """
    token = login_via_context(context)
    if not token:
        return {"message": "Authentication failed"}, 401

    
    # Localize the date to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    date = datetime.datetime.strptime(appointment_date, "%Y-%m-%d")
    start_date = eastern.localize(date.replace(hour=0, minute=0, second=0))
    end_date = eastern.localize(date.replace(hour=23, minute=59, second=59))
    
    # Format dates as ISO 8601 strings
    start_date_str = start_date.isoformat(timespec='seconds')
    end_date_str = end_date.isoformat(timespec='seconds')

    # Fetch appointments for the given date
    logging.info(f"Fetching appointments between {start_date_str} and {end_date_str}")
    appointments, status_code = get_appointments_schedule(token, start_date_str, end_date_str, context)

    if status_code != 200 or not appointments:
        logging.info(f"Error searching for appointments on {appointment_date} to cancel")
        return {"message": "No appointments exist on this date to cancel"}, 200

    # Assuming only one appointment per day
    appointment = appointments[0]
    appointment_id = appointment.get("Id")

    if not appointment_id:
        logging.info(f"No appointments to cancel found for {appointment_date}")
        return {"message": "No appointments exist on this date to cancel"}, 404

    logging.info(f"Cancelling appointment for {appointment_date}")

    # Cancel the appointment
    result, cancel_status_code = cancel_appointment(token, appointment_id, context)

    if cancel_status_code != 200:
        logging.info(f"Error cancelling appointment for {appointment_date}")
        return {"message": "Failed to cancel appointment"}, 500

    logging.info(f"Appointment for {appointment_date} has been cancelled")
    return {"message": f"The appointment for {appointment_date} has been cancelled."}, 200