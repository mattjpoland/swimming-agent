import os
import sys
from celery import Celery
from dotenv import load_dotenv
import ssl

# Add the parent directory to Python path so we can import src modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

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
        # Import the auto-booking service
        from src.domain.services.autoBookingService import process_auto_booking
        
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