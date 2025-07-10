# Swimlane Availability Checker

This Python project checks the availability of swim lanes and visualizes it.

## Setup

1. Clone the repo and navigate to the folder.
2. Create a virtual environment:
python -m venv venv

3. Activate it:
- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

4. Install dependencies:
pip install -r requirements.txt

5. Create a .env file
BASE_MAC_URL=https://www.ourclublogin.com/api/
COMPANY_ID=510726
DATABASE_URL=(connection string)
FLASK_DEBUG=true
OPENAI_API_KEY=(API Key 1)
OPENWEATHERMAP_API_KEY=(API Key 2)
REQUEST_LOGGING=true

6. Run the program:
python src/server.py

## Features

This project is a comprehensive swimming lane management system with the following architecture:

### 🏊 DOMAIN Module (`src/domain/`)
The core business logic layer that handles all swimming-related operations:
- **Services**: Business logic for availability checking, booking, cancellations, appointments, weather integration, and RAG (Retrieval-Augmented Generation) capabilities
- **Gateways**: External API integrations with the MAC (Member Access Control) system and weather services
- **SQL Layer**: Database access for authentication, scheduling, and RAG data sources
- **Drawing**: Visual generation for pool availability charts and member barcode generation

### 🔌 API Module (`src/api/`)
RESTful API endpoints providing programmatic access to all features:
- **Availability Endpoints**: Check lane availability with visual pool diagrams
- **Booking & Cancellation**: Book swim lanes and manage appointments
- **Member Services**: Generate membership barcodes and manage appointments
- **Weather Integration**: Current weather and forecasts for outdoor swimming decisions
- **Auto-booking**: Multiple endpoints for automated scheduling (synchronous, asynchronous via Celery, and smart scheduling)
- **Legacy Support**: Backward compatibility routes for existing integrations

### 🤖 AGENT Module (`src/agent/`)
AI-powered conversational interface using OpenAI:
- **Natural Language Processing**: Understands swimming-related requests in plain English
- **Intelligent Actions**: Maps user intents to specific actions (booking, checking availability, weather queries)
- **Memory Service**: Maintains conversation context and user preferences
- **Multi-format Responses**: Returns text, tool calls, and special formatted responses
- **Date & Pool Resolution**: Smart utilities for interpreting user input about dates and pool preferences

### 🔧 AGENT TOOLS
Function-calling capabilities available to the AI agent:

#### **Swimming Operations**
- **`check_lane_availability`**: Check pool availability for any date
  - Supports Indoor, Outdoor, or Both pools
  - Returns visual pool diagram or text description
  - Shows current bookings and available lanes
  
- **`book_swim_lane`**: Book a specific swim lane
  - Intelligent date parsing (today, tomorrow, next Monday, etc.)
  - Pool preference handling
  - Duration options (30, 45, 60, 90 minutes)
  - Lane selection with preferences
  
- **`get_appointments`**: View scheduled appointments
  - Shows all bookings for a specific date range
  - Includes booking details and confirmation numbers
  
- **`cancel_appointment`**: Cancel existing bookings
  - Cancels appointments by date
  - Provides confirmation of cancellation

#### **Member Services**
- **`get_membership_barcode`**: Generate facility access barcode
  - Returns scannable barcode image
  - Quick access with "barcode" shortcut
  - Essential for facility entry

#### **Environmental Information**
- **`get_current_weather`**: Current weather conditions
  - Temperature, conditions, wind speed
  - Helps decide between indoor/outdoor pools
  
- **`weather_forecast`**: Future weather predictions
  - Forecast for specific dates
  - Planning tool for outdoor swimming

#### **Information & Help**
- **`get_information`**: General swimming information
  - Hours of operation
  - Pool rules and guidelines
  - Membership information
  - Facility details

#### **Schedule Management**
- **`manage_schedule`** (Admin/User feature): Automated booking schedules
  - View current recurring bookings
  - Add/update booking commands for specific days
  - Remove or clear schedules
  - Natural language booking preferences

#### **Tool Chaining**
The agent supports intelligent tool chaining for complex requests:
- Can execute multiple tools in sequence
- Evaluates results before proceeding
- Maximum of 10 tool calls per request
- Smart decision-making about when to stop

### ⚙️ WORKER Module (`src/worker/`)
Background task processing for scheduled operations:
- **Celery Integration**: Asynchronous task execution with Redis backend
- **Auto-booking Tasks**: Process scheduled swim lane bookings at 9 PM
- **Cloud-Ready**: Supports both Upstash Redis (cloud) and local Redis configurations
- **Task Monitoring**: Track task status and results through API endpoints

### 🌐 WEB Module (`src/web/`)
User-friendly web interface:
- **User Portal**: 
  - Registration system with family member selection
  - Personal dashboard for managing auto-booking schedules
  - MAC password management for automated bookings
- **Admin Dashboard**:
  - User management (enable/disable accounts, API key regeneration)
  - Schedule oversight for all users
  - MAC password verification and updates
- **Responsive Design**: Clean, modern UI with swimming-themed styling
- **Security**: Session-based authentication with admin role support

### 🛠️ TOOLS
Development and debugging utilities:
- **Logging Service**: Configurable logging with presets (`verbose`, `normal`, `quiet`, `dev`)
  - Set via `LOG_LEVEL` environment variable
  - Automatic emoji filtering for Windows compatibility
  - Separate log levels for different components (OpenAI, HTTP libraries, etc.)
- **RAG Debugging**: 
  - `/api/rag-status` - Check index health and chunk distribution
  - `/api/debug-query` - Test semantic search queries with detailed similarity scores
  - `/api/rebuild-index` - Rebuild the FAISS index from database sources
- **Celery Tools**:
  - Run worker directly: `celery -A src.worker.tasks worker --loglevel=info`
  - Monitor with Flower: `celery -A src.worker.tasks flower`
  - Check task status via API: `/api/task-status/<task_id>`
- **Standalone Scripts**: Several modules can run independently for testing:
  - Gateway testing for login/family member retrieval
  - Direct database operations
  - Service-level function testing

### ⏰ CRON SCHEDULING
Automated booking execution system:
- **External CRON Design**: Uses external CRON services (not Celery Beat) to minimize Redis overhead
- **Multiple Endpoints**:
  - `/api/cron_schedule_swim_lanes` - Queues task via Celery (asynchronous)
  - `/api/cron_schedule_swim_lanes_direct` - Executes immediately (synchronous)
  - `/api/cron_schedule_swim_lanes_smart` - Only queues if users need booking
- **Recommended Schedule** (9 PM ET booking window):
  ```cron
  1 21 * * * curl -X POST https://your-app/api/cron_schedule_swim_lanes_smart
  10 21 * * * curl -X POST https://your-app/api/cron_schedule_swim_lanes_smart
  20 21 * * * curl -X POST https://your-app/api/cron_schedule_swim_lanes_smart
  30 21 * * * curl -X POST https://your-app/api/cron_schedule_swim_lanes_smart
  ```
- **Smart Features**:
  - Booking verification ensures only successful bookings update timestamps
  - Failed attempts get automatic retries on subsequent runs
  - Books for one week in advance (e.g., Monday's run books next Monday)
  - Checks if users have valid schedules and MAC passwords before processing
- **Monitoring**:
  - Admin dashboard shows last successful booking per day
  - Task IDs returned for async tracking
  - Detailed logging for troubleshooting
