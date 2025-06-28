import psycopg2
import os
import logging
import datetime
import pytz

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def add_or_update_schedule(username, schedule):
    """
    Add or update a user's swim lane schedule.
    The schedule parameter should be a dictionary with keys for each day of the week.
    Each day should contain a command string for the reasoning agent or None.
    
    Example:
    {
        "monday": "Look up available swim lane availability and book a swim lane on {date}. I would prefer outdoor pool at 7PM for 60 minutes. I'll take any lane but prefer 5, 2, 4, 3, 6, then 1. I'm willing to go a half hour earlier or later if need be. And as a last resort I'm also willing to shorten it to 30 minutes.",
        "tuesday": None,
        "wednesday": "Book indoor pool at 6AM for 30 minutes, any available lane",
        "thursday": "Book outdoor pool lane 2 at 5:30 PM for 60 minutes on {date}",
        "friday": None,
        "saturday": "Look for availability and book any outdoor lane for 45 minutes around 8 AM on {date}",
        "sunday": None
    }
    """
    # Extract command strings for each day
    monday_command = schedule.get("monday")
    tuesday_command = schedule.get("tuesday")
    wednesday_command = schedule.get("wednesday")
    thursday_command = schedule.get("thursday")
    friday_command = schedule.get("friday")
    saturday_command = schedule.get("saturday")
    sunday_command = schedule.get("sunday")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO swim_lane_schedule (
            username, monday_command, tuesday_command, wednesday_command,
            thursday_command, friday_command, saturday_command, sunday_command
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (username) DO UPDATE SET
            monday_command = EXCLUDED.monday_command,
            tuesday_command = EXCLUDED.tuesday_command,
            wednesday_command = EXCLUDED.wednesday_command,
            thursday_command = EXCLUDED.thursday_command,
            friday_command = EXCLUDED.friday_command,
            saturday_command = EXCLUDED.saturday_command,
            sunday_command = EXCLUDED.sunday_command,
            updated_at = CURRENT_TIMESTAMP;
    """, (
        username,
        monday_command,
        tuesday_command,
        wednesday_command,
        thursday_command,
        friday_command,
        saturday_command,
        sunday_command
    ))
    conn.commit()
    conn.close()

def get_schedule(username):
    """Retrieve the swim lane schedule for a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT monday_command, tuesday_command, wednesday_command,
               thursday_command, friday_command, saturday_command, sunday_command
        FROM swim_lane_schedule
        WHERE username = %s;
    """, (username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "monday": result[0] if result[0] else None,
            "tuesday": result[1] if result[1] else None,
            "wednesday": result[2] if result[2] else None,
            "thursday": result[3] if result[3] else None,
            "friday": result[4] if result[4] else None,
            "saturday": result[5] if result[5] else None,
            "sunday": result[6] if result[6] else None
        }
    return None

def get_all_active_schedules():
    """Retrieve all active swim lane schedules."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, monday_command, tuesday_command, wednesday_command,
               thursday_command, friday_command, saturday_command, sunday_command
        FROM swim_lane_schedule;
    """)
    results = cursor.fetchall()
    conn.close()
    
    schedules = []
    for row in results:
        username = row[0]
        schedule = {
            "username": username,
            "monday": row[1] if row[1] else None,
            "tuesday": row[2] if row[2] else None,
            "wednesday": row[3] if row[3] else None,
            "thursday": row[4] if row[4] else None,
            "friday": row[5] if row[5] else None,
            "saturday": row[6] if row[6] else None,
            "sunday": row[7] if row[7] else None
        }
        schedules.append(schedule)
    
    return schedules

def delete_schedule(username):
    """Delete a user's swim lane schedule."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM swim_lane_schedule
        WHERE username = %s;
    """, (username,))
    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0

def update_last_success(username, day_of_week):
    """
    Update the last successful run timestamp for a specific user and day.
    This should be called only after a booking attempt completes successfully.
    
    Args:
        username: The username to update
        day_of_week: The day of the week (e.g., 'monday', 'tuesday', etc.)
    """
    column_name = f"{day_of_week}_last_success"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            UPDATE swim_lane_schedule
            SET {column_name} = CURRENT_TIMESTAMP
            WHERE username = %s;
        """, (username,))
        conn.commit()
        logging.info(f"Updated {column_name} for user {username}")
    except Exception as e:
        logging.error(f"Failed to update {column_name} for user {username}: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def should_run_booking(username, day_of_week, cutoff_time=None):
    """
    Check if a booking should run based on the last successful run timestamp.
    
    Args:
        username: The username to check
        day_of_week: The day of the week (e.g., 'monday', 'tuesday', etc.)
        cutoff_time: Optional datetime to check against. If not provided, uses midnight of current day.
    
    Returns:
        bool: True if booking should run, False if it already ran successfully today
    """
    column_name = f"{day_of_week}_last_success"
    
    # If no cutoff time provided, use midnight of current day in Eastern time
    if cutoff_time is None:
        eastern = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(eastern)
        cutoff_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT {column_name}
            FROM swim_lane_schedule
            WHERE username = %s;
        """, (username,))
        result = cursor.fetchone()
        
        if result and result[0]:
            last_success = result[0]
            # Make last_success timezone-aware if it isn't already
            if last_success.tzinfo is None:
                # Assume database timestamps are in UTC
                last_success = pytz.utc.localize(last_success)
            
            # Convert cutoff_time to UTC for comparison if needed
            if cutoff_time.tzinfo is not None:
                cutoff_time_utc = cutoff_time.astimezone(pytz.utc)
            else:
                cutoff_time_utc = cutoff_time
            
            # If last success was after the cutoff time, don't run again
            if last_success > cutoff_time_utc:
                logging.info(f"Skipping {username} on {day_of_week} - already ran successfully at {last_success}")
                return False
        
        # No last success recorded or it was before cutoff time
        return True
        
    except Exception as e:
        logging.error(f"Error checking last success for {username} on {day_of_week}: {e}")
        # On error, allow the booking to proceed
        return True
    finally:
        cursor.close()
        conn.close()

def get_schedules_with_last_success():
    """
    Retrieve all active swim lane schedules with their last success timestamps.
    This is useful for admin monitoring.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, 
               monday_command, tuesday_command, wednesday_command,
               thursday_command, friday_command, saturday_command, sunday_command,
               monday_last_success, tuesday_last_success, wednesday_last_success,
               thursday_last_success, friday_last_success, saturday_last_success, sunday_last_success
        FROM swim_lane_schedule;
    """)
    results = cursor.fetchall()
    conn.close()
    
    schedules = []
    for row in results:
        username = row[0]
        schedule = {
            "username": username,
            "monday": row[1] if row[1] else None,
            "tuesday": row[2] if row[2] else None,
            "wednesday": row[3] if row[3] else None,
            "thursday": row[4] if row[4] else None,
            "friday": row[5] if row[5] else None,
            "saturday": row[6] if row[6] else None,
            "sunday": row[7] if row[7] else None,
            "monday_last_success": row[8] if row[8] else None,
            "tuesday_last_success": row[9] if row[9] else None,
            "wednesday_last_success": row[10] if row[10] else None,
            "thursday_last_success": row[11] if row[11] else None,
            "friday_last_success": row[12] if row[12] else None,
            "saturday_last_success": row[13] if row[13] else None,
            "sunday_last_success": row[14] if row[14] else None
        }
        schedules.append(schedule)
    
    return schedules