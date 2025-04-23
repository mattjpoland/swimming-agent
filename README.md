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
- Logs in via an API.
- Checks swim lane availability.
- Draws a pool with color-coded lane reservations.
