import sqlite3
import json

path = "d:/testc/aitesting-api/data/apis.db"
conn = sqlite3.connect(path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT * FROM apis WHERE path LIKE '%/sign/create%'")
rows = c.fetchall()

print(f"Found {len(rows)} APIs matching '/sign/create'")

for row in rows:
    print(f"\n--- API: {row['method']} {row['path']} ---")
    print(f"ID: {row['id']}")
    print(f"Project ID: {row['project_id']}")
    
    try:
        if row['parameters']:
            print("Parameters (Raw):", row['parameters'])
            print("Parameters (Parsed):", json.loads(row['parameters']))
        else:
            print("Parameters: None/Empty")
            
        if row['request_body']:
            print("Request Body (Raw):", row['request_body'])
            print("Request Body (Parsed):", json.loads(row['request_body']))
        else:
            print("Request Body: None/Empty")
            
        if row['headers']:
            print("Headers (Raw):", row['headers'])
            print("Headers (Parsed):", json.loads(row['headers']))
        else:
            print("Headers: None/Empty")

    except Exception as e:
        print(f"Error parsing JSON: {e}")

conn.close()
