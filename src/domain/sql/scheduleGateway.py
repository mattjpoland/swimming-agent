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
    Example:
    {
        "monday": {"pool": "Indoor Pool", "lane": "Lane 1", "time": "08:00:00"},
        "tuesday": None,
        "wednesday": {"pool": "Outdoor Pool", "lane": "Lane 2", "time": "10:00:00"},
        ...
    }
    """
    # Safely extract values from the schedule, handling None values
    def safe_get(day_schedule, key):
        if day_schedule is None:
            return None
        return day_schedule.get(key)
    
    monday_data = schedule.get("monday", None)
    tuesday_data = schedule.get("tuesday", None)
    wednesday_data = schedule.get("wednesday", None)
    thursday_data = schedule.get("thursday", None)
    friday_data = schedule.get("friday", None)
    saturday_data = schedule.get("saturday", None)
    sunday_data = schedule.get("sunday", None)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO swim_lane_schedule (
            username, monday_pool, monday_lane, monday_time,
            tuesday_pool, tuesday_lane, tuesday_time,
            wednesday_pool, wednesday_lane, wednesday_time,
            thursday_pool, thursday_lane, thursday_time,
            friday_pool, friday_lane, friday_time,
            saturday_pool, saturday_lane, saturday_time,
            sunday_pool, sunday_lane, sunday_time
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (username) DO UPDATE SET
            monday_pool = EXCLUDED.monday_pool,
            monday_lane = EXCLUDED.monday_lane,
            monday_time = EXCLUDED.monday_time,
            tuesday_pool = EXCLUDED.tuesday_pool,
            tuesday_lane = EXCLUDED.tuesday_lane,
            tuesday_time = EXCLUDED.tuesday_time,
            wednesday_pool = EXCLUDED.wednesday_pool,
            wednesday_lane = EXCLUDED.wednesday_lane,
            wednesday_time = EXCLUDED.wednesday_time,
            thursday_pool = EXCLUDED.thursday_pool,
            thursday_lane = EXCLUDED.thursday_lane,
            thursday_time = EXCLUDED.thursday_time,
            friday_pool = EXCLUDED.friday_pool,
            friday_lane = EXCLUDED.friday_lane,
            friday_time = EXCLUDED.friday_time,
            saturday_pool = EXCLUDED.saturday_pool,
            saturday_lane = EXCLUDED.saturday_lane,
            saturday_time = EXCLUDED.saturday_time,
            sunday_pool = EXCLUDED.sunday_pool,
            sunday_lane = EXCLUDED.sunday_lane,
            sunday_time = EXCLUDED.sunday_time,
            updated_at = CURRENT_TIMESTAMP;
    """, (
        username,
        safe_get(monday_data, "pool"),
        safe_get(monday_data, "lane"),
        safe_get(monday_data, "time"),
        safe_get(tuesday_data, "pool"),
        safe_get(tuesday_data, "lane"),
        safe_get(tuesday_data, "time"),
        safe_get(wednesday_data, "pool"),
        safe_get(wednesday_data, "lane"),
        safe_get(wednesday_data, "time"),
        safe_get(thursday_data, "pool"),
        safe_get(thursday_data, "lane"),
        safe_get(thursday_data, "time"),
        safe_get(friday_data, "pool"),
        safe_get(friday_data, "lane"),
        safe_get(friday_data, "time"),
        safe_get(saturday_data, "pool"),
        safe_get(saturday_data, "lane"),
        safe_get(saturday_data, "time"),
        safe_get(sunday_data, "pool"),
        safe_get(sunday_data, "lane"),
        safe_get(sunday_data, "time")
    ))
    conn.commit()
    conn.close()

def get_schedule(username):
    """Retrieve the swim lane schedule for a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT monday_pool, monday_lane, monday_time,
               tuesday_pool, tuesday_lane, tuesday_time,
               wednesday_pool, wednesday_lane, wednesday_time,
               thursday_pool, thursday_lane, thursday_time,
               friday_pool, friday_lane, friday_time,
               saturday_pool, saturday_lane, saturday_time,
               sunday_pool, sunday_lane, sunday_time
        FROM swim_lane_schedule
        WHERE username = %s;
    """, (username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "monday": {"pool": result[0], "lane": result[1], "time": result[2]} if result[2] else None,
            "tuesday": {"pool": result[3], "lane": result[4], "time": result[5]} if result[5] else None,
            "wednesday": {"pool": result[6], "lane": result[7], "time": result[8]} if result[8] else None,
            "thursday": {"pool": result[9], "lane": result[10], "time": result[11]} if result[11] else None,
            "friday": {"pool": result[12], "lane": result[13], "time": result[14]} if result[14] else None,
            "saturday": {"pool": result[15], "lane": result[16], "time": result[17]} if result[17] else None,
            "sunday": {"pool": result[18], "lane": result[19], "time": result[20]} if result[20] else None
        }
    return None

def get_all_active_schedules():
    """Retrieve all active swim lane schedules."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, 
               monday_pool, monday_lane, monday_time,
               tuesday_pool, tuesday_lane, tuesday_time,
               wednesday_pool, wednesday_lane, wednesday_time,
               thursday_pool, thursday_lane, thursday_time,
               friday_pool, friday_lane, friday_time,
               saturday_pool, saturday_lane, saturday_time,
               sunday_pool, sunday_lane, sunday_time
        FROM swim_lane_schedule;
    """)
    results = cursor.fetchall()
    conn.close()
    
    schedules = []
    for row in results:
        username = row[0]
        schedule = {
            "username": username,
            "monday": {"pool": row[1], "lane": row[2], "time": row[3]} if row[3] else None,
            "tuesday": {"pool": row[4], "lane": row[5], "time": row[6]} if row[6] else None,
            "wednesday": {"pool": row[7], "lane": row[8], "time": row[9]} if row[9] else None,
            "thursday": {"pool": row[10], "lane": row[11], "time": row[12]} if row[12] else None,
            "friday": {"pool": row[13], "lane": row[14], "time": row[15]} if row[15] else None,
            "saturday": {"pool": row[16], "lane": row[17], "time": row[18]} if row[18] else None,
            "sunday": {"pool": row[19], "lane": row[20], "time": row[21]} if row[21] else None
        }
        schedules.append(schedule)
    
    return schedules