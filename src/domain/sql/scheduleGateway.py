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
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        schedule.get("monday", {}).get("pool"),
        schedule.get("monday", {}).get("lane"),
        schedule.get("monday", {}).get("time"),
        schedule.get("tuesday", {}).get("pool"),
        schedule.get("tuesday", {}).get("lane"),
        schedule.get("tuesday", {}).get("time"),
        schedule.get("wednesday", {}).get("pool"),
        schedule.get("wednesday", {}).get("lane"),
        schedule.get("wednesday", {}).get("time"),
        schedule.get("thursday", {}).get("pool"),
        schedule.get("thursday", {}).get("lane"),
        schedule.get("thursday", {}).get("time"),
        schedule.get("friday", {}).get("pool"),
        schedule.get("friday", {}).get("lane"),
        schedule.get("friday", {}).get("time"),
        schedule.get("saturday", {}).get("pool"),
        schedule.get("saturday", {}).get("lane"),
        schedule.get("saturday", {}).get("time"),
        schedule.get("sunday", {}).get("pool"),
        schedule.get("sunday", {}).get("lane"),
        schedule.get("sunday", {}).get("time"),
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
            "sunday": {"pool": result[18], "lane": result[19], "time": result[20]} if result[20] else None,
        }
    return None