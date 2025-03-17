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
            "enabled": result[4],
        }
    return None

def store_auth(username, api_key, customer_id, alt_customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO auth_data (username, api_key, customer_id, alt_customer_id, enabled)
        VALUES (%s, %s, %s, %s, 0)
        ON CONFLICT (username) DO UPDATE SET 
        api_key = EXCLUDED.api_key,
        customer_id = EXCLUDED.customer_id,
        alt_customer_id = EXCLUDED.alt_customer_id;
    """, (username, api_key, customer_id, alt_customer_id))
    conn.commit()
    conn.close()