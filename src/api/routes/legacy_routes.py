from flask import Blueprint, jsonify, request
import logging
from src.api.routes.api_routes import get_swim_lane_availability, book_lane, cancel_lane, get_user_appointments

legacy_bp = Blueprint('legacy', __name__)

@legacy_bp.route("/availability", methods=["GET"])
def legacy_get_swim_lane_availability():
    """Legacy API Endpoint to return swim lane availability."""
    logging.info("Legacy: Availability endpoint called.")
    # Delegate to the API route logic
    return get_swim_lane_availability()

@legacy_bp.route("/book", methods=["POST"])
def legacy_book_lane():
    """Legacy API Endpoint to book a swim lane."""
    logging.info("Legacy: Book lane endpoint called.")
    # Delegate to the API route logic
    return book_lane()

@legacy_bp.route("/cancel", methods=["POST"])
def legacy_cancel_lane():
    """Legacy API Endpoint to cancel a swim lane appointment."""
    logging.info("Legacy: Cancel lane endpoint called.")
    # Delegate to the API route logic
    return cancel_lane()

@legacy_bp.route("/appointments", methods=["GET"])
def legacy_get_user_appointments():
    """Legacy API Endpoint to return scheduled swim lane appointments."""
    logging.info("Legacy: Appointments endpoint called.")
    # Delegate to the API route logic
    return get_user_appointments()