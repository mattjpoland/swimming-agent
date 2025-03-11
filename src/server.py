import datetime
from flask import Flask, request, send_file, jsonify
from src.drawing.visualize import generate_visualization
from src.logic.availabilityService import get_availability
from src.logic.schedulingService import get_appointments_schedule_action, book_swim_lane_action, cancel_appointment_action
app = Flask(__name__)
from src.constants import ITEMS

@app.route("/availability", methods=["GET"])
def get_swim_lane_availability():
    """API Endpoint to return a visualization of swim lane availability."""
    pool_name = request.args.get("pool", "Indoor Pool")
    date_str = request.args.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))

    if pool_name == "Indoor":
        pool_name = "Indoor Pool"
    elif pool_name == "Outdoor": 
        pool_name = "Outdoor Pool"

    if pool_name not in ITEMS:
        return jsonify({"error": "Invalid pool name. Use 'Indoor Pool' or 'Outdoor Pool'."}), 400

    item_id = ITEMS[pool_name]
    availability = get_availability(item_id, date_str)

    img_io = generate_visualization(availability, pool_name, date_str)
    return send_file(img_io, mimetype="image/png")

@app.route("/appointments", methods=["GET"])
def get_user_appointments():
    """ API Endpoint to return scheduled swim lane appointments for a given date range. """
    start_date_str = request.args.get("start_date", datetime.datetime.now().strftime("%Y-%m-%d"))
    end_date_str = request.args.get("end_date", (datetime.datetime.strptime(start_date_str, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))

    response, status_code = get_appointments_schedule_action(start_date_str, end_date_str)
    
    return jsonify(response), status_code

@app.route("/book", methods=["POST"])
def book_lane():
    """ API Endpoint to book a swim lane. """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid request. Expected JSON payload."}), 400

        date = data.get("date")  # Must be YYYY-MM-DD
        time = data.get("time")  # Must be a valid slot like "10:00 AM"
        duration = data.get("duration", "60")  # Default to 60 minutes
        location = data.get("location", "Indoor Pool")
        lane = data.get("lane", "1")

        # Ensure lane is formatted as "Lane 1", "Lane 2", etc.
        if lane.isdigit():
            lane = f"Lane {lane}"

        # Ensure duration is formatted as "30 Min", "60 Min", etc.
        if duration.isdigit():
            duration = f"{duration} Min"

        response, status_code = book_swim_lane_action(date, time, duration, location, lane)
        
        return jsonify(response)

    except Exception as e:
        return jsonify({"message": f"Unexpected error: {str(e)}"}), 500

@app.route("/cancel", methods=["POST"])
def cancel_lane():
    """ API Endpoint to cancel a swim lane appointment. """
    data = request.json
    appointment_date = data.get("date")

    response, status_code = cancel_appointment_action(appointment_date)
    
    return jsonify(response), status_code

if __name__ == "__main__":
    print("Debug URL: http://127.0.0.1:5000/appointments?start_date=2025-01-05")
    print("Deploy URL: https://swimming-agent.onrender.com/appointments?start_date=2025-01-05")

    print("Debug URL: http://127.0.0.1:5000/availability?pool=Indoor%20Pool")
    print("Deploy URL: https://swimming-agent.onrender.com/availability?pool=Indoor%20Pool")
    app.run(host="0.0.0.0", port=5000, debug=True)
