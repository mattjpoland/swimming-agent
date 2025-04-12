from flask import Blueprint, jsonify, request, g, send_file
from datetime import datetime
import logging
import io
import barcode
from barcode.writer import ImageWriter
from src.api.logic.availabilityService import get_availability
from src.api.logic.appointmentService import get_appointments_schedule_action, get_appointment_data
from src.api.logic.bookingService import book_swim_lane_action
from src.api.logic.cancellationService import cancel_appointment_action
from src.api.logic.membershipService import get_barcode_id_action
from src.drawing.visualize import generate_visualization, combine_visualizations
from src.decorators import require_api_key
from src.sql.authGateway import get_auth  # Assuming this retrieves user data
from src.web.gateways.webLoginGateway import login_with_credentials  # Import login gateway
from src.api.gateways.loginGateway import login_via_context, login_via_credentials  # Import the updated login function

api_bp = Blueprint('api', __name__)

@api_bp.route("/availability", methods=["GET"])
@require_api_key
def get_swim_lane_availability():
    """API Endpoint to return a visualization of swim lane availability."""
    pool_name = request.args.get("pool", "Indoor Pool")
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

    if pool_name in ["Indoor", "Outdoor"]:
        pool_name = f"{pool_name} Pool"

    if pool_name == "Both" or pool_name == "Both Pools":
        indoor_pool_name = "Indoor Pool"
        outdoor_pool_name = "Outdoor Pool"

        indoor_item_id = g.context["ITEMS"][indoor_pool_name]
        outdoor_item_id = g.context["ITEMS"][outdoor_pool_name]

        indoor_availability = get_availability(indoor_item_id, date_str, g.context)
        outdoor_availability = get_availability(outdoor_item_id, date_str, g.context)

        indoor_appt = get_appointment_data(date_str, g.context)
        outdoor_appt = get_appointment_data(date_str, g.context)

        indoor_img = generate_visualization(indoor_availability, indoor_pool_name, date_str, indoor_appt, g.context)
        outdoor_img = generate_visualization(outdoor_availability, outdoor_pool_name, date_str, outdoor_appt, g.context)

        combined_img_io = combine_visualizations(indoor_img, outdoor_img)
        return send_file(combined_img_io, mimetype="image/png")

    if pool_name not in g.context["ITEMS"]:
        return jsonify({"error": "Invalid pool name. Use 'Indoor Pool', 'Outdoor Pool', or 'Both Pools'."}), 400

    item_id = g.context["ITEMS"][pool_name]
    availability = get_availability(item_id, date_str, g.context)
    appt = get_appointment_data(date_str, g.context)

    img_io = generate_visualization(availability, pool_name, date_str, appt, g.context)
    return send_file(img_io, mimetype="image/png")

@api_bp.route("/appointments", methods=["GET"])
@require_api_key
def get_user_appointments():
    """API Endpoint to return scheduled swim lane appointments for a given date."""
    date_str = request.args.get("date")
    response, status_code = get_appointments_schedule_action(date_str, g.context)
    return jsonify(response), status_code

@api_bp.route("/book", methods=["POST"])
@require_api_key
def book_lane():
    """API Endpoint to book a swim lane."""
    data = request.json
    date = data.get("date")
    time = data.get("time")
    duration = data.get("duration", "60")
    location = data.get("location", "Indoor Pool")
    lane = data.get("lane", "1")

    if location in ["Indoor", "Outdoor"]:
        location = f"{location} Pool"

    if lane.isdigit():
        lane = f"Lane {lane}"
    if duration.isdigit():
        duration = f"{duration} Min"

    # log date, time, duration, location, lane
    logging.info(f"Booking request: {date}, {time}, {duration}, {location}, {lane}")

    response, status_code = book_swim_lane_action(date, time, duration, location, lane, g.context)
    return jsonify(response), status_code

@api_bp.route("/cancel", methods=["POST"])
@require_api_key
def cancel_lane():
    """API Endpoint to cancel a swim lane appointment."""
    data = request.json
    appointment_date = data.get("date")
    response, status_code = cancel_appointment_action(appointment_date, g.context)
    return jsonify(response), status_code

@api_bp.route("/barcode", methods=["GET"])
@require_api_key
def generate_barcode():
    """
    API Endpoint to generate a barcode image for a user's BarcodeId using Code 39.
    """
    # Get the barcode ID using the membership service
    response, status_code = get_barcode_id_action(g.context)
    
    # If there was an error, return it
    if status_code != 200:
        return jsonify(response), status_code
    
    # Extract the barcode ID from the response
    barcode_id = response.get("barcode_id")
    
    # Log the original barcode ID for verification
    logging.info(f"Generating barcode for ID: {barcode_id}")
    
    try:
        # Import the barcode libraries
        import barcode
        from barcode.writer import ImageWriter
        
        # Generate the barcode image using Code 39 without checksum
        barcode_class = barcode.get_barcode_class('code39')
        
        # Create the ImageWriter instance without options parameter
        writer = ImageWriter()
        
        # Set writer attributes individually (for older versions)
        writer.quiet_zone = 2.5
        writer.text = True  # Enable text rendering
        
        # Try with add_checksum parameter first
        try:
            barcode_format = barcode_class(barcode_id, writer=writer, add_checksum=False)
        except TypeError:
            # Fallback for older versions that don't support add_checksum parameter
            barcode_format = barcode_class(barcode_id, writer=writer)
            # Try to set the property after initialization
            try:
                barcode_format.add_checksum = False
            except (AttributeError, TypeError):
                logging.warning("Could not disable checksum through property, using default behavior")
        
        # Verify the encoded data doesn't have an added checksum
        try:
            encoded_data = barcode_format.get_fullcode()
            logging.info(f"Encoded barcode data: {encoded_data}")
            
            # Validate that no checksum was added
            if encoded_data != barcode_id:
                logging.warning(f"WARNING: Encoded data ({encoded_data}) doesn't match original ID ({barcode_id})")
        except (AttributeError, TypeError):
            logging.warning("Could not verify encoded data, continuing with generation")
        
        # Generate the barcode image
        barcode_image = io.BytesIO()
        barcode_format.write(barcode_image)
        barcode_image.seek(0)
        
        # Return the barcode image as a response
        return send_file(barcode_image, mimetype="image/png")
    
    except Exception as e:
        logging.exception(f"Error generating barcode: {str(e)}")
        return jsonify({"error": f"Failed to generate barcode: {str(e)}"}), 500