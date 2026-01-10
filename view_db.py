import sqlite3

# Connect to the database
conn = sqlite3.connect("sales_crm.db")
cursor = conn.cursor()

# Get all rows
cursor.execute("SELECT * FROM leads")
rows = cursor.fetchall()

print("\n📊 DATABASE CONTENTS (sales_crm.db):")
print("-" * 60)
print(f"{'ID':<5} | {'COMPANY':<20} | {'CATEGORY':<10} | {'DATE'}")
print("-" * 60)

for row in rows:
    # row = (id, company, category, email_draft, date)
    print(f"{row[0]:<5} | {row[1]:<20} | {row[2]:<10} | {row[4]}")

conn.close()