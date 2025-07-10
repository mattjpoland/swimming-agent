#!/bin/bash
# Smart Celery worker that adjusts behavior based on time of day

# Get current hour in Eastern time
HOUR=$(TZ="America/New_York" date +%H)
echo "Current Eastern hour: $HOUR"

# Check if we're in booking window (8 PM - 11 PM Eastern)
# This covers 9 PM ET booking time in both EDT and EST
if [ $HOUR -ge 20 ] && [ $HOUR -le 23 ]; then
    echo "ACTIVE HOURS: Running with moderate polling (30 second intervals)"
    # During booking hours: moderate polling (not too aggressive)
    export CELERY_BROKER_TRANSPORT_OPTIONS='{"polling_interval": 30.0}'
else
    echo "QUIET HOURS: Running with relaxed polling (30 minute intervals)"
    # Outside booking hours: very relaxed polling
    export CELERY_BROKER_TRANSPORT_OPTIONS='{"polling_interval": 1800.0}'
fi

# Run Celery with the appropriate settings
exec celery -A src.worker.tasks worker \
    --loglevel=info \
    --max-tasks-per-child=10 \
    --concurrency=1 