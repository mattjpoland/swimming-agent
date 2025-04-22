import os
import psycopg2
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Get database connection string from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logging.error("DATABASE_URL environment variable not found")
    exit(1)

def add_mac_password_column():
    """
    Add the mac_password column to the swim_lane_schedule table.
    This script should be run once and then removed.
    """
    conn = None
    try:
        logging.info("Connecting to the database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # First check if the column already exists to avoid errors
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'swim_lane_schedule' 
                AND column_name = 'mac_password'
            );
        """)
        column_exists = cursor.fetchone()[0]
        
        if column_exists:
            logging.info("mac_password column already exists in the swim_lane_schedule table")
        else:
            # Add the mac_password column
            logging.info("Adding mac_password column to swim_lane_schedule table...")
            cursor.execute("""
                ALTER TABLE swim_lane_schedule 
                ADD COLUMN mac_password TEXT;
            """)
            
            # Commit the transaction
            conn.commit()
            logging.info("Successfully added mac_password column!")
            
        # Display the current table structure for verification
        logging.info("Current table structure:")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'swim_lane_schedule';
        """)
        columns = cursor.fetchall()
        for column in columns:
            logging.info(f"  - {column[0]}: {column[1]}")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed")

if __name__ == "__main__":
    logging.info("Starting the script to add mac_password column...")
    add_mac_password_column()
    logging.info("Script completed")
    print("\n⚠️  IMPORTANT: Delete this script after running it successfully for security reasons ⚠️")