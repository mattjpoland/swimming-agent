import psycopg2
import os
import logging

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