from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
import logging
import os
from src.domain.sql.authGateway import get_auth, toggle_auth_enabled, get_all_auth_data
from src.contextManager import load_context_for_registration_pages
from src.web.gateways.webLoginGateway import login_with_credentials
from src.web.services.familyService import get_family_members_action
from src.decorators import require_admin
from src.domain.sql.scheduleGateway import get_all_active_schedules, get_schedule, add_or_update_schedule, delete_schedule

# Define the template folder relative to this file
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))

web_bp = Blueprint('web', __name__, 
                   template_folder=template_dir,
                   static_folder=static_dir)

@web_bp.route("/login", methods=["GET", "POST"])
def login():
    """Web login page."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if the username already exists in the database
        auth_entry = get_auth(username)
        if auth_entry:
            session['username'] = username  # Store the username in the session
            if auth_entry.get("is_admin"):
                return redirect(url_for("web.admin_page"))
            else:
                return redirect(url_for("web.already_submitted"))

        # Handle new user registration
        context = load_context_for_registration_pages()
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

        # If login fails, return an error
        error = "Login failed. Please check your credentials."
        return render_template("login.html", error=error)

    # Render the login page for GET requests
    return render_template("login.html")

@web_bp.route("/admin", methods=["GET"])
@require_admin
def admin_page():
    """Web admin page."""
    auth_data = get_all_auth_data()
    auth_data_list = [
        {
            "username": record[0],
            "api_key": record[1],
            "customer_id": record[2],
            "alt_customer_id": record[3],
            "is_enabled": bool(record[4]),
            "is_admin": bool(record[5])
        }
        for record in auth_data
    ]
    return render_template("admin.html", auth_data=auth_data_list)

@web_bp.route("/toggle_enabled/<username>", methods=["POST"])
@require_admin
def toggle_enabled(username):
    """Toggle the enabled column for a given auth_data record."""
    auth_entry = get_auth(username)
    if auth_entry and auth_entry.get("is_admin"):
        return jsonify({"error": "Cannot toggle enabled status for admin users."}), 403
    toggle_auth_enabled(username)
    return redirect(url_for("web.admin_page"))

@web_bp.route("/admin/schedules", methods=["GET"])
@require_admin
def admin_schedules():
    """View all swim lane schedules."""
    schedules = get_all_active_schedules()
    return render_template("admin_schedules.html", schedules=schedules)

@web_bp.route("/admin/schedule", methods=["GET"])
@require_admin
def get_user_schedule():
    """Get a specific user's schedule."""
    username = request.args.get('username')
    if not username:
        return jsonify({"status": "error", "message": "Username parameter is required"}), 400
    
    logging.info(f"get_user_schedule called with username: '{username}'")
    schedule = get_schedule(username)
    logging.info(f"Schedule retrieved: {schedule}")
    if schedule is None:
        schedule = {
            "monday": None,
            "tuesday": None,
            "wednesday": None,
            "thursday": None,
            "friday": None,
            "saturday": None,
            "sunday": None
        }
    return jsonify({"username": username, "schedule": schedule})

@web_bp.route("/admin/schedule", methods=["POST"])
@require_admin
def update_user_schedule():
    """Update a user's schedule."""
    data = request.json
    username = data.get('username')
    schedule_data = data.get('schedule', {})
    
    if not username:
        return jsonify({"status": "error", "message": "Username is required"}), 400
    
    add_or_update_schedule(username, schedule_data)
    return jsonify({"status": "success", "message": f"Schedule updated for {username}"})

@web_bp.route("/admin/schedule", methods=["DELETE"])
@require_admin
def delete_user_schedule():
    """Delete a user's schedule."""
    username = request.args.get('username')
    if not username:
        return jsonify({"status": "error", "message": "Username parameter is required"}), 400
        
    success = delete_schedule(username)
    if success:
        return jsonify({"status": "success", "message": f"Schedule deleted for {username}"})
    else:
        return jsonify({"status": "error", "message": f"No schedule found for {username}"}), 404

@web_bp.route("/admin/schedule/new", methods=["POST"])
@require_admin
def create_new_schedule():
    """Create a new schedule."""
    data = request.json
    username = data.get("username")
    schedule = data.get("schedule", {})
    
    # Check if user exists in auth_data
    auth_entry = get_auth(username)
    if not auth_entry:
        return jsonify({"status": "error", "message": f"User {username} not found"}), 404
    
    add_or_update_schedule(username, schedule)
    return jsonify({"status": "success", "message": f"Schedule created for {username}"})