import matplotlib
matplotlib.use('Agg')  # Force non-GUI backend before importing pyplot

import matplotlib.pyplot as plt
import datetime
import pytz
from flask import Flask, request, send_file
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

TIME_SLOTS = [f"{hour % 12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}"
              for hour in range(8, 22) for minute in (0, 30)]


def format_api_time(api_time):
    """Convert API datetime format to match TIME_SLOTS."""
    dt = datetime.datetime.fromisoformat(api_time[:-6])  # Remove timezone offset
    dt = dt.astimezone(pytz.timezone("America/New_York"))  # Convert to local Eastern Time
    return dt.strftime("%I:%M %p").lstrip("0")  # Ensure no leading zero


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
    """Generate and save the swim lane availability visualization."""
    lanes = LANES_BY_POOL[pool_name]

    fig, ax = plt.subplots(figsize=(14, 8))

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
    ax.set_xticks(range(len(TIME_SLOTS)))
    ax.set_xticklabels(TIME_SLOTS, fontsize=8, rotation=45)
    ax.set_yticks(range(len(lanes)))
    ax.set_yticklabels(lanes, fontsize=10)

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
