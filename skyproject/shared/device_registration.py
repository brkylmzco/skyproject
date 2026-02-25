import sqlite3
import os
import logging
from contextlib import contextmanager

# Use environment variable for DB path
default_db_path = os.getenv('DEVICE_DB_PATH', 'device_tokens.db')
DB_PATH = default_db_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS device_tokens (
    user_id TEXT NOT NULL,
    token TEXT NOT NULL,
    platform TEXT NOT NULL,
    PRIMARY KEY (user_id, token)
)''')
conn.commit()

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

class DeviceRegistrationService:
    @staticmethod
    def register_device(user_id: str, token: str, platform: str) -> bool:
        """Register a device token for push notifications."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''INSERT OR REPLACE INTO device_tokens (user_id, token, platform) VALUES (?, ?, ?)''',
                               (user_id, token, platform))
                conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error('Database error during registration: %s', str(e))
            return False

    @staticmethod
    def remove_token(token: str) -> None:
        """Remove a device token from the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''DELETE FROM device_tokens WHERE token = ?''', (token,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error('Database error during token removal: %s', str(e))

    @staticmethod
    def get_all_tokens() -> list:
        """Retrieve all device tokens."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM device_tokens')
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error('Database error during token retrieval: %s', str(e))
            return []
