from src.api.login import login
from src.api.scheduling import get_appointments_schedule
import datetime

def get_scheduled_appointments(start_date, end_date):
    """
    Fetch scheduled swim lane appointments for a given date range.
    """
    token = login()
    if not token:
        return {"error": "Authentication failed"}, 401

    appointments = get_appointments_schedule(token, start_date, end_date)

    if appointments is None:
        return {"error": "Failed to retrieve appointments"}, 500

    return appointments, 200  # Return data with HTTP 200 OK
