import matplotlib
matplotlib.use('Agg')  # Force non-GUI backend before importing pyplot

import matplotlib.pyplot as plt
import datetime
from dateutil import parser  # Import this at the top
import pytz
from flask import Flask, request, send_file, jsonify
from src.api import login, check_swim_lane_availability
import io

app = Flask(__name__)

# Constants
LANES_BY_POOL = {
    "Indoor Pool": ["Indoor Lane 1", "Indoor Lane 2", "Indoor Lane 3", "Indoor Lane 4", "Indoor Lane 5", "Indoor Lane 6"],
    "Outdoor Pool": ["Outdoor Lane 1", "Outdoor Lane 2", "Outdoor Lane 3", "Outdoor Lane 4", "Outdoor Lane 5", "Outdoor Lane 6"]
}

ITEMS = {
    "Outdoor Pool": 359,
    "Indoor Pool": 366
}

# Define correct time slots (Eastern Time)
TIME_SLOTS = [datetime.time(hour, minute).strftime("%I:%M %p").lstrip("0")
              for hour in range(8, 22) for minute in (0, 30)]

def format_api_time(api_time):
    """Convert API time to Eastern Time and match TIME_SLOTS."""
    try:
        utc_dt = parser.isoparse(api_time)  # Automatically handles timezones
        et_dt = utc_dt.astimezone(pytz.timezone("America/New_York"))  # Convert to ET
        return et_dt.strftime("%I:%M %p").lstrip("0")  # Match TIME_SLOTS format
    except Exception as e:
        print(f"Error parsing datetime: {api_time}, Error: {e}")
        return None  # Return None to handle errors gracefully

def get_availability(item_id, date_str):
    """Fetch availability data for a given pool type and date."""
    token = login()
    if not token:
        return {}

    data = check_swim_lane_availability(token, date_str, item_id)

    # Initialize all time slots as unavailable
    availability = {time: [] for time in TIME_SLOTS}

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


def generate_visualization(availability, pool_name, date_str):
    """Generate and save the swim lane availability visualization with a clean reset."""
    lanes = LANES_BY_POOL[pool_name]
    num_lanes = len(lanes)
    num_times = len(TIME_SLOTS)

    fig, ax = plt.subplots(figsize=(14, 8))

    # Draw the table cells
    for i, lane in enumerate(reversed(lanes)):  # Reverse for top-down display
        for j, time in enumerate(TIME_SLOTS):
            is_available = lane in availability.get(time, [])
            color = "green" if is_available else "red"
            rect = plt.Rectangle((j, i), 1, 1, facecolor=color, edgecolor="black")
            ax.add_patch(rect)
            ax.text(j + 0.5, i + 0.5, lane.split()[-1], ha="center", va="center", fontsize=9, color="white")

    # ✅ Keep Grid Aligned (Prevent Shifting)
    ax.set_xlim(0, num_times)
    ax.set_ylim(0, num_lanes)

    # ✅ Standard Tick Labels
    ax.set_xticks(range(num_times))
    ax.set_xticklabels(TIME_SLOTS, fontsize=8, rotation=45, ha="center")

    ax.set_yticks(range(num_lanes))
    ax.set_yticklabels(reversed(lanes), fontsize=10, va="center")

    # Adjust subplot parameters to center the axes
    plt.subplots_adjust(left=0.15, right=0.85, top=0.85, bottom=0.15)

    # ✅ Standard Axis Labels (No Offset Adjustments)
    ax.set_xlabel("Time Slots", fontsize=14, fontweight="bold")
    ax.set_ylabel("Lanes", fontsize=14, fontweight="bold")

    # ✅ Standard Title Placement
    ax.set_title(f"{pool_name} Availability for {date_str}", fontsize=16, fontweight="bold")

    # ✅ Default Spines and Gridlines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    # Save to a temporary in-memory file
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png', bbox_inches="tight")
    img_io.seek(0)

    plt.close(fig)  # Close the figure to free memory

    return img_io



@app.route("/availability", methods=["GET"])
def get_swim_lane_availability():
    """API Endpoint to return a visualization of swim lane availability."""
    pool_name = request.args.get("pool", "Indoor Pool")
    date_str = request.args.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))

    if pool_name not in ITEMS:
        return jsonify({"error": "Invalid pool name. Use 'Indoor Pool' or 'Outdoor Pool'."}), 400

    item_id = ITEMS[pool_name]
    availability = get_availability(item_id, date_str)

    img_io = generate_visualization(availability, pool_name, date_str)
    return send_file(img_io, mimetype="image/png")

if __name__ == "__main__":
    print("Debug URL: http://127.0.0.1:5000/availability?pool=Indoor%20Pool")
    print("Deploy URL: https://swimming-agent.onrender.com/availability?pool=Indoor%20Pool")
    app.run(host="0.0.0.0", port=5000, debug=True)
