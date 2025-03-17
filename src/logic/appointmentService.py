from src.api.loginGateway import login
from src.api.appointmentGateway import get_appointments_schedule
from src.api.availabilityGateway import check_swim_lane_availability
import src.contextManager
import datetime
import pytz
import requests

def get_appointments_schedule_action(date_str, context):
    """
    Fetch scheduled swim lane appointments for a given date.
    """
    token = login(context)
    if not token:
        return {"error": "Authentication failed"}, 401

    # Localize the date to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    start_date = eastern.localize(date.replace(hour=0, minute=0, second=0, microsecond=0))
    end_date = eastern.localize(date.replace(hour=23, minute=59, second=59, microsecond=999999))

    # Format dates as ISO 8601 strings
    start_date_str = start_date.isoformat(timespec='seconds')
    end_date_str = end_date.isoformat(timespec='seconds')

    print(f"Fetching appointments between {start_date_str} and {end_date_str}")
    appointments, status_code = get_appointments_schedule(token, start_date_str, end_date_str, context)

    if status_code != 200:
        return {"message": "Error retrieving swim lane information."}, status_code

    if appointments:
        appointment = appointments[0]  # Assuming only one appointment per day
        pool_name = appointment.get("ClubName", "Unknown Pool")
        booked_resources = appointment.get("BookedResources", [])
        lane = booked_resources[0] if booked_resources else "Unknown Lane"
        time_str = appointment.get("StartDateTime", "Unknown Time")
        duration = appointment.get("Duration", 60)  # Assuming duration is in minutes

        # Parse and format the time
        try:
            appointment_time = datetime.datetime.fromisoformat(time_str)
            time = appointment_time.strftime("%I:%M %p")
        except ValueError:
            time = "Unknown Time"
            appointment_time = None

        message = f"You have an appointment for {lane} at {time} on {date_str}."

        if appointment_time:
            # Check availability before and after the appointment
            before_start = appointment_time - datetime.timedelta(minutes=duration)
            after_end = appointment_time + datetime.timedelta(minutes=duration)

            # Extract pool name from lane and get item_id
            pool_key = lane.split()[0] + " Pool"
            item_id = context["ITEMS"].get(pool_key, None)
            if not item_id:
                return {"message": "Invalid pool name."}, 400

            availability = check_swim_lane_availability(token, date_str, item_id, context)

            # Flatten the availability times
            available_times = []
            for day in availability.get("Availability", []):
                for time_slot in day.get("AvailableTimes", []):
                    for selection in time_slot.get("PossibleBookSelections", []):
                        for lane_info in selection:
                            if lane_info["Name"] == lane:
                                available_times.append(datetime.datetime.fromisoformat(time_slot["StartDateTime"]))

            # ✅ FIX: Reverse the logic to check if lane is **booked** before/after
            before_free = before_start in available_times
            after_free = after_end in available_times

            if before_free and after_free:
                message += " The lane is free before and after your appointment."
            elif not before_free and after_free:
                message += " The lane is free after your appointment."
            elif before_free and not after_free:
                message += " The lane is free before your appointment."

    else:
        print(f"No appointment found for {date_str}")
        message = f"You do not have a swim lane on {date_str}."

    return {"message": message}, 200

def get_appointment_data(date_str, context):
    """
    Fetch scheduled swim lane appointment data for a given date.
    """
    token = login(context)
    if not token:
        return {"error": "Authentication failed"}, 401

    # Localize the date to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    start_date = eastern.localize(date.replace(hour=0, minute=0, second=0, microsecond=0))
    end_date = eastern.localize(date.replace(hour=23, minute=59, second=59, microsecond=999999))

    # Format dates as ISO 8601 strings
    start_date_str = start_date.isoformat(timespec='seconds')
    end_date_str = end_date.isoformat(timespec='seconds')

    print(f"Fetching appointments between {start_date_str} and {end_date_str}")
    appointments, status_code = get_appointments_schedule(token, start_date_str, end_date_str, context)

    if status_code != 200:
        return {"message": "Error retrieving swim lane information."}, status_code

    if appointments:
        appointment = appointments[0]  # Assuming only one appointment per day
        booked_resources = appointment.get("BookedResources", [])
        lane = booked_resources[0] if booked_resources else "Unknown Lane"
        time_str = appointment.get("StartDateTime", "Unknown Time")
        duration = appointment.get("Duration", 60)  # Assuming duration is in minutes

        # Parse and format the time
        try:
            appointment_time = datetime.datetime.fromisoformat(time_str)
            time = appointment_time.strftime("%I:%M %p")
        except ValueError:
            time = "Unknown Time"
            appointment_time = None

        return {
            "lane": lane,
            "time": time,
            "duration": duration
        }

    return {}
