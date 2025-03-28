from flask import Flask, redirect, url_for
from src.routes.api_routes import api_bp
from src.routes.web_routes import web_bp
from src.routes.legacy_routes import legacy_bp
import logging
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Register Blueprints
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(web_bp, url_prefix="/web")
app.register_blueprint(legacy_bp)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Sends logs to stdout
    ]
)
logging.info("Server started.")

@app.route("/", methods=["GET"])
def index():
    """Redirect root to the web login page."""
    return redirect(url_for("web.login"))

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)