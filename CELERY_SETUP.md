# Celery Background Task Setup

This document explains how to set up and use Celery with Redis for background task execution in the Swimming Agent application.

## Overview

The application now uses Celery with Redis as both the message broker and result backend to handle background tasks. This allows long-running operations like auto-booking to be processed asynchronously without blocking the web API.

## Environment Variables

You need to configure the following environment variables for Redis connection:

### Option 1: Individual Upstash Redis Components
```bash
UPSTASH_REDIS_HOST=your-upstash-redis-host.upstash.io
UPSTASH_REDIS_PORT=6379
UPSTASH_REDIS_PASSWORD=your-upstash-redis-password
```

### Option 2: Direct Redis URL
```bash
REDIS_URL=rediss://:password@host:port
```

**Note:** The application uses `rediss://` (with double 's') for secure SSL connections to Upstash Redis.

## Local Development Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   Create a `.env` file in the project root with your Redis configuration:
   ```bash
   UPSTASH_REDIS_HOST=your-upstash-redis-host.upstash.io
   UPSTASH_REDIS_PORT=6379
   UPSTASH_REDIS_PASSWORD=your-upstash-redis-password
   ```

3. **Start Redis** (if running locally)
   ```bash
   redis-server
   ```

4. **Start Celery Worker**
   ```bash
   celery -A tasks worker --loglevel=info
   ```

5. **Start Flask Application**
   ```bash
   python src/server.py
   ```

## API Endpoints

### Queue Auto-Booking Task
- **Endpoint:** `POST /api/cron_schedule_swim_lanes`
- **Description:** Queues the auto-booking process as a background task
- **Response:** Returns a 202 status with the task ID
- **Example Response:**
  ```json
  {
    "status": "accepted",
    "message": "Auto-booking process has been queued for background execution",
    "task_id": "abc123-def456-ghi789"
  }
  ```

### Check Task Status
- **Endpoint:** `GET /api/task-status/<task_id>`
- **Description:** Get the status and result of a background task
- **Response:** Returns task state and result/error information
- **Example Response:**
  ```json
  {
    "task_id": "abc123-def456-ghi789",
    "state": "SUCCESS",
    "result": {
      "status": "SUCCESS",
      "message": "Auto-booking process completed: 2 successful, 0 failed",
      "results": [...],
      "summary": {
        "total_processed": 2,
        "successful": 2,
        "failed": 0
      }
    }
  }
  ```

## Task States

- **PENDING:** Task is waiting to be executed
- **PROGRESS:** Task is currently running
- **SUCCESS:** Task completed successfully
- **FAILURE:** Task failed with an error
- **REVOKED:** Task was cancelled

## Deployment on Render

The `render.yaml` file defines two services:

1. **Web Service** (`swimming-agent-web`): Runs the Flask application
2. **Worker Service** (`swimming-agent-worker`): Runs the Celery worker with smart polling

### Smart Polling Configuration

The worker uses a smart polling strategy based on time of day:
- **Active Hours (8 PM - 11 PM ET)**: Polls every 30 seconds during booking window
- **Quiet Hours (all other times)**: Polls every 30 minutes to minimize Redis requests

This configuration is optimized for the 9 PM ET booking window when the swimming facility releases new appointment slots.

### Important Note on Celery Beat

Celery Beat scheduler has been disabled in this configuration. All scheduling should be done through external CRON services (like Render's CRON jobs) that call the appropriate API endpoints. This significantly reduces Redis polling overhead.

### Environment Variables on Render

Set the following environment variables in your Render dashboard:

- `UPSTASH_REDIS_HOST`
- `UPSTASH_REDIS_PORT`
- `UPSTASH_REDIS_PASSWORD`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `MAC_PASSWORD`

### Manual Deployment

If not using `render.yaml`, create two services:

**Web Service:**
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn src.server:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`

**Worker Service:**
- Build Command: `pip install -r requirements.txt`
- Start Command: `celery -A tasks worker --loglevel=info`

## Monitoring and Debugging

### Celery Monitoring
You can monitor Celery tasks using the Celery Flower web interface:

```bash
pip install flower
celery -A tasks flower
```

### Logs
- Check application logs for task execution details
- Celery worker logs show task processing information
- Failed tasks include error details in the response

### Common Issues

1. **Redis Connection Issues**
   - Verify Redis credentials and host
   - Ensure SSL is enabled for Upstash (`rediss://`)
   - Check firewall/network connectivity

2. **Task Timeout**
   - Tasks have a 30-minute timeout
   - Long-running tasks may need to be optimized

3. **Worker Not Processing Tasks**
   - Ensure Celery worker is running
   - Check worker logs for errors
   - Verify Redis connection in worker

## Testing

To test the background task functionality:

1. Start the Celery worker
2. Make a POST request to `/api/cron_schedule_swim_lanes`
3. Use the returned task ID to check status via `/api/task-status/<task_id>`
4. Monitor the worker logs for task execution details 