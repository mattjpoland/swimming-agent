from flask import Blueprint, jsonify, request, g, send_file
from datetime import datetime
import logging
import io
import barcode
from barcode.writer import ImageWriter
import json
from src.domain.services.availabilityService import get_availability
from src.domain.services.appointmentService import get_appointments_schedule_action, get_appointment_data
from src.domain.services.bookingService import book_swim_lane_action
from src.domain.services.cancellationService import cancel_appointment_action
from src.domain.services.membershipService import get_barcode_id_action
from src.domain.services.weatherService import get_weather_for_zip, get_weather_forecast_for_date
from src.domain.drawing.availabilityVisualGenerator import generate_visualization, combine_visualizations
from src.decorators import require_api_key
from src.domain.sql.authGateway import get_auth  # Assuming this retrieves user data
from src.web.gateways.webLoginGateway import login_with_credentials  # Import login gateway
from src.domain.gateways.loginGateway import login_via_context, login_via_credentials  # Import the updated login function
from src.domain.drawing.barcodeGenerator import generate_barcode_image
from src.domain.services.ragIndexingService import rebuild_index_from_db  # Make sure this import path matches your project
from src.domain.services.ragQueryingService import debug_rag_status, debug_query

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

        appt = get_appointment_data(date_str, date_str, g.context)
        

        indoor_img = generate_visualization(indoor_availability, indoor_pool_name, date_str, appt, g.context)
        outdoor_img = generate_visualization(outdoor_availability, outdoor_pool_name, date_str, appt, g.context)

        combined_img_io = combine_visualizations(indoor_img, outdoor_img)
        return send_file(combined_img_io, mimetype="image/png")

    if pool_name not in g.context["ITEMS"]:
        return jsonify({"error": "Invalid pool name. Use 'Indoor Pool', 'Outdoor Pool', or 'Both Pools'."}), 400

    item_id = g.context["ITEMS"][pool_name]
    availability = get_availability(item_id, date_str, g.context)
    appt = get_appointment_data(date_str, date_str, g.context)

    img_io = generate_visualization(availability, pool_name, date_str, appt, g.context)
    return send_file(img_io, mimetype="image/png")

@api_bp.route("/appointments", methods=["GET"])
@require_api_key
def get_user_appointments():
    """API Endpoint to return scheduled swim lane appointments for a given date."""
    date_str = request.args.get("date")
    response, status_code = get_appointments_schedule_action(date_str, date_str, g.context)
    return jsonify(response), status_code

@api_bp.route("/book", methods=["POST"])
@require_api_key
def book_lane():
    """API Endpoint to book a swim lane."""
    data = request.json or {}
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
    data = request.json or {}
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
        # Generate the barcode image using the helper function
        barcode_image = generate_barcode_image(barcode_id)

        # Return the barcode image as a response
        return send_file(barcode_image, mimetype="image/png")

    except RuntimeError as e:
        logging.exception(f"Error generating barcode: {str(e)}")
        return jsonify({"error": f"Failed to generate barcode: {str(e)}"}), 500

@api_bp.route("/weather", methods=["GET"])
@require_api_key
def get_weather():
    """
    API Endpoint to fetch the current weather for ZIP code 48823.
    """
    zip_code = "48823"
    country_code = "us"

    try:
        # Call the weather service to get formatted weather data
        weather = get_weather_for_zip(zip_code, country_code)

        # Return the weather data as JSON
        return jsonify({
            "status": "success",
            "weather": weather
        }), 200

    except RuntimeError as e:
        logging.exception(f"Error in weather service: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to fetch weather data. Please try again later."
        }), 500

@api_bp.route("/weather/forecast", methods=["GET"])
@require_api_key
def get_weather_forecast():
    """
    API Endpoint to fetch the weather forecast for a specific future date.
    """
    zip_code = "48823"
    country_code = "us"
    target_date = request.args.get("date")  # Expecting a date in YYYY-MM-DD format

    if not target_date:
        return jsonify({
            "status": "error",
            "message": "Missing required 'date' parameter in YYYY-MM-DD format."
        }), 400

    try:
        # Call the weather service to get the forecast for the target date
        forecast = get_weather_forecast_for_date(zip_code, country_code, target_date)

        # Return the forecast data as JSON
        return jsonify({
            "status": "success",
            "forecast": forecast
        }), 200

    except RuntimeError as e:
        logging.exception(f"Error in weather forecast service: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to fetch weather forecast. Please try again later."
        }), 500

@api_bp.route("/rebuild-index", methods=["POST"])
def api_rebuild_index():
    success, msg = rebuild_index_from_db()
    if success:
        logging.info(f"/api/rebuild-index: {msg}")
        return jsonify({"status": "success", "message": msg})
    else:
        logging.error(f"/api/rebuild-index failed: {msg}")
        return jsonify({"status": "error", "message": msg}), 500

@api_bp.route('/rag-status', methods=['GET'])
def get_rag_status():
    """Get detailed status of the RAG system"""
    try:
        debug_rag_status()
        return jsonify({
            "status": "success",
            "message": "RAG status logged. Check application logs for details."
        })
    except Exception as e:
        logging.error(f"Failed to get RAG status: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api_bp.route('/debug-query', methods=['POST'])
def debug_query_route():
    """Debug a RAG query"""
    try:
        data = request.get_json() or {}
        query = data.get('query')
        if not query:
            return jsonify({"error": "No query provided"}), 400
            
        debug_query(query)
        return jsonify({
            "status": "success",
            "message": "Query debug info logged. Check application logs."
        })
        
    except Exception as e:
        logging.error(f"Debug query error: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route("/schedule/auto-book", methods=["POST"])
@require_api_key
def auto_book_lanes():
    """API Endpoint for auto-booking scheduled swim lanes for the current day."""
    from domain.services.autoBookingService import process_auto_booking
    
    try:
        results = process_auto_booking()
        return jsonify({
            "status": "success", 
            "message": f"Auto-booking process completed with {len(results)} results",
            "results": results
        }), 200
    except Exception as e:
        logging.exception(f"Auto-booking process failed: {str(e)}")
        return jsonify({"status": "error", "message": f"Auto-booking process failed: {str(e)}"}), 500

@api_bp.route("/cron_schedule_swim_lanes", methods=["POST"])
@require_api_key
def cron_schedule_swim_lanes():
    """
    CRON Endpoint for automated swim lane scheduling.
    This endpoint is designed to be called by external CRON services.
    It queues the auto-booking process as a background task using Celery.
    """
    try:
        logging.info("CRON auto-booking process queued")
        
        # Import and queue the Celery task
        from worker.tasks import run_auto_booking
        
        # Queue the task for background execution
        task = run_auto_booking.delay()
        
        logging.info(f"Auto-booking task queued with ID: {task.id}")
        
        return jsonify({
            "status": "accepted", 
            "message": "Auto-booking process has been queued for background execution",
            "task_id": task.id
        }), 202
    except Exception as e:
        logging.exception(f"Failed to queue auto-booking task: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Failed to queue auto-booking task: {str(e)}",
            "error_type": type(e).__name__
        }), 500

@api_bp.route("/task-status/<task_id>", methods=["GET"])
@require_api_key
def get_task_status(task_id):
    """
    Get the status of a background task by its ID.
    """
    try:
        from worker.tasks import run_auto_booking
        
        # Get the task result
        task_result = run_auto_booking.AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {
                'task_id': task_id,
                'state': task_result.state,
                'status': 'Task is pending...'
            }
        elif task_result.state == 'PROGRESS':
            response = {
                'task_id': task_id,
                'state': task_result.state,
                'status': task_result.info.get('status', 'Task is running...')
            }
        elif task_result.state == 'SUCCESS':
            response = {
                'task_id': task_id,
                'state': task_result.state,
                'result': task_result.result
            }
        else:
            # Task failed or was revoked
            response = {
                'task_id': task_id,
                'state': task_result.state,
                'error': str(task_result.info)
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        logging.exception(f"Failed to get task status for {task_id}: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Failed to get task status: {str(e)}"
        }), 500

