import datetime
from flask import Flask, request, send_file, jsonify
from src.drawing.visualize import generate_visualization
from src.logic.availability import get_availability
from src.logic.scheduling import get_scheduled_appointments  # ✅ Import logic layer
app = Flask(__name__)
from src.constants import ITEMS

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

@app.route("/appointments", methods=["GET"])
def get_user_appointments():
    """ API Endpoint to return scheduled swim lane appointments for a given date range. """
    start_date = request.args.get("start_date", datetime.datetime.now().strftime("%Y-%m-%d"))
    end_date = request.args.get("end_date", start_date)  # Default to same day if not provided

    response, status_code = get_scheduled_appointments(start_date, end_date)
    
    if status_code == 200:
        appointments = response
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
            
            message = f"You have {lane} at {time} today."
        else:
            message = "You do not have a swim lane today."
    else:
        message = "Error retrieving swim lane information."

    return jsonify({"message": message}), status_code

if __name__ == "__main__":
    print("Debug URL: http://127.0.0.1:5000/appointments?start_date=2025-01-05")
    print("Deploy URL: https://swimming-agent.onrender.com/appointments?start_date=2025-01-05")

    print("Debug URL: http://127.0.0.1:5000/availability?pool=Indoor%20Pool")
    print("Deploy URL: https://swimming-agent.onrender.com/availability?pool=Indoor%20Pool")
    app.run(host="0.0.0.0", port=5000, debug=True)
