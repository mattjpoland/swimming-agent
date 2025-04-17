from functools import wraps
from flask import request, jsonify, g, session
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
        requested_api_key = auth_header.split(" ")[1] if auth_header else None

        g.context = load_context_for_authenticated_user(requested_api_key, mac_password)

        if not g.context:
            logging.warning("Unauthorized access attempt with invalid API key.")
            return jsonify({"error": "Unauthorized"}), 401

        if not g.context.get("IS_ENABLED"):
            logging.warning(f"Access denied for disabled account: {g.context.get('USERNAME')}")
            return jsonify({"error": "Account not enabled"}), 403

        logging.info(f"Authenticated user: {g.context.get('USERNAME')}")
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            logging.warning("Unauthorized admin access attempt: No username in session.")
            return jsonify({"error": "Unauthorized"}), 401

        auth_entry = get_auth(session['username'])
        if not auth_entry or not auth_entry.get("is_admin"):
            logging.warning(f"Unauthorized admin access attempt by user: {session.get('username')}")
            return jsonify({"error": "Unauthorized"}), 401

        logging.info(f"Admin access granted to user: {session['username']}")
        return f(*args, **kwargs)
    return decorated_function