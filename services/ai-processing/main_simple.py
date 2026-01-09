"""
简化版后端服务 - 只支持 Swagger 导入
解决网络问题无法安装依赖的临时方案
"""
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn

app = FastAPI(title="AI Testing API - Simplified")

# 内存存储（临时方案）
imported_apis = []

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/v1/import/swagger")
async def import_swagger(
    source: str = Form(None),
    file: UploadFile = File(None)
):
    """Swagger 导入接口（简化版）"""
    try:
        swagger_data = None
        
        # URL 导入
        if source:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(source)
                swagger_data = response.json()
        
        # 文件上传
        elif file:
            content = await file.read()
            swagger_data = json.loads(content)
        
        if not swagger_data:
            return {"success": False, "message": "请提供 URL 或文件"}
        
        # 简单解析 Swagger
        apis = []
        paths = swagger_data.get("paths", {})
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    api_item = {
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "project_id": "default-project"
                    }
                    apis.append(api_item)
        
        # 保存到内存存储
        global imported_apis
        imported_apis = apis
        
        return {
            "success": True,
            "message": f"成功解析 {len(apis)} 个 API",
            "indexed": len(apis),  # 前端期望的字段
            "total": len(apis),    # 前端期望的字段
            "apis": apis,
            "project_id": "default-project"  # 前端期望的字段
        }
        
    except Exception as e:
        return {"success": False, "message": f"导入失败: {str(e)}"}

@app.get("/api/v1/apis")
async def list_apis():
    """API 列表（简化版）"""
    return imported_apis

if __name__ == "__main__":
    print("🚀 启动简化版后端服务...")
    print("📝 注意：这是临时版本，只支持基本的 Swagger 导入功能")
    uvicorn.run(app, host="0.0.0.0", port=8000)
