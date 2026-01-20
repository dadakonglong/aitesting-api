import sqlite3
import json
import os

DB_PATH = r"D:/testc/aitesting-api\data/apis.db"

def debug_api_list():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apis ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    print(f"Total APIs: {len(rows)}")
    for r in rows[:15]:
        headers = json.loads(r["headers"] or "{}")
        print(f"[{r['project_id']}] {r['method']} {r['path']}: {headers}")

if __name__ == "__main__":
    debug_api_list()
