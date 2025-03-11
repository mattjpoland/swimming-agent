from src.api.loginGateway import login
from src.api.appointmentGateway import cancel_appointment, get_appointments_schedule
import datetime

def cancel_appointment_action(appointment_date):
    """
    Cancel an existing swim lane appointment on a given date.
    """
    token = login()
    if not token:
        return {"message": "Authentication failed"}, 401

    # Fetch appointments for the given date
    start_date = appointment_date
    end_date = (datetime.datetime.strptime(appointment_date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    appointments, status_code = get_appointments_schedule(token, start_date, end_date)

    if status_code != 200 or not appointments:
        print(f"Error searching for appointments on {appointment_date} to cancel")
        return {"message": "No appointments exist on this date to cancel"}, 404

    # Assuming only one appointment per day
    appointment = appointments[0]
    appointment_id = appointment.get("Id")

    if not appointment_id:
        print(f"No appointments to cancel found for {appointment_date}")
        return {"message": "No appointments exist on this date to cancel"}, 404

    print(f"Cancelling appointment for {appointment_date}")

    # Cancel the appointment
    result, cancel_status_code = cancel_appointment(token, appointment_id)

    if cancel_status_code != 200:
        print(f"Error cancelling appointment for {appointment_date}")
        return {"message": "Failed to cancel appointment"}, 500

    print(f"Appointment for {appointment_date} has been cancelled")
    return {"message": "The appointment has been cancelled."}, 200