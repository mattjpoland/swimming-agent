from src.api.gateways.loginGateway import login
from src.api.gateways.appointmentGateway import book_swim_lane
import datetime
import pytz

def book_swim_lane_action(date, time_slot, duration, location, lane, context):
    """
    Book a swim lane for a given date range.
    """
    token = login(context)
    if not token:
        return {"message": "Authentication failed"}, 401

    # Combine date and time_slot into a datetime object
    appointment_datetime_str = f"{date} {time_slot}"
    appointment_datetime = datetime.datetime.strptime(appointment_datetime_str, "%Y-%m-%d %I:%M %p")

    # Localize to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    appointment_datetime = eastern.localize(appointment_datetime)

    # Format as ISO 8601 string
    appointment_date_time = appointment_datetime.isoformat()

    appointments, status_code = book_swim_lane(token, appointment_date_time, duration, location, lane, context)

    if status_code != 200 or not appointments or not appointments.get("Success"):
        return {"message": "Failed to book appointment"}, 500

    message = f"{location} {lane} successfully booked for {duration} on {date} at {time_slot}"
    return {"message": message}, 200