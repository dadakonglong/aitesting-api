import sqlite3
import json
import os

DB_PATH = r"D:/testc/aitesting-api\data/apis.db"

def diagnose():
    if not os.path.exists(DB_PATH):
        print("数据库不存在")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. 统计项目
    cursor.execute("SELECT project_id, COUNT(*) as count FROM apis GROUP BY project_id")
    projects = cursor.fetchall()
    print("=== 项目统计 ===")
    for p in projects:
        print(f"项目: {p['project_id']}, 接口数: {p['count']}")
    
    # 2. 检查含有 multipart/form-data 的接口
    print("\n=== 包含 multipart/form-data 的接口 ===")
    cursor.execute("SELECT project_id, method, path, headers FROM apis WHERE headers LIKE '%multipart/form-data%'")
    rows = cursor.fetchall()
    for row in rows:
        print(f"[{row['project_id']}] {row['method']} {row['path']}")
    
    # 3. 检查 GET 接口中非空的 headers
    print("\n=== GET 接口中非空的 headers (潜在污染点) ===")
    cursor.execute("SELECT project_id, path, headers FROM apis WHERE method = 'GET' AND headers != '{}' AND headers IS NOT NULL")
    rows = cursor.fetchall()
    for row in rows:
        print(f"[{row['project_id']}] GET {row['path']}: {row['headers']}")
    
    conn.close()

if __name__ == "__main__":
    diagnose()
