from flask import Flask, redirect, url_for
from src.routes.api_routes import api_bp
from src.routes.web_routes import web_bp
from src.routes.legacy_routes import legacy_bp
from src.routes.agent_routes import agent_bp  # Import the new agent_routes
from src.sql.ragSourceGateway import ensure_rag_sources_table, get_all_rag_sources, add_rag_source, rag_source_exists
import logging
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Print all RAG sources to the console
rag_sources = get_all_rag_sources()
print("RAG Sources from database:")
for source in rag_sources:
    print(source)

# Register Blueprints
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(agent_bp, url_prefix="/agent")  # Register the new agent blueprint
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