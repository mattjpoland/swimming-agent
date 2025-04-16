from src.api.gateways.loginGateway import login_via_context
from src.api.gateways.appointmentGateway import get_appointments_schedule
from src.api.gateways.availabilityGateway import check_swim_lane_availability
import src.contextManager
import datetime
import pytz
import requests
import logging

def get_appointments_schedule_action(start_date=None, end_date=None, context=None):
    """
    Fetch scheduled swim lane appointments for a given date or date range.
    Accepts start_date and end_date parameters. For a single day, set both to the same date.
    Returns both the formatted message and the raw appointments data.
    """
    token = login_via_context(context)
    if not token:
        return {"error": "Authentication failed"}, 401

    # Localize the date(s) to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    
    # Validate that we have both start_date and end_date
    if not start_date or not end_date:
        return {"message": "Both start_date and end_date must be provided."}, 400
    
    # Process date range
    start_date_obj = eastern.localize(datetime.datetime.strptime(start_date, "%Y-%m-%d")
                                 .replace(hour=0, minute=0, second=0, microsecond=0))
    end_date_obj = eastern.localize(datetime.datetime.strptime(end_date, "%Y-%m-%d")
                               .replace(hour=23, minute=59, second=59, microsecond=999999))
    
    # Determine if this is a single day query
    single_date_mode = start_date == end_date

    # Format dates as ISO 8601 strings
    start_date_str = start_date_obj.isoformat(timespec='seconds')
    end_date_str = end_date_obj.isoformat(timespec='seconds')

    logging.info(f"Fetching appointments between {start_date_str} and {end_date_str}")
    appointments, status_code = get_appointments_schedule(token, start_date_str, end_date_str, context)

    if status_code != 200:
        return {"message": "Error retrieving swim lane information."}, status_code

    if appointments and single_date_mode:
        # Single date mode - similar to original function
        appointment = appointments[0]  # Assuming only one appointment per day
        pool_name = appointment.get("ClubName", "Unknown Pool")
        booked_resources = appointment.get("BookedResources", [])
        lane = booked_resources[0] if booked_resources else "Unknown Lane"
        time_str = appointment.get("StartDateTime", "Unknown Time")
        duration = appointment.get("DurationInMinutes", 60)  # Get duration from correct field

        # Parse and format the time
        try:
            appointment_time = datetime.datetime.fromisoformat(time_str)
            time = appointment_time.strftime("%I:%M %p")
        except ValueError:
            time = "Unknown Time"
            appointment_time = None

        message = f"You have an appointment for {lane} at {time} on {start_date}."

        if appointment_time:
            # Check availability before and after the appointment
            before_start = appointment_time - datetime.timedelta(minutes=duration)
            after_end = appointment_time + datetime.timedelta(minutes=duration)

            # Extract pool name from lane and get item_id
            pool_key = lane.split()[0] + " Pool"
            item_id = context["ITEMS"].get(pool_key, None)
            if not item_id:
                return {"message": "Invalid pool name."}, 400

            availability = check_swim_lane_availability(token, start_date, item_id, context)

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

        # Return both the message and the raw appointment data
        return {
            "message": message,
            "appointments": appointments
        }, 200
    elif appointments:
        # Multiple dates mode - return detailed information about each appointment
        appointment_details = []
        
        for appointment in appointments:
            pool_name = appointment.get("ClubName", "Unknown Pool")
            booked_resources = appointment.get("BookedResources", [])
            lane = booked_resources[0] if booked_resources else "Unknown Lane"
            time_str = appointment.get("StartDateTime", "Unknown Time")
            duration = appointment.get("DurationInMinutes", 60)  # Get duration from correct field

            # Parse and format the time
            try:
                appointment_time = datetime.datetime.fromisoformat(time_str)
                formatted_date = appointment_time.strftime("%Y-%m-%d")
                formatted_time = appointment_time.strftime("%I:%M %p")
            except ValueError:
                formatted_date = "Unknown Date"
                formatted_time = "Unknown Time"
            
            # Add the appointment details to the list
            appointment_details.append({
                "date": formatted_date,
                "time": formatted_time,
                "pool": pool_name,
                "lane": lane,
                "duration": duration
            })
        
        return {
            "appointments": appointments,
            "appointment_details": appointment_details
        }, 200
    else:
        if single_date_mode:
            logging.info(f"No appointment found for {start_date}")
            message = f"You do not have a swim lane appointment on {start_date}."
        else:
            logging.info(f"No appointments found between {start_date} and {end_date}")
            message = f"You do not have any swim lane appointments from {start_date} to {end_date}."
            
        return {
            "message": message,
            "appointments": []
        }, 200

def get_appointment_data(start_date, end_date=None, context=None):
    """
    Fetch scheduled swim lane appointment data for a given date.
    If end_date is not provided, it will be set to start_date (single day query).
    """
    token = login_via_context(context)
    if not token:
        return {"error": "Authentication failed"}, 401

    # If end_date not provided, set it to start_date (single day query)
    if not end_date:
        end_date = start_date

    # Localize the date to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    
    start_date_obj = eastern.localize(start_dt.replace(hour=0, minute=0, second=0, microsecond=0))
    end_date_obj = eastern.localize(end_dt.replace(hour=23, minute=59, second=59, microsecond=999999))

    # Format dates as ISO 8601 strings
    start_date_str = start_date_obj.isoformat(timespec='seconds')
    end_date_str = end_date_obj.isoformat(timespec='seconds')

    logging.info(f"Fetching appointments between {start_date_str} and {end_date_str}")
    appointments, status_code = get_appointments_schedule(token, start_date_str, end_date_str, context)

    if status_code != 200:
        return {"message": "Error retrieving swim lane information."}, status_code

    if appointments:
        appointment = appointments[0]  # Assuming only one appointment per day
        booked_resources = appointment.get("BookedResources", [])
        lane = booked_resources[0] if booked_resources else "Unknown Lane"
        time_str = appointment.get("StartDateTime", "Unknown Time")
        duration = appointment.get("DurationInMinutes", 60)  # Get duration from correct field

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
