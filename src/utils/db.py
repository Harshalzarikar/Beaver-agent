import sqlite3
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Database:
    def __init__(self):
        self.db_name = settings.db_name

    def init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT,
                    category TEXT,
                    company TEXT,
                    draft TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        logger.info("Database initialized.")

    def save_record(self, category: str, company: str, draft: str, thread_id: str = "default"):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "INSERT INTO processed_emails (thread_id, category, company, draft) VALUES (?, ?, ?, ?)",
                (thread_id, category, company, draft)
            )

db = Database()
