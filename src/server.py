import datetime
import os
import json
import uuid
import logging
from flask import Flask, request, send_file, jsonify, g, render_template, redirect, url_for, session
from dotenv import load_dotenv
from src.drawing.visualize import generate_visualization
from src.logic.availabilityService import get_availability
from src.logic.appointmentService import get_appointments_schedule_action, get_appointment_data
from src.logic.bookingService import book_swim_lane_action
from src.logic.cancellationService import cancel_appointment_action
from src.constants import load_context_for_authenticated_user, load_context_for_registration_pages
from src.web.gateways.webLoginGateway import login_with_credentials
from src.web.services.familyService import get_family_members_action
from src.sql.authGateway import get_auth, store_auth  # Import the functions from authGateway
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        requested_api_key = auth_header.split(" ")[1] if auth_header else None
        g.context = load_context_for_authenticated_user(requested_api_key)
        
        if not g.context:
            return jsonify({"error": "Unauthorized"}), 401
        
        # Check if the API key is enabled
        if g.context.get("ENABLED") != 1:
            return jsonify({"error": "Account not enabled"}), 403
        
        mac_password = request.headers.get("mac_password")
        if mac_password:
            g.context["PASSWORD"] = mac_password
        
        return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("register"))

@app.route("/availability", methods=["GET"])
@require_api_key
def get_swim_lane_availability():
    """API Endpoint to return a visualization of swim lane availability."""
    pool_name = request.args.get("pool", "Indoor Pool")
    date_str = request.args.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))

    if pool_name == "Indoor":
        pool_name = "Indoor Pool"
    elif pool_name == "Outdoor": 
        pool_name = "Outdoor Pool"

    if pool_name not in g.context["ITEMS"]:
        return jsonify({"error": "Invalid pool name. Use 'Indoor Pool' or 'Outdoor Pool'."}), 400

    item_id = g.context["ITEMS"][pool_name]
    availability = get_availability(item_id, date_str, g.context)

    appt = get_appointment_data(date_str, g.context)

    img_io = generate_visualization(availability, pool_name, date_str, appt, g.context)
    return send_file(img_io, mimetype="image/png")

@app.route("/appointments", methods=["GET"])
@require_api_key
def get_user_appointments():
    """ API Endpoint to return scheduled swim lane appointments for a given date. """
    date_str = request.args.get("date")
    
    print(f"Fetching appointments for {date_str}")
    response, status_code = get_appointments_schedule_action(date_str, g.context)
    
    return jsonify(response), status_code

@app.route("/book", methods=["POST"])
@require_api_key
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
            print(f"Booking {location} {lane} for {duration} at {time} on {date}")

        if location == "Indoor":
            location = "Indoor Pool"
        elif location == "Outdoor": 
            location = "Outdoor Pool"

        print(f"Booking {location} {lane} for {duration} at {time} on {date}")

        response, status_code = book_swim_lane_action(date, time, duration, location, lane, g.context)
        
        return jsonify(response)

    except Exception as e:
        return jsonify({"message": f"Unexpected error: {str(e)}"}), 500

@app.route("/cancel", methods=["POST"])
@require_api_key
def cancel_lane():
    """ API Endpoint to cancel a swim lane appointment. """
    data = request.json
    appointment_date = data.get("date")
    print(f"Cancelling appointment for {appointment_date}")

    response, status_code = cancel_appointment_action(appointment_date, g.context)
    
    return jsonify(response), status_code

@app.route("/register", methods=["GET", "POST"])
def register():
    context = load_context_for_registration_pages()
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        # Check if the username already exists in the database
        auth_entry = get_auth(username)
        if auth_entry:
            return redirect(url_for("already_submitted"))
        
        response = login_with_credentials(username, password, context)
        if response:
            context["CUSTOMER_ID"] = str(response.get("CustomerId"))
            customer = {
                "Id": response.get("CustomerId"),
                "DisplayName": response.get("CustomerName", {}).get("DisplayName"),
                "Username": username
            }
            family_members = get_family_members_action(username, password, context)
            if family_members is None:
                family_members = []
            family_members.append(customer)  # Add the customer to the family_members list
            return render_template("registration.html", customer=customer, family_members=family_members)
        else:
            error = "Login failed. Please check your credentials."
            return render_template("registration.html", error=error)
    return render_template("registration.html")

@app.route("/select_family_member", methods=["POST"])
def select_family_member():
    selected_family_member = request.form["family_member"]
    username = request.form["username"]
    customer_id = request.form["customer_id"]
    
    # Generate a new API key
    new_api_key = uuid.uuid4().hex
    
    # Store the new entry in the database
    store_auth(username, new_api_key, customer_id, selected_family_member)
    logging.info(f"Stored new auth entry for {username}")
    
    return redirect(url_for("confirmation"))

@app.route("/confirmation", methods=["GET"])
def confirmation():
    return render_template("confirmation.html")

@app.route("/already_submitted", methods=["GET"])
def already_submitted():
    return render_template("already_submitted.html")

if __name__ == "__main__":
    print("Debug URL: http://127.0.0.1:5000/")
    print("Deploy URL: https://swimming-agent.onrender.com/")
    app.run(host="0.0.0.0", port=5000, debug=True)
