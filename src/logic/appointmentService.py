from src.api.loginGateway import login
from src.api.appointmentGateway import get_appointments_schedule
import datetime
import pytz
import requests

def get_appointments_schedule_action(start_date, end_date):
    """
    Fetch scheduled swim lane appointments for a given date range.
    """
    token = login()
    if not token:
        return {"error": "Authentication failed"}, 401

    appointments, status_code = get_appointments_schedule(token, start_date, end_date)

    if status_code != 200 or not appointments:
        return {"message": "Error retrieving swim lane information."}, status_code

    if appointments:
        appointment = appointments[0]  # Assuming only one appointment per day
        pool_name = appointment.get("ClubName", "Unknown Pool")
        booked_resources = appointment.get("BookedResources", [])
        lane = booked_resources[0] if booked_resources else "Unknown Lane"
        time_str = appointment.get("StartDateTime", "Unknown Time")
        
        # Parse and format the time
        try:
            time = datetime.datetime.fromisoformat(time_str).strftime("%I:%M %p")
        except ValueError:
            time = "Unknown Time"
        
        message = f"You have {pool_name} {lane} at {time} today."
    else:
        message = "You do not have a swim lane today."

    return {"message": message}, 200