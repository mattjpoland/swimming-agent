from src.api.loginGateway import login
from src.api.schedulingGateway import get_appointments_schedule, book_swim_lane, cancel_appointment
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

def book_swim_lane_action(date, time_slot, duration, location, lane):
    """
    Book a swim lane for a given date range.
    """
    token = login()
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

    appointments, status_code = book_swim_lane(token, appointment_date_time, duration, location, lane)

    if status_code != 200 or not appointments or not appointments[0].get("Success"):
        return {"message": "Failed to book appointment"}, 500

    message = f"{location} {lane} successfully booked for {duration} on {date} at {time_slot}"
    return {"message": message}, 200

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
        print(f"Error searching for  appointments on {appointment_date} to cancel")
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
