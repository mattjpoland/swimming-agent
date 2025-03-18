import psycopg2
import os

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
            "is_enabled": result[4],
            "is_admin": result[5]
        }
    return None

def store_auth(username, api_key, customer_id, alt_customer_id, is_admin=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO auth_data (username, api_key, customer_id, alt_customer_id, is_enabled, is_admin)
        VALUES (%s, %s, %s, %s, 0, %s)
        ON CONFLICT (username) DO UPDATE SET 
        api_key = EXCLUDED.api_key,
        customer_id = EXCLUDED.customer_id,
        alt_customer_id = EXCLUDED.alt_customer_id,
        is_admin = EXCLUDED.is_admin;
    """, (username, api_key, customer_id, alt_customer_id, is_admin))
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
            "is_admin": result[5]
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
    cursor.execute("UPDATE auth_data SET is_enabled = NOT is_enabled WHERE username = %s", (username,))
    conn.commit()
    conn.close()