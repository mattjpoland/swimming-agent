import os
import datetime
import logging
from src.domain.sql.scheduleGateway import get_all_active_schedules
from src.domain.sql.authGateway import get_mac_password
from src.domain.services.bookingService import book_swim_lane_action
import pytz

def get_day_of_week():
    """Get the current day of the week in lowercase."""
    eastern = pytz.timezone('US/Eastern')
    today = datetime.datetime.now(eastern)
    return today.strftime("%A").lower()

def process_auto_booking():
    """
    Process automated bookings based on saved schedules.
    This function retrieves all active schedules and books lanes
    for the current day of the week.
    """
    logging.info("Starting automated lane booking process")
    
    # Get current day of week
    today = get_day_of_week()
    logging.info(f"Processing bookings for {today}")
    
    # Get all active schedules
    schedules = get_all_active_schedules()
    logging.info(f"Found {len(schedules)} total schedules")
    
    results = []
    for schedule in schedules:
        username = schedule["username"]
        today_schedule = schedule.get(today)
        
        if not today_schedule:
            logging.info(f"No booking scheduled for {username} on {today}")
            continue
        
        # Get the MAC password from auth_data table
        mac_password = get_mac_password(username)
        if not mac_password:
            logging.warning(f"Missing MAC password for user {username}, cannot proceed with booking")
            results.append({
                "username": username,
                "status": "error",
                "message": "Missing MAC password"
            })
            continue
        
        # Extract booking details
        pool = today_schedule.get("pool")
        lane = today_schedule.get("lane")
        time = today_schedule.get("time")
        
        if not all([pool, lane, time]):
            logging.warning(f"Incomplete booking information for {username} on {today}")
            results.append({
                "username": username,
                "status": "error",
                "message": "Incomplete booking information"
            })
            continue
        
        # Format date for booking
        eastern = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(eastern)
        booking_date = now.strftime("%Y-%m-%d")
        
        # Format time for booking (convert from 24-hour to 12-hour format)
        try:
            hour, minute, second = map(int, time.split(':'))
            if hour == 0:
                time_12hr = f"12:{minute:02d} AM"
            elif hour < 12:
                time_12hr = f"{hour}:{minute:02d} AM"
            elif hour == 12:
                time_12hr = f"12:{minute:02d} PM"
            else:
                time_12hr = f"{hour-12}:{minute:02d} PM"
        except ValueError:
            logging.error(f"Invalid time format for {username}: {time}")
            results.append({
                "username": username,
                "status": "error",
                "message": f"Invalid time format: {time}"
            })
            continue
        
        # Create a context with user credentials
        context = {
            "COMPANY_ID": os.getenv("COMPANY_ID"),
            "CUSTOMER_ID": os.getenv("CUSTOMER_ID"),
            "MAC_USERNAME": username,
            "MAC_PASSWORD": mac_password,
            "RESOURCE_TYPE_IDS": {
                "Indoor Pool": 75,
                "Outdoor Pool": 76
            },
            "LOCATION_SHORT_NAMES": {
                "Indoor Pool": "IP",
                "Outdoor Pool": "OP"
            },
            "APPOINTMENT_ITEMS": {
                "30 IP Lane Reservation": 1193,
                "60 IP Lane Reservation": 1194,
                "30 OP Lane Reservation": 1195,
                "60 OP Lane Reservation": 1196
            },
            "ASSIGNED_RESOURCE_IDS": {
                "30 IP": 135,
                "60 IP": 136,
                "30 OP": 139,
                "60 OP": 140
            },
            "BOOK_SELECTION_IDS": {
                "IP Lane 1": 7700,
                "IP Lane 2": 7701,
                "IP Lane 3": 7702,
                "IP Lane 4": 7703,
                "IP Lane 5": 7704,
                "IP Lane 6": 7705,
                "IP Lane 7": 7706,
                "IP Lane 8": 7707,
                "OP Lane 1": 7708,
                "OP Lane 2": 7709,
                "OP Lane 3": 7710,
                "OP Lane 4": 7711,
                "OP Lane 5": 7712,
                "OP Lane 6": 7713,
                "OP Lane 7": 7714,
                "OP Lane 8": 7715
            },
            "ITEMS": {
                "Indoor Pool": 1193,
                "Outdoor Pool": 1195
            }
        }
        
        # Default duration (60 minutes)
        duration = "60"
        
        try:
            logging.info(f"Attempting to book {lane} at {pool} for {username} on {booking_date} at {time_12hr}")
            
            # Call booking service
            response, status = book_swim_lane_action(
                booking_date, 
                time_12hr,
                duration, 
                pool, 
                lane, 
                context
            )
            
            if status == 200:
                logging.info(f"Successfully booked {lane} at {pool} for {username}")
                results.append({
                    "username": username,
                    "status": "success",
                    "message": response.get("message", "Booking successful")
                })
            else:
                logging.error(f"Failed to book for {username}: {response}")
                results.append({
                    "username": username,
                    "status": "error",
                    "message": response.get("message", "Booking failed")
                })
                
        except Exception as e:
            logging.exception(f"Error during booking for {username}: {str(e)}")
            results.append({
                "username": username,
                "status": "error", 
                "message": f"Exception: {str(e)}"
            })
    
    return results