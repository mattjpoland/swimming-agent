import os
import datetime
import logging
import requests
from src.domain.sql.scheduleGateway import get_all_active_schedules
from src.domain.sql.authGateway import get_mac_password
import pytz

def get_day_of_week():
    """Get the current day of the week in lowercase."""
    eastern = pytz.timezone('US/Eastern')
    today = datetime.datetime.now(eastern)
    return today.strftime("%A").lower()

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
        
        # Get the MAC password from auth_data table
        mac_password = get_mac_password(username)
        if not mac_password:
            logging.warning(f"Missing MAC password for user {username}, cannot proceed with booking")
            results.append({
                "username": username,
                "status": "error",
                "message": "Missing MAC password"
            })
            continue
        
        # Format date for booking
        eastern = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(eastern)
        booking_date = now.strftime("%Y-%m-%d")
        
        # Replace {date} placeholder in the command with today's date
        processed_command = today_command.replace("{date}", booking_date)
        
        try:
            logging.info(f"Sending command to reasoning agent for {username}: {processed_command}")
            
            # Call the reasoning agent endpoint
            agent_result = call_reasoning_agent(processed_command, username, mac_password)
            
            if agent_result.get("status") == "success":
                logging.info(f"Successfully processed auto-booking for {username}")
                results.append({
                    "username": username,
                    "status": "success",
                    "message": agent_result.get("message", "Booking processed successfully")
                })
            else:
                logging.error(f"Failed to process auto-booking for {username}: {agent_result}")
                results.append({
                    "username": username,
                    "status": "error",
                    "message": agent_result.get("message", "Booking failed")
                })
                
        except Exception as e:
            logging.exception(f"Error during auto-booking for {username}: {str(e)}")
            results.append({
                "username": username,
                "status": "error", 
                "message": f"Exception: {str(e)}"
            })
    
    return results

def call_reasoning_agent(command, username, mac_password):
    """
    Call the reasoning agent endpoint with the scheduling command.
    """
    try:
        # Prepare the request payload
        payload = {
            "user_input": command,
            "response_format": "auto"
        }
        
        # Prepare headers with authentication
        headers = {
            "Content-Type": "application/json",
            "x-api-key": os.getenv("API_KEY", ""),
            "x-mac-username": username,
            "x-mac-password": mac_password
        }
          # Make the request to the agent endpoint
        agent_url = f"https://swimming-agent.onrender.com/agent/chat"
        response = requests.post(agent_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return {
                "status": "success",
                "message": result.get("message", "Command processed successfully"),
                "details": result
            }
        else:
            return {
                "status": "error",
                "message": f"Agent endpoint returned status {response.status_code}: {response.text}"
            }
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to call reasoning agent: {e}")
        return {
            "status": "error",
            "message": f"Failed to communicate with reasoning agent: {str(e)}"
        }
    except Exception as e:
        logging.error(f"Unexpected error calling reasoning agent: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }