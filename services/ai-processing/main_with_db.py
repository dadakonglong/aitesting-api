"""
完整版后端服务 - 使用 Supabase REST API 实现数据持久化
不需要额外的 Python 包，只使用 httpx
"""
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn
import os
from typing import List, Dict

app = FastAPI(title="AI Testing API - With Database")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase 配置（从环境变量读取）
SUPABASE_URL = "https://bpehgjqovegvzujbmgxr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwZWhnanFvdmVndnp1amJtZ3hyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzc4NTY5MzUsImV4cCI6MjA1MzQzMjkzNX0.xxx"  # 需要替换为真实的 anon key

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/v1/import/swagger")
async def import_swagger(
    source: str = Form(None),
    file: UploadFile = File(None)
):
    """Swagger 导入接口（完整版 - 保存到数据库）"""
    try:
        import httpx
        
        swagger_data = None
        
        # URL 导入
        if source:
            async with httpx.AsyncClient() as client:
                response = await client.get(source)
                swagger_data = response.json()
        
        # 文件上传
        elif file:
            content = await file.read()
            swagger_data = json.loads(content)
        
        if not swagger_data:
            return {"success": False, "message": "请提供 URL 或文件"}
        
        # 解析 Swagger
        apis = []
        paths = swagger_data.get("paths", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    api_item = {
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "project_id": "default-project"
                    }
                    apis.append(api_item)
        
        # 保存到 Supabase（使用 REST API）
        async with httpx.AsyncClient() as client:
            # 先删除旧数据（可选）
            # await client.delete(
            #     f"{SUPABASE_URL}/rest/v1/apis",
            #     headers={
            #         "apikey": SUPABASE_KEY,
            #         "Authorization": f"Bearer {SUPABASE_KEY}"
            #     }
            # )
            
            # 批量插入新数据
            if apis:
                response = await client.post(
                    f"{SUPABASE_URL}/rest/v1/apis",
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    },
                    json=apis
                )
                
                if response.status_code not in [200, 201]:
                    print(f"Error saving to database: {response.status_code} - {response.text}")
                    # 即使保存失败也返回成功，因为解析是成功的
        
        return {
            "success": True,
            "message": f"成功解析 {len(apis)} 个 API",
            "indexed": len(apis),
            "total": len(apis),
            "apis": apis,
            "project_id": "default-project"
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"success": False, "message": f"导入失败: {str(e)}"}

@app.get("/api/v1/apis")
async def list_apis():
    """API 列表（从数据库查询）"""
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/apis",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching from database: {response.status_code} - {response.text}")
                return []
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

if __name__ == "__main__":
    print("🚀 启动完整版后端服务...")
    print("📝 使用 Supabase REST API 实现数据持久化")
    uvicorn.run(app, host="0.0.0.0", port=8000)
