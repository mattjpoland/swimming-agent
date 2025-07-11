import os
import datetime
import logging
import requests
import time
from src.domain.sql.scheduleGateway import get_all_active_schedules, should_run_booking, update_last_success
from src.domain.sql.authGateway import get_mac_password
import pytz

# Configuration for MAC booking system
# Default to 8 days for the new 9 PM booking window (9 PM on day X → book for day X+8)
# Can be set to 7 for the old midnight booking window (12 AM on day X → book for day X+7)
MAC_BOOKING_DAYS_AHEAD = int(os.getenv("MAC_BOOKING_DAYS_AHEAD", "8"))

# Log the configuration on module load
logging.info(f"MAC booking configuration: Booking {MAC_BOOKING_DAYS_AHEAD} days ahead")

def get_day_of_week():
    """Get the current day of the week in lowercase."""
    eastern = pytz.timezone('US/Eastern')
    today = datetime.datetime.now(eastern)
    return today.strftime("%A").lower()

def call_reasoning_agent(command, username, mac_password, user_api_key, session_id=None):
    """
    Call the reasoning agent endpoint with the scheduling command.
    """
    try:
        # Prepare the request payload
        payload = {
            "user_input": command,
            "response_format": "auto"
        }
        
        # Add session_id if provided
        if session_id:
            payload["session_id"] = session_id
          # Prepare headers with authentication using the user's API key
        headers = {
            "Content-Type": "application/json",
            "x-api-key": user_api_key,
            "x-mac-pw": mac_password  # Fixed header name to match decorator
        }
          # Make the request to the agent endpoint with shorter timeout to prevent hanging
        agent_url = f"https://swimming-agent.onrender.com/agent/chat"
        logging.info(f"Calling agent endpoint: {agent_url}")
        logging.info(f"Request payload: {payload}")
        logging.info(f"Request headers: {{'Content-Type': headers['Content-Type'], 'x-api-key': '***', 'x-mac-pw': '***'}}")  # Hide sensitive data
        
        # Add retry logic for network issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    agent_url, 
                    json=payload, 
                    headers=headers, 
                    timeout=120,  # Reduced timeout
                    verify=True
                )
                
                logging.info(f"Agent response status: {response.status_code}")
                logging.info(f"Agent response content: {response.text[:500]}...")  # Log first 500 chars
                
                if response.status_code == 200:
                    result = response.json()
                    logging.info(f"Parsed JSON response: {result}")
                    # Extract session_id from response if present
                    returned_session_id = result.get("session_id", session_id)
                    logging.info(f"Extracted session_id: {returned_session_id}")
                    logging.info(f"Original session_id parameter: {session_id}")
                    logging.info(f"Result keys: {list(result.keys())}")
                    return {
                        "status": "success",
                        "message": result.get("message", "Command processed successfully"),
                        "details": result,
                        "session_id": returned_session_id
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Agent endpoint returned status {response.status_code}: {response.text}",
                        "session_id": session_id
                    }
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logging.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:  # Last attempt
                    raise
                time.sleep(5)  # Wait before retry
                
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to call reasoning agent after {max_retries} attempts: {e}")
        return {
            "status": "error",
            "message": f"Failed to communicate with reasoning agent: {str(e)}",
            "session_id": session_id
        }
    except Exception as e:
        logging.error(f"Unexpected error calling reasoning agent: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "session_id": session_id
        }

def verify_booking_exists(username, target_date, context):
    """
    Verify if a booking actually exists for the target date.
    Returns True if a booking is found, False otherwise.
    """
    try:
        from src.domain.services.appointmentService import get_appointments_schedule_action
        
        # Check appointments for the specific target date
        response, status_code = get_appointments_schedule_action(
            start_date=target_date,
            end_date=target_date,
            context=context
        )
        
        if status_code == 200:
            appointments = response.get("appointments", [])
            if appointments:
                logging.info(f"Verified booking exists for {username} on {target_date}: {len(appointments)} appointment(s) found")
                return True
            else:
                logging.warning(f"No booking found for {username} on {target_date}")
                return False
        else:
            logging.error(f"Failed to verify booking for {username} on {target_date}: status {status_code}")
            return False
            
    except Exception as e:
        logging.error(f"Error verifying booking for {username} on {target_date}: {e}")
        return False

def process_auto_booking():
    """
    Process automated bookings based on saved schedules.
    This function retrieves all active schedules and sends commands
    to the reasoning agent for execution.
    """
    logging.info("Starting automated lane booking process")
    
    # Get current day of week
    today = get_day_of_week()
    logging.info(f"Processing bookings for {today}")
    
    # Get all active schedules
    schedules = get_all_active_schedules()
    logging.info(f"Found {len(schedules)} total schedules")
    
    results = []
    for schedule in schedules:
        username = schedule["username"]
        today_command = schedule.get(today)
        
        if not today_command:
            logging.info(f"No booking scheduled for {username} on {today}")
            continue
        
        # Check if this user's booking for today has already run successfully
        if not should_run_booking(username, today):
            logging.info(f"Skipping {username} - booking already completed successfully today")
            results.append({
                "username": username,
                "status": "skipped",
                "message": "Already completed successfully today"
            })
            continue
        
        # Get the MAC password and API key from auth_data table
        mac_password = get_mac_password(username)
        if not mac_password:
            logging.warning(f"Missing MAC password for user {username}, cannot proceed with booking")
            results.append({
                "username": username,
                "status": "error",
                "message": "Missing MAC password"
            })
            continue
        
        # Get the user's API key for agent authentication
        from src.domain.sql.authGateway import get_auth
        user_auth = get_auth(username)
        if not user_auth or not user_auth.get("api_key"):
            logging.warning(f"Missing API key for user {username}, cannot proceed with booking")
            results.append({
                "username": username,
                "status": "error",
                "message": "Missing API key"
            })
            continue
        
        user_api_key = user_auth["api_key"]
        
        # Format date for booking - one week from today
        eastern = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(eastern)
        # Calculate the target booking date (one week from today)
        target_date = now + datetime.timedelta(days=MAC_BOOKING_DAYS_AHEAD)
        booking_date = target_date.strftime("%Y-%m-%d")
        
        # Replace {date} placeholder in the command with the target date
        processed_command = today_command.replace("{date}", booking_date)
        
        # Get the context for this user
        from src.contextManager import load_context_for_authenticated_user
        user_context = load_context_for_authenticated_user(user_api_key, mac_password)
        
        try:
            logging.info(f"Sending command to reasoning agent for {username}: {processed_command}")
            
            # Call the reasoning agent endpoint with detailed logging
            logging.info(f"Making agent request for user {username}...")
            agent_result = call_reasoning_agent(processed_command, username, mac_password, user_api_key)
            logging.info(f"Agent request completed for user {username} with status: {agent_result.get('status')}")
            logging.info(f"Agent result details: {agent_result}")
            
            # Always make a follow-up call to ensure booking happens
            # Check if we have a session_id (which indicates the first call was successful)
            session_id = agent_result.get("session_id")
            logging.info(f"Session ID from first call: {session_id}")
            
            if session_id:
                logging.info(f"First call successful, session_id: {session_id}")
                logging.info(f"Making follow-up call for {username} to force booking")
                
                # Make a follow-up call to force booking
                follow_up_message = "If you booked a lane for me, thank you. If you presented options, please just make a selection you think most fits my preferences and book it."
                
                follow_up_result = call_reasoning_agent(follow_up_message, username, mac_password, user_api_key, session_id)
                logging.info(f"Follow-up agent request completed for user {username} with status: {follow_up_result.get('status')}")
                logging.info(f"Follow-up result details: {follow_up_result}")
                
                # Use the follow-up result for the final status
                if follow_up_result.get("status") == "success":
                    logging.info(f"Agent calls completed successfully for {username}, now verifying booking...")
                    
                    # Wait a moment for the booking to be processed
                    time.sleep(2)
                    
                    # Verify that a booking actually exists for the target date
                    booking_verified = verify_booking_exists(username, booking_date, user_context)
                    
                    if booking_verified:
                        logging.info(f"Successfully verified booking for {username} on {booking_date}")
                        
                        # Update the last successful run timestamp only if booking is verified
                        try:
                            update_last_success(username, today)
                            logging.info(f"Updated last success timestamp for {username} on {today}")
                        except Exception as e:
                            logging.error(f"Failed to update last success timestamp for {username}: {e}")
                        
                        results.append({
                            "username": username,
                            "status": "success",
                            "message": f"Booking verified for {booking_date}"
                        })
                    else:
                        logging.warning(f"Booking verification failed for {username} on {booking_date} - not updating last success")
                        results.append({
                            "username": username,
                            "status": "error",
                            "message": f"Booking attempt completed but no booking found for {booking_date}"
                        })
                else:
                    logging.error(f"Failed to process auto-booking for {username} after follow-up: {follow_up_result}")
                    results.append({
                        "username": username,
                        "status": "error",
                        "message": follow_up_result.get("message", "Booking failed after follow-up")
                    })
            else:
                logging.error(f"Failed to process auto-booking for {username}: No session_id returned from first call")
                results.append({
                    "username": username,
                    "status": "error",
                    "message": agent_result.get("message", "Booking failed - no session established")
                })
                
        except Exception as e:
            logging.exception(f"Error during auto-booking for {username}: {str(e)}")
            results.append({
                "username": username,
                "status": "error", 
                "message": f"Exception: {str(e)}"
            })
    
    return results