import os
import sys
from celery import Celery
from dotenv import load_dotenv
import ssl

# Get the directory containing this tasks.py file
TASKS_DIR = os.path.dirname(os.path.abspath(__file__))

# Add the tasks directory to Python path if not already there
if TASKS_DIR not in sys.path:
    sys.path.insert(0, TASKS_DIR)

# Also add the parent directory (which contains src/) to Python path
PARENT_DIR = os.path.dirname(TASKS_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Load environment variables
load_dotenv()

# Get Redis configuration from environment variables
UPSTASH_REDIS_HOST = os.getenv('UPSTASH_REDIS_HOST')
UPSTASH_REDIS_PORT = os.getenv('UPSTASH_REDIS_PORT', '6379')
UPSTASH_REDIS_PASSWORD = os.getenv('UPSTASH_REDIS_PASSWORD')

# Construct Redis URL for secure Upstash connection
if UPSTASH_REDIS_HOST and UPSTASH_REDIS_PASSWORD:
    REDIS_URL = f"rediss://:{UPSTASH_REDIS_PASSWORD}@{UPSTASH_REDIS_HOST}:{UPSTASH_REDIS_PORT}"
else:
    # Fallback to REDIS_URL if provided directly
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Initialize Celery app
celery_app = Celery(
    'swimming_agent',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks']
)

# Celery configuration with SSL settings for Upstash Redis
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='US/Eastern',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Redis SSL configuration for Upstash
    broker_use_ssl={
        'ssl_cert_reqs': ssl.CERT_NONE,
        'ssl_ca_certs': None,
        'ssl_certfile': None,
        'ssl_keyfile': None,
    },
    redis_backend_use_ssl={
        'ssl_cert_reqs': ssl.CERT_NONE,
        'ssl_ca_certs': None,
        'ssl_certfile': None,
        'ssl_keyfile': None,
    }
)

@celery_app.task(bind=True, name='run_auto_booking')
def run_auto_booking(self):
    """
    Celery task to run the automated booking process.
    This task imports and calls the existing process_auto_booking function.
    """
    try:
        # Debug: Log the current working directory and Python path
        import logging
        logging.info(f"Current working directory: {os.getcwd()}")
        logging.info(f"Python path: {sys.path}")
        logging.info(f"Tasks.py location: {os.path.abspath(__file__)}")
        
        # Try to import the auto-booking service with better error handling
        try:
            from src.domain.services.autoBookingService import process_auto_booking
            logging.info("Successfully imported process_auto_booking")
        except ImportError as import_error:
            logging.error(f"Import error: {import_error}")
            logging.error(f"Available modules in src: {os.listdir('src') if os.path.exists('src') else 'src directory not found'}")
            logging.error(f"Available modules in current directory: {os.listdir('.')}")
            raise
        
        # Update task state to indicate processing
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Processing auto-booking requests...'}
        )
        
        # Call the existing auto-booking function
        results = process_auto_booking()
        
        # Count successful and failed bookings
        successful = len([r for r in results if r.get("status") == "success"])
        failed = len([r for r in results if r.get("status") == "error"])
        
        # Return the results
        return {
            'status': 'SUCCESS',
            'message': f'Auto-booking process completed: {successful} successful, {failed} failed',
            'results': results,
            'summary': {
                'total_processed': len(results),
                'successful': successful,
                'failed': failed
            }
        }
        
    except Exception as e:
        # Update task state to indicate failure
        self.update_state(
            state='FAILURE',
            meta={'status': 'FAILURE', 'error': str(e)}
        )
        raise

if __name__ == '__main__':
    celery_app.start() 