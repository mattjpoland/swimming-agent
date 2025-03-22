from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
import logging
from src.sql.authGateway import get_auth, toggle_auth_enabled, get_all_auth_data
from src.decorators import require_admin

web_bp = Blueprint('web', __name__)

@web_bp.route("/login", methods=["GET", "POST"])
def login():
    """Web login page."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        auth_entry = get_auth(username)
        if auth_entry:
            session['username'] = username
            if auth_entry.get("is_admin"):
                return redirect(url_for("web.admin_page"))
            else:
                return redirect(url_for("web.already_submitted"))
        return render_template("login.html", error="Invalid credentials")
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