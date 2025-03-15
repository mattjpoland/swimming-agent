import src.constants
from src.api.availabilityGateway import check_swim_lane_availability  # Import swim lane function
from dateutil import parser  # Import this at the top
from src.api.loginGateway import login
import pytz


def format_api_time(api_time):
    """Convert API time to Eastern Time and match TIME_SLOTS."""
    try:
        utc_dt = parser.isoparse(api_time)  # Automatically handles timezones
        et_dt = utc_dt.astimezone(pytz.timezone("America/New_York"))  # Convert to ET
        return et_dt.strftime("%I:%M %p").lstrip("0")  # Match TIME_SLOTS format
    except Exception as e:
        print(f"Error parsing datetime: {api_time}, Error: {e}")
        return None  # Return None to handle errors gracefully

def get_availability(item_id, date_str, context):
    """Fetch availability data for a given pool type and date."""
    token = login(context)
    if not token:
        return {}

    data = check_swim_lane_availability(token, date_str, item_id, context)

    # Initialize all time slots as unavailable
    availability = {time: [] for time in context["TIME_SLOTS"]}

    # ✅ Handle case where Availability is missing or empty
    if not data or "Availability" not in data or not data["Availability"]:
        print(f"⚠️ No availability data returned for ItemId {item_id} on {date_str}")
        return availability  # Return empty availability instead of breaking

    for slot in data["Availability"][0]["AvailableTimes"]:
        formatted_time = format_api_time(slot["StartDateTime"])
        if formatted_time in availability:
            for lane_group in slot["PossibleBookSelections"]:
                for lane in lane_group:
                    lane_name = lane["Name"]
                    availability[formatted_time].append(lane_name)

    return availability