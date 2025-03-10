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

    availability = {time: [] for time in TIME_SLOTS}  # Initialize all time slots

    if data and "Availability" in data:
        for slot in data["Availability"][0]["AvailableTimes"]:
            formatted_time = format_api_time(slot["StartDateTime"])

            if formatted_time in availability:
                for lane_group in slot["PossibleBookSelections"]:
                    for lane in lane_group:
                        lane_name = lane["Name"]
                        availability[formatted_time].append(lane_name)

    return availability


def generate_visualization(availability, pool_name, date_str):
    """Generate and save the swim lane availability visualization with centered axes labels."""
    lanes = LANES_BY_POOL[pool_name]

    fig, ax = plt.subplots(figsize=(14, 8))

    for i, lane in enumerate(reversed(lanes)):  # Reverse for top-down display
        for j, time in enumerate(TIME_SLOTS):
            is_available = lane in availability.get(time, [])
            color = "green" if is_available else "red"
            rect = plt.Rectangle((j, i), 1, 1, facecolor=color, edgecolor="black")
            ax.add_patch(rect)
            ax.text(j + 0.5, i + 0.5, lane.split()[-1], ha="center", va="center", fontsize=9, color="white")

    # Correct Axis Limits (Prevent Offset)
    ax.set_xlim(0, len(TIME_SLOTS))
    ax.set_ylim(0, len(lanes))
    
    # Configure tick labels
    ax.set_xticks(range(len(TIME_SLOTS)))
    ax.set_xticklabels(TIME_SLOTS, fontsize=8, rotation=45, ha="right")
    ax.set_yticks(range(len(lanes)))
    ax.set_yticklabels(reversed(lanes), fontsize=10)  # Show lanes top-down

    # Center the x and y labels
    ax.set_xlabel("Time Slots", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_ylabel("Lanes", fontsize=12, fontweight="bold", labelpad=10)
    
    # Move only the labels, NOT the entire grid
    ax.xaxis.set_label_coords(0.5, -0.08)  # Center x-label
    ax.yaxis.set_label_coords(-0.08, 0.5)  # Center y-label

    # Set title
    ax.set_title(f"{pool_name} Availability for {date_str}", fontsize=14, fontweight="bold")

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
    app.run(host="0.0.0.0", port=5000, debug=True)
