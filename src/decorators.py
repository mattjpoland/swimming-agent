from functools import wraps
from flask import request, jsonify, g, session, redirect, url_for
import logging
from src.contextManager import load_context_for_authenticated_user
from src.domain.sql.authGateway import get_auth

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'context'):
            g.context = {}

        mac_password = request.headers.get("x-mac-pw")
        auth_header = request.headers.get("Authorization")
        x_api_key = request.headers.get("x-api-key")
        
        # Support both Authorization: Bearer <key> and x-api-key: <key> formats
        requested_api_key = None
        if auth_header and auth_header.startswith("Bearer "):
            requested_api_key = auth_header.split(" ")[1]
        elif x_api_key:
            requested_api_key = x_api_key

        g.context = load_context_for_authenticated_user(requested_api_key, mac_password)

        if not g.context:
            logging.warning("Unauthorized access attempt with invalid API key.")
            return jsonify({"error": "Unauthorized"}), 401

        if not g.context.get("IS_ENABLED"):
            logging.warning(f"Access denied for disabled account: {g.context.get('USERNAME')}")
            return jsonify({"error": "Account not enabled"}), 403

        # Log user authentication with admin status
        is_admin = g.context.get("IS_ADMIN", False)
        username = g.context.get("USERNAME")
        admin_status = "admin" if is_admin else "regular user"
        logging.info(f"Authenticated user: {username} (Status: {admin_status})")
        
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            logging.warning("Unauthorized admin access attempt: No username in session.")
            # Check if this is a web request (likely if it's not JSON)
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({"error": "Unauthorized"}), 401
            else:
                # For web requests, redirect to login page
                return redirect(url_for("web.login"))

        auth_entry = get_auth(session['username'])
        if not auth_entry or not auth_entry.get("is_admin"):
            logging.warning(f"Unauthorized admin access attempt by user: {session.get('username')}")
            # Check if this is a web request (likely if it's not JSON)
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({"error": "Unauthorized"}), 401
            else:
                # For web requests, redirect to login page
                return redirect(url_for("web.login"))

        logging.info(f"Admin access granted to user: {session['username']}")
        return f(*args, **kwargs)
    return decorated_function