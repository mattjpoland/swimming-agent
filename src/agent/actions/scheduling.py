from flask import jsonify, g
from src.agent.base import AgentAction
from src.domain.sql.scheduleGateway import add_or_update_schedule, get_schedule
from src.domain.sql.authGateway import get_mac_password
import logging
import json
from datetime import time, datetime

class ManageScheduleAction(AgentAction):
    @property
    def name(self):
        return "manage_schedule"
    
    @property
    def description(self):
        return "Update or view a user's recurring swim lane automatic booking schedule."
    
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "day": {
                    "type": "string", 
                    "description": "The day of week to update (monday, tuesday, wednesday, thursday, friday, saturday, sunday)."
                },
                "pool": {
                    "type": "string", 
                    "description": "The pool to book ('Indoor Pool' or 'Outdoor Pool'). Required when adding a schedule."
                },
                "lane": {
                    "type": "string", 
                    "description": "The lane to book (e.g., 'Lane 1', 'Lane 2'). Required when adding a schedule."
                },
                "time": {
                    "type": "string", 
                    "description": "The time to book in 24-hour format (e.g., '06:00:00', '17:30:00'). Required when adding a schedule."
                },
                "action": {
                    "type": "string",
                    "enum": ["view", "add", "remove", "clear"],
                    "description": "The action to perform: view schedule, add a booking, remove a specific day's booking, or clear entire schedule."
                }
            },
            "required": ["action"]
        }
    
    @property
    def prompt_instructions(self):
        return (
                "You can help users manage their automated swim lane booking schedule. "
                "Users can set up recurring bookings for specific days of the week. "
                "Use the manage_schedule function with the following actions: "
                "- 'view': Show the user's current schedule (no additional parameters needed) "
                "- 'add': Add or update a booking for a specific day (requires day, pool, lane, time) "
                "- 'remove': Remove a booking for a specific day (requires day) "
                "- 'clear': Clear the entire schedule (no additional parameters needed) "
                "For time, use 24-hour format (e.g., '06:00:00' for 6:00 AM). "
                "The auto-booking system will automatically book lanes according to the user's schedule "
                "if they have their MAC password configured in the system."
        )
    
    @property
    def response_format_instructions(self):
        return (
            "Format your response as follows:\n"
            "1. For 'view' action, you MUST ALWAYS present the user's COMPLETE SCHEDULE in your response:\n"
            "   - ALWAYS INCLUDE ALL scheduled days, times, pools and lanes in your response\n"
            "   - If auto-booking is inactive, still show the FULL SCHEDULE but clearly note it's not currently auto-booking\n"
            "   - If the schedule is in the response data, but not in your message, this is an ERROR - fix it by including the schedule\n"
            "   - NEVER tell a user they 'don't have a schedule' if the API returns schedule data\n"
            "2. For 'add' action, confirm the day, time, pool, and lane that was scheduled\n"
            "3. For 'remove' action, confirm which day's booking was removed\n"
            "4. For 'clear' action, confirm that the entire schedule was cleared\n"
            "5. If there was an error, explain clearly what went wrong and how to fix it\n"
            "6. Include a brief explanation of how the auto-booking system works"
        )
    
    def _days_to_ordinal(self, day):
        day = day.lower()
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if day in days:
            return day
        
        ordinals = {
            "1st": "monday",
            "2nd": "tuesday", 
            "3rd": "wednesday",
            "4th": "thursday",
            "5th": "friday",
            "6th": "saturday",
            "7th": "sunday",
            "1": "monday",
            "2": "tuesday",
            "3": "wednesday",
            "4": "thursday", 
            "5": "friday",
            "6": "saturday",
            "7": "sunday"
        }
        
        return ordinals.get(day, day)
    
    def _make_json_serializable(self, obj):
        """Convert non-serializable objects to JSON-serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (datetime, time)):
            return obj.isoformat()
        else:
            return obj
    
    def execute(self, arguments, context, user_input, **kwargs):
        """Execute the schedule management action."""
        try:
            # Extract parameters
            action = arguments.get("action", "view").lower()
            day = self._days_to_ordinal(arguments.get("day", "")) if arguments.get("day") else None
            pool = arguments.get("pool")
            lane = arguments.get("lane")
            time = arguments.get("time") 
            
            # Check for username - first try MAC_USERNAME, then try USERNAME, finally check IS_ADMIN
            username = context.get("MAC_USERNAME") or context.get("USERNAME")
            is_admin = bool(context.get("IS_ADMIN", False))
            
            if not username:
                if is_admin:
                    # For admins, use a default admin username if actual username isn't found
                    username = "admin_user"
                    logging.info(f"Admin access detected, using default username: {username}")
                else:
                    return jsonify({
                        "message": "You need to be logged in to manage your schedule.",
                        "status": "error"
                    }), 401
            
            logging.info(f"Managing schedule for user: {username} (Admin: {is_admin})")
            
            # Get current schedule
            current_schedule = get_schedule(username) or {}
            
            if action == "view":
                # Check if user has a MAC password set (for informational purposes only)
                has_password = get_mac_password(username) is not None
                
                # Make the schedule JSON-serializable
                serializable_schedule = self._make_json_serializable(current_schedule)
                
                # Check if the schedule has any configured days
                has_schedule_items = any(day_schedule is not None for day_schedule in current_schedule.values())
                
                if not has_schedule_items:
                    return jsonify({
                        "message": "You don't have any automated bookings scheduled yet. Use the add action to set up your schedule.",
                        "schedule": {},
                        "status": "success"
                    }), 200
                
                # Format the schedule details into a human-readable string
                schedule_details = []
                days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                for day in days:
                    day_data = current_schedule.get(day)
                    if day_data:
                        pool = day_data.get("pool", "Unknown pool")
                        lane = day_data.get("lane", "Unknown lane")
                        time_value = day_data.get("time", "Unknown time")
                        schedule_details.append(f"- {day.capitalize()}: {pool}, {lane} at {time_value}")
                
                schedule_text = "\n".join(schedule_details)
                
                # Return the schedule with appropriate message based on auto-booking status
                auto_booking_status = "active" if has_password else "inactive (MAC password not configured)"
                
                message = (f"Here's your current automated booking schedule (Auto-booking is {auto_booking_status}):\n\n"
                          f"{schedule_text}\n\n"
                          f"The system will automatically book these lanes according to this schedule "
                          f"{'when it runs each day' if has_password else 'once you configure your MAC password'}.")
                
                return jsonify({
                    "message": message,
                    "schedule": serializable_schedule,
                    "status": "success",
                    "auto_booking_enabled": has_password
                }), 200
                
            elif action == "add":
                # Validate required parameters
                if not all([day, pool, lane, time]):
                    return jsonify({
                        "message": "Missing required parameters. Please provide day, pool, lane, and time.",
                        "status": "error"
                    }), 400
                
                # Initialize or update schedule
                if not current_schedule:
                    schedule = {
                        "monday": None,
                        "tuesday": None,
                        "wednesday": None,
                        "thursday": None,
                        "friday": None,
                        "saturday": None,
                        "sunday": None
                    }
                else:
                    schedule = current_schedule.copy()
                
                # Check if they have a password already (for informational purposes only)
                has_password = get_mac_password(username) is not None
                auto_booking_message = " Auto-booking is active." if has_password else " Note: Auto-booking is inactive - MAC password not configured."
                
                # Update the specific day
                schedule[day] = {
                    "pool": pool,
                    "lane": lane,
                    "time": time
                }
                
                # Save to database
                add_or_update_schedule(username, schedule)
                
                return jsonify({
                    "message": f"Successfully scheduled {pool}, {lane} for {day.capitalize()} at {time}." + auto_booking_message,
                    "status": "success",
                    "auto_booking_enabled": has_password
                }), 200
                
            elif action == "remove":
                # Validate parameters
                if not day:
                    return jsonify({
                        "message": "Please specify which day's booking to remove.",
                        "status": "error"
                    }), 400
                
                if not current_schedule:
                    return jsonify({
                        "message": "You don't have any scheduled bookings to remove.",
                        "status": "error"
                    }), 400
                
                # Clone the schedule
                schedule = current_schedule.copy()
                
                # Check if there's anything scheduled for this day
                if not schedule.get(day):
                    return jsonify({
                        "message": f"You don't have any bookings scheduled for {day.capitalize()}.",
                        "status": "error"
                    }), 400
                
                # Remove the booking for this day
                schedule[day] = None
                
                # Save back to database
                add_or_update_schedule(username, schedule)
                
                return jsonify({
                    "message": f"Successfully removed the booking for {day.capitalize()}.",
                    "status": "success"
                }), 200
                
            elif action == "clear":
                if not current_schedule:
                    return jsonify({
                        "message": "You don't have any scheduled bookings to clear.",
                        "status": "error"
                    }), 400
                
                # Create an empty schedule
                empty_schedule = {
                    "monday": None,
                    "tuesday": None,
                    "wednesday": None,
                    "thursday": None,
                    "friday": None,
                    "saturday": None,
                    "sunday": None
                }
                
                # Save the empty schedule
                add_or_update_schedule(username, empty_schedule)
                
                return jsonify({
                    "message": "Your entire booking schedule has been cleared.",
                    "status": "success"
                }), 200
                
            else:
                return jsonify({
                    "message": f"Unknown action: {action}. Valid actions are: view, add, remove, clear.",
                    "status": "error"
                }), 400
                
        except Exception as e:
            logging.exception(f"Error in manage_schedule action: {str(e)}")
            return jsonify({
                "message": f"I encountered an error while managing your schedule: {str(e)}",
                "status": "error"
            }), 500