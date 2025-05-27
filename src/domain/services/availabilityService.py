import src.contextManager
import logging
from src.domain.gateways.availabilityGateway import check_swim_lane_availability  # Import swim lane function
from dateutil import parser  # Import this at the top
from src.domain.gateways.loginGateway import login_via_context
import pytz


def format_api_time(api_time):
    """Convert API time to Eastern Time and match TIME_SLOTS."""
    try:
        utc_dt = parser.isoparse(api_time)  # Automatically handles timezones
        et_dt = utc_dt.astimezone(pytz.timezone("America/New_York"))  # Convert to ET
        return et_dt.strftime("%I:%M %p").lstrip("0")  # Match TIME_SLOTS format
    except Exception as e:
        logging.info(f"Error parsing datetime: {api_time}, Error: {e}")
        return None  # Return None to handle errors gracefully

def get_availability(item_id, date_str, context):
    """Fetch availability data for a given pool type and date."""
    try:
        token = login_via_context(context)
        if not token:
            logging.warning("Failed to get authentication token")
            return {}

        data = check_swim_lane_availability(token, date_str, item_id, context)

        # Initialize all time slots as unavailable
        availability = {time: [] for time in context["TIME_SLOTS"]}

        # ✅ Handle case where Availability is missing or empty
        if not data or "Availability" not in data or not data["Availability"]:
            logging.info(f"⚠️ No availability data returned for ItemId {item_id} on {date_str}")
            return availability  # Return empty availability instead of breaking

        # Safely access availability data
        availability_data = data["Availability"]
        if not isinstance(availability_data, list) or len(availability_data) == 0:
            logging.info(f"⚠️ Invalid availability data structure for ItemId {item_id} on {date_str}")
            return availability

        available_times = availability_data[0].get("AvailableTimes")
        if not available_times:
            logging.info(f"⚠️ No available times in data for ItemId {item_id} on {date_str}")
            return availability

        for slot in available_times:
            if not slot or "StartDateTime" not in slot:
                continue
                
            formatted_time = format_api_time(slot["StartDateTime"])
            if formatted_time and formatted_time in availability:
                possible_selections = slot.get("PossibleBookSelections", [])
                for lane_group in possible_selections:
                    if isinstance(lane_group, list):
                        for lane in lane_group:
                            if lane and "Name" in lane:
                                lane_name = lane["Name"]
                                availability[formatted_time].append(lane_name)

        return availability
        
    except Exception as e:
        logging.error(f"Error in get_availability for ItemId {item_id} on {date_str}: {e}", exc_info=True)
        return {time: [] for time in context.get("TIME_SLOTS", [])}