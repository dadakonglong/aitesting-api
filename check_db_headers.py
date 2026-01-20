import sqlite3
import json
import os

DB_PATH = r"D:/testc/aitesting-api\data/apis.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print("数据库不存在")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 查询特定项目的最新数据
    cursor.execute("SELECT path, method, headers, project_id FROM apis WHERE project_id = 'ms-增值项目' LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("未找到该项目的数据")
        return

    for row in rows:
        print(f"[{row[3]}] {row[1]} {row[0]}: {row[2]}")

if __name__ == "__main__":
    check_db()
