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

# Also add the parent directory (which contains domain/, agent/, etc.) to Python path
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
    USE_SSL = True
else:
    # Fallback to REDIS_URL if provided directly
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    USE_SSL = REDIS_URL.startswith('rediss://')

# Initialize Celery app
celery_app = Celery(
    'swimming_agent',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['src.worker.tasks']
)

# Base Celery configuration
celery_config = {
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'US/Eastern',
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 30 * 60,  # 30 minutes
    'task_soft_time_limit': 25 * 60,  # 25 minutes
    'worker_prefetch_multiplier': 1,
    'worker_max_tasks_per_child': 1000,
    # Add these optimizations to reduce Redis requests
    'broker_transport_options': {
        'visibility_timeout': 3600,  # 1 hour
        'polling_interval': 60.0,     # Poll every 1 minute - balanced for booking needs
        'max_retries': 3,
        # Additional optimizations
        'fanout_prefix': True,
        'fanout_patterns': True,
    },
    'result_expires': 3600,  # Results expire after 1 hour
    'task_ignore_result': True,  # Don't store results unless explicitly needed
    'task_acks_late': True,  # Acknowledge tasks after completion
    'worker_send_task_events': False,  # Disable task events
    'task_send_sent_event': False,  # Don't send task-sent events
    'worker_disable_rate_limits': True,  # Disable rate limit checks
    # Additional optimizations
    'broker_connection_retry': False,  # Don't retry connection on startup
    'broker_connection_retry_on_startup': False,
    'broker_pool_limit': 1,  # Limit connection pool
    'redis_max_connections': 2,  # Limit Redis connections
    'redis_socket_keepalive': True,
    'redis_socket_keepalive_options': {
        1: 30,  # TCP_KEEPIDLE
        2: 10,  # TCP_KEEPINTVL
        3: 6,   # TCP_KEEPCNT
    },
}

# Add SSL configuration only if using secure Redis
if USE_SSL:
    celery_config.update({
        'broker_use_ssl': {
            'ssl_cert_reqs': ssl.CERT_NONE,
            'ssl_ca_certs': None,
            'ssl_certfile': None,
            'ssl_keyfile': None,
        },
        'redis_backend_use_ssl': {
            'ssl_cert_reqs': ssl.CERT_NONE,
            'ssl_ca_certs': None,
            'ssl_certfile': None,
            'ssl_keyfile': None,
        }
    })

# Apply the configuration
celery_app.conf.update(celery_config)

# Force broker transport options to ensure they're applied
celery_app.conf.broker_transport_options = {
    'visibility_timeout': 3600,
    'polling_interval': 60.0,  # 1 minute - good balance for booking responsiveness
    'max_retries': 3,
    'fanout_prefix': True,
    'fanout_patterns': True,
}

# Remove Celery Beat schedule - using external CRON instead
# Commented out to prevent Beat scheduler from running
# from celery.schedules import crontab
# 
# celery_app.conf.beat_schedule = {
#     'auto-booking-midnight': {
#         'task': 'run_auto_booking',
#         'schedule': crontab(hour='0', minute='1'),  # 12:01 AM Eastern
#     },
#     'auto-booking-retry-1': {
#         'task': 'run_auto_booking',
#         'schedule': crontab(hour='0', minute='10'),  # 12:10 AM Eastern
#     },
#     'auto-booking-retry-2': {
#         'task': 'run_auto_booking',
#         'schedule': crontab(hour='0', minute='20'),  # 12:20 AM Eastern
#     },
# }

# Set timezone for beat schedule
celery_app.conf.update({'timezone': 'US/Eastern'})

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
            # Import from the domain services
            from src.domain.services.autoBookingService import process_auto_booking
            logging.info("Successfully imported process_auto_booking")
        except ImportError as import_error:
            logging.error(f"Import error: {import_error}")
            logging.error(f"Available modules in current directory: {os.listdir('.')}")
            logging.error(f"Available modules in parent directory: {os.listdir('..') if os.path.exists('..') else 'parent directory not found'}")
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