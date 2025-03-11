from src.api.loginGateway import login
from src.api.appointmentGateway import get_appointments_schedule
import datetime
import pytz
import requests

def get_appointments_schedule_action(date_str):
    """
    Fetch scheduled swim lane appointments for a given date.
    """
    token = login()
    if not token:
        return {"error": "Authentication failed"}, 401

    # Localize the date to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    start_date = eastern.localize(date.replace(hour=0, minute=0, second=0))
    end_date = eastern.localize(date.replace(hour=23, minute=59, second=59))

    # Format dates as ISO 8601 strings
    start_date_str = start_date.isoformat(timespec='seconds')
    end_date_str = end_date.isoformat(timespec='seconds')

    print(f"Fetching appointments between {start_date_str} and {end_date_str}")
    appointments, status_code = get_appointments_schedule(token, start_date_str, end_date_str)

    if status_code != 200:
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
        
        print(f"Found appointment for {lane} at {time} on {date_str}")
        message = f"You have {lane} at {time} on {date_str}."
    else:
        print(f"No appointment found for {date_str}")
        message = f"You do not have a swim lane on {date_str}."

    return {"message": message}, 200