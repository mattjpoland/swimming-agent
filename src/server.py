from flask import Flask, redirect, url_for
from src.api.routes.api_routes import api_bp
from src.api.routes.legacy_routes import legacy_bp
from src.web.routes.web_routes import web_bp
from src.agent.routes.agent_routes import agent_bp  # Import the new agent_routes
from src.domain.sql.ragSourceGateway import ensure_rag_sources_table, get_all_rag_sources, add_rag_source, rag_source_exists
from src.domain.services.ragIndexingService import verify_index  # Import verify_index
import logging
import os
import sys

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

# Configure logging with encoding handling for Windows
console_handler = logging.StreamHandler()
# For Windows console compatibility, replace emoji characters
if sys.platform == 'win32':
    class EmojiFilter(logging.Filter):
        def filter(self, record):
            if isinstance(record.msg, str):
                # Replace common emojis with text equivalents
                record.msg = record.msg.replace('🔄', '[REFRESH]')
                record.msg = record.msg.replace('✅', '[SUCCESS]')
                record.msg = record.msg.replace('⚠️', '[WARNING]')
                record.msg = record.msg.replace('❌', '[ERROR]')
            return True
    
    console_handler.addFilter(EmojiFilter())

# Set DEBUG level explicitly and ensure propagate=True
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG level
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        console_handler,
        logging.FileHandler('swimming_agent.log', encoding='utf-8')  # Add file logging with UTF-8 encoding
    ]
)

# Make sure root logger is set to DEBUG too
logging.getLogger().setLevel(logging.DEBUG)

# Add detailed index verification after logging setup
index_status = verify_index()
if index_status["status"] == "ok":
    logging.info("RAG Index Status: OK")
    logging.info(f"  • Total chunks: {index_status['chunks_count']}")
    logging.info("  • Sources distribution:")
    for source, count in index_status["sources"].items():
        logging.info(f"    - {source}: {count} chunks")
    logging.info("\nSample content from each source:")
    for sample in index_status["sample_chunks"]:
        logging.info(f"\n{sample['source']}:")
        logging.info(f"  {sample['text']}")
else:
    logging.warning(f"RAG Index Status: {index_status['status']}")
    logging.warning(f"  • Message: {index_status.get('message', 'Unknown error')}")

logging.info("Server started.")

@app.route("/", methods=["GET"])
def index():
    """Redirect root to the web login page."""
    return redirect(url_for("web.login"))

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)