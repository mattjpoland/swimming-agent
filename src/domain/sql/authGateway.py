import psycopg2
import os
import logging

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def get_auth(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auth_data WHERE username = %s", (username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "username": result[0],
            "api_key": result[1],
            "customer_id": result[2],
            "alt_customer_id": result[3],
            "is_enabled": bool(result[4]),  # Convert to boolean
            "is_admin": bool(result[5]),    # Convert to boolean
            "mac_password": result[6] if len(result) > 6 else None  # Add mac_password if it exists
        }
    return None

def store_auth(username, api_key, customer_id, alt_customer_id, is_enabled=False, is_admin=False, mac_password=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO auth_data (username, api_key, customer_id, alt_customer_id, is_enabled, is_admin, mac_password)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (username) DO UPDATE SET 
        api_key = EXCLUDED.api_key,
        customer_id = EXCLUDED.customer_id,
        alt_customer_id = EXCLUDED.alt_customer_id,
        is_enabled = EXCLUDED.is_enabled,
        is_admin = EXCLUDED.is_admin,
        mac_password = CASE WHEN EXCLUDED.mac_password IS NOT NULL THEN EXCLUDED.mac_password ELSE auth_data.mac_password END;
    """, (username, api_key, customer_id, alt_customer_id, is_enabled, is_admin, mac_password))
    conn.commit()
    conn.close()

def get_auth_by_api_key(api_key):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auth_data WHERE api_key = %s", (api_key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "username": result[0],
            "api_key": result[1],
            "customer_id": result[2],
            "alt_customer_id": result[3],
            "is_enabled": result[4],
            "is_admin": result[5],
            "mac_password": result[6] if len(result) > 6 else None  # Add mac_password if it exists
        }
    return None

def get_all_auth_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auth_data")
    results = cursor.fetchall()
    conn.close()
    return results

def toggle_auth_enabled(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE auth_data
        SET is_enabled = NOT is_enabled
        WHERE username = %s
    """, (username,))
    conn.commit()
    conn.close()

def update_mac_password(username, mac_password):
    """Update the MAC password for a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE auth_data
        SET mac_password = %s
        WHERE username = %s
    """, (mac_password, username))
    rows_updated = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_updated > 0

def get_mac_password(username):
    """Get the MAC password for a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT mac_password FROM auth_data WHERE username = %s", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def delete_user(username):
    """Delete a user from the auth_data table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM auth_data WHERE username = %s", (username,))
    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0

def update_api_key(username, new_api_key):
    """Update the API key for a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE auth_data
        SET api_key = %s
        WHERE username = %s
    """, (new_api_key, username))
    rows_updated = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_updated > 0