import sqlite3
import os

# Try to find the DB
possible_paths = [
    "d:/testc/aitesting-api/data/apis.db",
    "d:/testc/aitesting-api/services/data/apis.db",
    "d:/testc/aitesting-api/services/ai-processing/data/apis.db"
]

found = False
for path in possible_paths:
    if os.path.exists(path):
        print(f"Found DB at: {path}")
        try:
            conn = sqlite3.connect(path)
            c = conn.cursor()
            c.execute("SELECT count(*) FROM apis")
            count = c.fetchone()[0]
            print(f"Total APIs: {count}")
            
            if count > 0:
                c.execute("SELECT id, method, path, project_id FROM apis LIMIT 5")
                for row in c.fetchall():
                    print(f" - {row}")
            else:
                print("Table 'apis' is empty.")
            
            conn.close()
            found = True
        except Exception as e:
            print(f"Error reading {path}: {e}")

if not found:
    print("No database file found in expected locations.")
