from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
import logging
import os
import secrets
from src.domain.sql.authGateway import get_auth, toggle_auth_enabled, get_all_auth_data, update_mac_password, store_auth, delete_user, update_api_key
from src.contextManager import load_context_for_registration_pages
from src.web.gateways.webLoginGateway import login_with_credentials
from src.web.services.familyService import get_family_members_action
from src.decorators import require_admin
from src.domain.sql.scheduleGateway import get_all_active_schedules, get_schedule, add_or_update_schedule, delete_schedule, get_schedules_with_last_success

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
                # Check if user is enabled and has MAC password for dashboard access
                if auth_entry.get("is_enabled") and auth_entry.get("mac_password"):
                    # Auto-sync MAC password if it's different from what they logged in with
                    stored_mac_password = auth_entry.get("mac_password")
                    if stored_mac_password and stored_mac_password != password:
                        # Password has changed - update it automatically
                        success = update_mac_password(username, password)
                        if success:
                            logging.info(f"Auto-updated MAC password for {username} - password had changed")
                        else:
                            logging.error(f"Failed to auto-update MAC password for {username}")
                    
                    return redirect(url_for("web.user_dashboard"))
                elif auth_entry.get("is_enabled"):
                    # User is enabled but needs to set MAC password
                    # Store the password temporarily so they can choose to save it
                    session['login_password'] = password
                    return redirect(url_for("web.setup_mac_password"))
                else:
                    # User is not enabled yet
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
            if isinstance(family_members, list):
                family_members.append(customer)  # Add the customer to the family_members list
            else:
                family_members = [customer]  # Create new list with just the customer
            
            # Store the MAC password in session for later use during registration
            session['mac_password'] = password
            session['username'] = username  # Store username as well
            
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
            "is_admin": bool(record[5]),
            "has_mac_password": bool(record[6]) if len(record) > 6 else False
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
    import datetime
    import pytz
    
    schedules = get_schedules_with_last_success()
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    
    # Convert all timestamps to Eastern Time
    for schedule in schedules:
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            timestamp_key = f"{day}_last_success"
            if schedule.get(timestamp_key):
                # Assume database timestamps are in UTC
                utc_timestamp = schedule[timestamp_key]
                if utc_timestamp.tzinfo is None:
                    # Make it timezone-aware as UTC
                    utc_timestamp = pytz.utc.localize(utc_timestamp)
                # Convert to Eastern Time
                schedule[timestamp_key] = utc_timestamp.astimezone(eastern)
    
    return render_template("admin_schedules.html", schedules=schedules, now=lambda: now, eastern_tz=eastern)

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
    username = data.get('username') if data else None
    schedule_data = data.get('schedule', {}) if data else {}
    
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
    username = data.get("username") if data else None
    schedule = data.get("schedule", {}) if data else {}
    
    # Check if user exists in auth_data
    auth_entry = get_auth(username)
    if not auth_entry:
        return jsonify({"status": "error", "message": f"User {username} not found"}), 404
    
    add_or_update_schedule(username, schedule)
    return jsonify({"status": "success", "message": f"Schedule created for {username}"})

@web_bp.route("/admin/mac-password", methods=["POST"])
@require_admin
def update_user_mac_password():
    """Update a user's MAC password."""
    data = request.json
    username = data.get("username") if data else None
    mac_password = data.get("mac_password", "").strip() if data else ""
    
    if not username:
        return jsonify({"status": "error", "message": "Username is required"}), 400
    
    # Check if user exists
    auth_entry = get_auth(username)
    if not auth_entry:
        return jsonify({"status": "error", "message": f"User {username} not found"}), 404
    
    # Don't allow updating admin user's MAC password from this interface
    if auth_entry.get("is_admin"):
        return jsonify({"status": "error", "message": "Cannot update MAC password for admin users"}), 403
    
    # If a password is provided, validate it by attempting to login
    if mac_password:
        context = load_context_for_registration_pages()
        login_response = login_with_credentials(username, mac_password, context)
        
        if not login_response:
            return jsonify({"status": "error", "message": f"Invalid MAC password for {username}. Please verify the password is correct for the MAC website."}), 400
    
    # Update the MAC password (empty string will clear it)
    success = update_mac_password(username, mac_password if mac_password else None)
    
    if success:
        message = f"MAC password {'updated' if mac_password else 'cleared'} for {username}"
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": f"Failed to update MAC password for {username}"}), 500

@web_bp.route("/admin/delete-user", methods=["POST"])
@require_admin
def delete_user_admin():
    """Delete a user and all their associated data."""
    data = request.json
    username = data.get("username") if data else None
    
    if not username:
        return jsonify({"status": "error", "message": "Username is required"}), 400
    
    # Check if user exists
    auth_entry = get_auth(username)
    if not auth_entry:
        return jsonify({"status": "error", "message": f"User {username} not found"}), 404
    
    # Don't allow deleting admin users
    if auth_entry.get("is_admin"):
        return jsonify({"status": "error", "message": "Cannot delete admin users"}), 403
    
    try:
        # Delete user's schedule first (if it exists)
        schedule_deleted = delete_schedule(username)
        schedule_message = f" Schedule deleted." if schedule_deleted else " No schedule found."
        
        # Delete the user from auth_data
        user_deleted = delete_user(username)
        
        if user_deleted:
            message = f"User {username} has been successfully deleted.{schedule_message}"
            return jsonify({"status": "success", "message": message})
        else:
            return jsonify({"status": "error", "message": f"Failed to delete user {username}"}), 500
            
    except Exception as e:
        logging.exception(f"Error deleting user {username}: {str(e)}")
        return jsonify({"status": "error", "message": f"An error occurred while deleting user {username}: {str(e)}"}), 500

@web_bp.route("/admin/regenerate-api-key", methods=["POST"])
@require_admin
def regenerate_api_key():
    """Regenerate API key for a user."""
    data = request.json
    username = data.get("username") if data else None
    
    if not username:
        return jsonify({"status": "error", "message": "Username is required"}), 400
    
    # Check if user exists
    auth_entry = get_auth(username)
    if not auth_entry:
        return jsonify({"status": "error", "message": f"User {username} not found"}), 404
    
    # Don't allow regenerating admin API keys from this interface
    if auth_entry.get("is_admin"):
        return jsonify({"status": "error", "message": "Cannot regenerate API keys for admin users"}), 403
    
    try:
        # Generate new API key
        new_api_key = generate_api_key()
        
        # Update the API key in the database
        success = update_api_key(username, new_api_key)
        
        if success:
            return jsonify({
                "status": "success", 
                "message": f"API key regenerated for {username}",
                "new_api_key": new_api_key
            })
        else:
            return jsonify({"status": "error", "message": f"Failed to regenerate API key for {username}"}), 500
            
    except Exception as e:
        logging.exception(f"Error regenerating API key for {username}: {str(e)}")
        return jsonify({"status": "error", "message": f"An error occurred while regenerating API key for {username}: {str(e)}"}), 500

def generate_api_key():
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

@web_bp.route("/select_family_member", methods=["POST"])
def select_family_member():
    """Handle family member selection and complete registration."""
    username = request.form.get("username")
    customer_id = request.form.get("customer_id")
    family_member_id = request.form.get("family_member")
    save_mac_password = request.form.get("save_mac_password") == "on"  # Checkbox value
    
    if not username or not customer_id or not family_member_id:
        return render_template("registration.html", error="Missing required information"), 400
    
    # Generate a proper API key
    api_key = generate_api_key()
    
    # Use the MAC password from session if user opted to save it
    mac_password_to_store = None
    if save_mac_password and session.get('mac_password'):
        mac_password_to_store = session.get('mac_password')
        # Password was already validated during login, so we know it's valid
    
    try:
        store_auth(
            username=username,
            api_key=api_key,
            customer_id=customer_id,
            alt_customer_id=family_member_id,
            is_enabled=False,  # Will be enabled by admin later
            is_admin=False,
            mac_password=mac_password_to_store
        )
        
        logging.info(f"Registration completed for user: {username}, MAC password {'set' if mac_password_to_store else 'not provided'}")
        
        # Store the username and MAC password status in session for the confirmation page
        session['username'] = username
        session['mac_password_set'] = bool(mac_password_to_store)
        
        # Clear the MAC password from session for security after registration
        if 'mac_password' in session:
            del session['mac_password']
        
        return redirect(url_for("web.registration_complete"))
        
    except Exception as e:
        logging.error(f"Error storing registration data for {username}: {str(e)}")
        return render_template("registration.html", error="Registration failed. Please try again."), 500

@web_bp.route("/registration_complete", methods=["GET"])
def registration_complete():
    """Show registration completion confirmation."""
    username = session.get('username')
    if not username:
        return redirect(url_for("web.login"))
    
    return render_template("confirmation.html", username=username)

@web_bp.route("/user/dashboard", methods=["GET"])
def user_dashboard():
    """User dashboard for managing auto-booking schedules."""
    username = session.get('username')
    if not username:
        return redirect(url_for("web.login"))
    
    # Verify user is enabled
    auth_entry = get_auth(username)
    if not auth_entry or not auth_entry.get("is_enabled"):
        return redirect(url_for("web.already_submitted"))
    
    # Check if user has MAC password for auto-booking features
    has_mac_password = auth_entry.get("mac_password") is not None
    
    # Get the user's current schedule
    user_schedule = get_schedule(username)
    if user_schedule is None:
        user_schedule = {
            "monday": None,
            "tuesday": None,
            "wednesday": None,
            "thursday": None,
            "friday": None,
            "saturday": None,
            "sunday": None
        }
    
    return render_template("user_dashboard.html", username=username, schedule=user_schedule, has_mac_password=has_mac_password)

@web_bp.route("/user/schedule", methods=["POST"])
def update_my_schedule():
    """Allow users to update their own schedule."""
    username = session.get('username')
    if not username:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    
    # Verify user is enabled (MAC password not required to save schedule)
    auth_entry = get_auth(username)
    if not auth_entry or not auth_entry.get("is_enabled"):
        return jsonify({"status": "error", "message": "Access denied"}), 403
    
    data = request.json
    schedule_data = data.get('schedule', {}) if data else {}
    
    try:
        add_or_update_schedule(username, schedule_data)
        
        # Check if they have MAC password for appropriate message
        if not auth_entry.get("mac_password"):
            return jsonify({"status": "warning", "message": "Schedule saved, but you need to set your MAC password first to enable auto-booking."})
        else:
            return jsonify({"status": "success", "message": "Your schedule has been updated successfully!"})
    except Exception as e:
        logging.error(f"Error updating schedule for {username}: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to update schedule. Please try again."}), 500

@web_bp.route("/user/schedule", methods=["DELETE"])
def delete_my_schedule():
    """Allow users to delete their own schedule."""
    username = session.get('username')
    if not username:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    
    # Verify user is enabled (MAC password not required to delete schedule)
    auth_entry = get_auth(username)
    if not auth_entry or not auth_entry.get("is_enabled"):
        return jsonify({"status": "error", "message": "Access denied"}), 403
    
    try:
        success = delete_schedule(username)
        if success:
            return jsonify({"status": "success", "message": "Your schedule has been deleted successfully!"})
        else:
            return jsonify({"status": "error", "message": "No schedule found to delete"}), 404
    except Exception as e:
        logging.error(f"Error deleting schedule for {username}: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to delete schedule. Please try again."}), 500

@web_bp.route("/user/mac-password", methods=["POST"])
def update_my_mac_password():
    """Allow users to update their own MAC password."""
    username = session.get('username')
    if not username:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    
    # Verify user is enabled
    auth_entry = get_auth(username)
    if not auth_entry or not auth_entry.get("is_enabled"):
        return jsonify({"status": "error", "message": "Access denied"}), 403
    
    data = request.json
    mac_password = data.get("mac_password", "").strip() if data else ""
    
    if not mac_password:
        return jsonify({"status": "error", "message": "MAC password is required"}), 400
    
    # Validate the MAC password by attempting to login
    context = load_context_for_registration_pages()
    login_response = login_with_credentials(username, mac_password, context)
    
    if not login_response:
        return jsonify({"status": "error", "message": "Invalid MAC password. Please check your password and try again."}), 400
    
    try:
        success = update_mac_password(username, mac_password)
        if success:
            logging.info(f"User {username} updated their MAC password")
            return jsonify({"status": "success", "message": "Your MAC password has been updated successfully!"})
        else:
            return jsonify({"status": "error", "message": "Failed to update MAC password. Please try again."}), 500
    except Exception as e:
        logging.error(f"Error updating MAC password for {username}: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to update MAC password. Please try again."}), 500

@web_bp.route("/setup-mac-password", methods=["GET", "POST"])
def setup_mac_password():
    """Allow enabled users to set their MAC password."""
    username = session.get('username')
    if not username:
        return redirect(url_for("web.login"))
    
    # Verify user is enabled
    auth_entry = get_auth(username)
    if not auth_entry or not auth_entry.get("is_enabled"):
        return redirect(url_for("web.already_submitted"))
    
    # If they already have a MAC password, redirect to dashboard
    if auth_entry.get("mac_password"):
        return redirect(url_for("web.user_dashboard"))
    
    if request.method == "POST":
        save_login_password = request.form.get("save_login_password") == "on"
        
        if save_login_password:
            # Use the password from their recent login session
            login_password = session.get('login_password')
            
            if not login_password:
                error = "Session expired. Please log in again."
                return render_template("setup_mac_password.html", username=username, error=error)
            
            # Update the MAC password with their login password
            success = update_mac_password(username, login_password)
            
            if success:
                logging.info(f"User {username} successfully saved their login password as MAC password")
                # Clear the login password from session for security
                if 'login_password' in session:
                    del session['login_password']
                return redirect(url_for("web.user_dashboard"))
            else:
                error = "Failed to save MAC password. Please try again."
                return render_template("setup_mac_password.html", username=username, error=error)
        else:
            # User chose not to save their password, go to dashboard without MAC password
            logging.info(f"User {username} chose not to save their MAC password")
            # Clear the login password from session for security
            if 'login_password' in session:
                del session['login_password']
            return redirect(url_for("web.user_dashboard"))
    
    return render_template("setup_mac_password.html", username=username)

@web_bp.route("/already_submitted", methods=["GET"])
def already_submitted():
    """Landing page for users who are registered but not yet enabled or missing MAC password."""
    username = session.get('username')
    if not username:
        return redirect(url_for("web.login"))
    
    # Check if user has MAC password saved
    auth_entry = get_auth(username)
    has_mac_password = auth_entry and auth_entry.get("mac_password") is not None
    
    return render_template("already_submitted.html", username=username, has_mac_password=has_mac_password)

@web_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Logout the current user."""
    session.clear()
    return redirect(url_for("web.login"))