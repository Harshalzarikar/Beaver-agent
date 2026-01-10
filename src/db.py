import sqlite3
import os
from datetime import datetime

# Creates the DB file in the main folder, not inside src
DB_NAME = "sales_crm.db"

def init_db():
    """Creates the table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create table to store leads and complaints
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            category TEXT,
            email_draft TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized (sales_crm.db).")

def save_lead(company_name, category, email_draft):
    """Saves the result to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Insert data safely
    cursor.execute('''
        INSERT INTO leads (company_name, category, email_draft, created_at)
        VALUES (?, ?, ?, ?)
    ''', (company_name, category, email_draft, timestamp))
    
    conn.commit()
    conn.close()
    print(f"💾 Saved to Database: {company_name or 'Unknown'} ({category})")