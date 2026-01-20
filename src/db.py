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
            email_draft TEXT UNIQUE,
            created_at TEXT
        )
    ''')
    
    # SENIOR-LEVEL FIX: Add index for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_company_name ON leads (company_name)')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized (sales_crm.db).")

def save_lead(company_name, category, email_draft):
    """Saves the result to the database in a thread-safe manner."""
    try:
        # SENIOR-LEVEL FIX: Use a new connection for each thread/transaction
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Use INSERT OR IGNORE to handle the UNIQUE constraint gracefully
            cursor.execute('''
                INSERT OR IGNORE INTO leads (company_name, category, email_draft, created_at)
                VALUES (?, ?, ?, ?)
            ''', (company_name, category, email_draft, timestamp))
            
            conn.commit()
            # Check if a row was actually inserted
            if cursor.rowcount > 0:
                print(f"💾 Saved to Database: {company_name or 'Unknown'} ({category})")
            else:
                print(f"⚠️ Duplicate email draft detected. Not saved.")
                
    except sqlite3.Error as e:
        print(f"❌ Database Error: {e}")