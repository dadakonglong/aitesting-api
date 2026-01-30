# -*- coding: utf-8 -*-
"""
补充缺失的项目管理 API 端点
"""

# 添加到 main_sqlite.py 文件末尾的代码

@app.post("/api/v1/projects")
async def create_project(project: dict):
    """创建新项目"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        project_id = project.get('id') or project.get('name')
        project_name = project.get('name')
        description = project.get('description', '')
        
        cursor.execute("""
            INSERT OR REPLACE INTO projects (id, name, description, created_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (project_id, project_name, description))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "project_id": project_id}
    except Exception as e:
        print(f"创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
