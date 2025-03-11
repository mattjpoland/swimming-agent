import matplotlib.pyplot as plt
import datetime
import pytz
from src.api.login import login, check_swim_lane_availability

# Constants
LANES_BY_POOL = {
    "Indoor Pool": ["Indoor Lane 1", "Indoor Lane 2", "Indoor Lane 3", "Indoor Lane 4", "Indoor Lane 5", "Indoor Lane 6"],
    "Outdoor Pool": ["Outdoor Lane 1", "Outdoor Lane 2", "Outdoor Lane 3", "Outdoor Lane 4", "Outdoor Lane 5", "Outdoor Lane 6"]
}

TIME_SLOTS = [f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"
              for hour in range(8, 22) for minute in (0, 30)]

ITEMS = {
    "Outdoor Pool": 359,
    "Indoor Pool": 366
}

# Prompt the user for a date (default to today)
def get_date():
    default_date = datetime.datetime.now().strftime("%Y-%m-%d")
    user_input = input(f"Enter date (YYYY-MM-DD) [default: {default_date}]: ").strip()
    return user_input if user_input else default_date  # Use input date or default to today

# Converts API datetime format to match TIME_SLOTS
def format_api_time(api_time):
    dt = datetime.datetime.fromisoformat(api_time[:-6])  # Remove timezone offset
    dt = dt.astimezone(pytz.timezone("America/New_York"))  # Convert to local Eastern Time
    return dt.strftime("%I:%M %p").lstrip("0")  # Ensure no leading zero

# Fetch availability data for a given pool type
def get_availability(item_id, date_str):
    token = login()
    if not token:
        print("Failed to retrieve auth token.")
        return {}

    data = check_swim_lane_availability(token, date_str, item_id)

    availability = {time: [] for time in TIME_SLOTS}  # Initialize all time slots

    if data and "Availability" in data:
        for slot in data["Availability"][0]["AvailableTimes"]:
            formatted_time = format_api_time(slot["StartDateTime"])

            if formatted_time in availability:
                for lane_group in slot["PossibleBookSelections"]:
                    for lane in lane_group:
                        lane_name = lane["Name"]
                        if lane_name in LANES_BY_POOL["Indoor Pool"] + LANES_BY_POOL["Outdoor Pool"]:
                            availability[formatted_time].append(lane_name)

    print(f"\nFinal Mapped Availability for Item {item_id} on {date_str}:")
    for time, lanes in availability.items():
        print(f"{time}: {lanes}")  # Check if lanes are mapped correctly

    return availability

# Draw the pools using API data
def draw_pools():
    selected_date = get_date()  # Get user-selected date
    fig, axes = plt.subplots(2, 1, figsize=(14, 16))  # Two plots: Outdoor and Indoor

    for ax, (pool_name, item_id) in zip(axes, ITEMS.items()):
        lanes = LANES_BY_POOL[pool_name]  # Use correct lane names for each pool
        availability = get_availability(item_id, selected_date)

        for i, lane in enumerate(lanes):
            for j, time in enumerate(TIME_SLOTS):
                is_available = lane in availability.get(time, [])
                color = "green" if is_available else "red"
                rect = plt.Rectangle((j, i), 1, 1, facecolor=color, edgecolor="black")
                ax.add_patch(rect)
                ax.text(j + 0.5, i + 0.5, lane.split()[-1], ha="center", va="center", fontsize=9, color="white")

        # Configure axes
        ax.set_xlim(0, len(TIME_SLOTS))
        ax.set_ylim(0, len(lanes))

        # Center labels
        ax.set_xticks([x + 0.5 for x in range(len(TIME_SLOTS))])  # Offset X labels
        ax.set_xticklabels(TIME_SLOTS, fontsize=8, rotation=45, ha="right")

        ax.set_yticks([y + 0.5 for y in range(len(lanes))])  # Offset Y labels
        ax.set_yticklabels(lanes, fontsize=10, va="center")

        # Title includes pool name and selected date
        ax.set_title(f"{pool_name} Availability for {selected_date}", fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.show()

# Run the visualization
if __name__ == "__main__":
    draw_pools()
