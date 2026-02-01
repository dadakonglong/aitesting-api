"""
AI处理服务主入口
提供场景理解、数据生成、断言生成等AI能力
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

from services.nlu_service import NLUService
from services.scenario_parser import ScenarioParser
from services.data_generator import DataGenerator
from services.assertion_generator import AssertionGenerator
from services.vector_service import VectorService
from services.rag_engine import RAGEngine
from services.data_import_service import DataImportService

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="AI Processing Service",
    description="AI智能处理服务 - 场景理解、数据生成、断言生成",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from routers import import_router
import sqlite3
import json
import uuid
from typing import Any

app.include_router(import_router.router)
from routers import api_management
app.include_router(api_management.router)

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data/apis.db")

# ============= 项目管理路由 (同步自 main_sqlite.py) =============

@app.get("/api/v1/projects")
async def list_projects():
    """获取系统中所有项目信息"""
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/v1/projects")
async def create_project(project: BaseModel):
    """创建新项目"""
    try:
        project_id = str(uuid.uuid4())[:8]
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
            (project_id, project.name if hasattr(project, 'name') else getattr(project, 'dict')().get('name'), 
             project.description if hasattr(project, 'description') else getattr(project, 'dict')().get('description'))
        )
        conn.commit()
        conn.close()
        return {"success": True, "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/projects/{project_id}/export")
async def export_project(project_id: str):
    """导出项目数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = dict(cursor.fetchone() or {})
        if not project: raise HTTPException(status_code=404, detail="项目不存在")
        cursor.execute("SELECT * FROM apis WHERE project_id = ?", (project_id,))
        apis = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM project_environments WHERE project_id = ?", (project_id,))
        environments = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM scenarios WHERE project_id = ?", (project_id,))
        scenarios = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM test_cases WHERE project_id = ?", (project_id,))
        test_cases = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM api_test_cases WHERE project_id = ?", (project_id,))
        api_test_cases = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"version": "1.0", "project": project, "apis": apis, "environments": environments, "scenarios": scenarios, "test_cases": test_cases, "api_test_cases": api_test_cases}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/projects/import")
async def import_project(data: Dict[str, Any]):
    """导入项目数据"""
    try:
        project = data.get("project")
        if not project: raise HTTPException(status_code=400, detail="无效数据")
        project_id = project["id"]
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if cursor.fetchone():
            project_id = f"{project_id}_imported_{uuid.uuid4().hex[:4]}"
            project["id"] = project_id
            project["name"] = f"{project['name']} (导入)"
        cursor.execute("INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                       (project["id"], project["name"], project.get("description", ""), project.get("created_at")))
        def safe_json(v): return json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
        for item in data.get("apis", []):
            cursor.execute("INSERT INTO apis (path, method, summary, description, base_url, parameters, request_body, headers, project_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (item["path"], item["method"], item.get("summary"), item.get("description"), item.get("base_url"), safe_json(item.get("parameters")), safe_json(item.get("request_body")), safe_json(item.get("headers")), project_id, item.get("created_at")))
        for item in data.get("environments", []):
            cursor.execute("INSERT INTO project_environments (project_id, env_name, base_url, is_default, created_at) VALUES (?, ?, ?, ?, ?)",
                           (project_id, item["env_name"], item["base_url"], item.get("is_default", 0), item.get("created_at")))
        for item in data.get("scenarios", []):
            cursor.execute("INSERT INTO scenarios (name, description, natural_language_input, project_id, nlu_result, test_case_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (item.get("name"), item.get("description"), item.get("natural_language_input"), project_id, safe_json(item.get("nlu_result")), item.get("test_case_id"), item.get("created_at")))
        for item in data.get("test_cases", []):
            cursor.execute("INSERT INTO test_cases (name, steps, project_id, created_at) VALUES (?, ?, ?, ?)",
                           (item.get("name"), safe_json(item.get("steps")), project_id, item.get("created_at")))
        for item in data.get("api_test_cases", []):
            cursor.execute("INSERT INTO api_test_cases (project_id, api_id, method, path, source, case_type, name, description, request_template, expected_template, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (project_id, item.get("api_id"), item.get("method"), item.get("path"), item.get("source"), item.get("case_type"), item.get("name"), item.get("description"), safe_json(item.get("request_template")), safe_json(item.get("expected_template")), item.get("created_at"), item.get("updated_at")))
        conn.commit()
        conn.close()
        return {"success": True, "project_id": project_id, "message": f"项目 {project['name']} 已成功导入"}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# 初始化服务
nlu_service = NLUService(
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL", "gpt-4")
)

scenario_parser = ScenarioParser(
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL", "gpt-4")
)

data_generator = DataGenerator(
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL", "gpt-4")
)

assertion_generator = AssertionGenerator(
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL", "gpt-4")
)

vector_service = VectorService(
    qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

rag_engine = RAGEngine(
    qdrant_url=os.getenv("QDRANT_URL", "http://qdrant:6333"),
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

data_import_service = DataImportService(
    vector_service=vector_service
)

# ============= 请求/响应模型 =============

class ScenarioUnderstandingRequest(BaseModel):
    description: str
    project_id: str
    knowledge_context: Optional[Dict] = None

class ScenarioParseRequest(BaseModel):
    nlu_result: Dict
    project_id: str

class DataGenerationRequest(BaseModel):
    param_schema: Dict
    business_rules: List[Dict] = []
    strategy: str = "smart"
    count: int = 1
    # 新增选填字段，用于后端查找 Schema
    api_path: Optional[str] = None
    method: Optional[str] = None
    project_id: str = "default-project"

class AssertionGenerationRequest(BaseModel):
    api_info: Dict
    business_context: Dict = {}
    test_data: Dict = {}

class VectorIndexRequest(BaseModel):
    item_type: str  # api, test_case, scenario
    item_data: Dict

class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10
    filter_type: Optional[str] = None
    project_id: Optional[str] = None

class RAGEnhanceRequest(BaseModel):
    description: str
    project_id: str

# ============= API端点 =============

@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "AI Processing Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

# === NLU相关 ===

@app.post("/api/v1/ai/understand-scenario")
async def understand_scenario(request: ScenarioUnderstandingRequest):
    """
    场景理解 - 自然语言理解
    
    将用户的自然语言描述转换为结构化的场景理解
    """
    try:
        result = await nlu_service.understand_scenario(
            description=request.description,
            knowledge_context=request.knowledge_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ai/parse-scenario")
async def parse_scenario(request: ScenarioParseRequest):
    """
    场景解析 - 生成接口调用序列
    
    基于NLU结果和知识图谱，生成完整的测试步骤
    """
    try:
        result = await scenario_parser.parse_scenario(
            nlu_result=request.nlu_result,
            project_id=request.project_id,
            db_path=DB_PATH
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === 数据生成相关 ===

@app.post("/api/v1/ai/generate-data")
async def generate_data(request: DataGenerationRequest):
    """
    智能数据生成
    
    根据参数schema和业务规则生成测试数据
    """
    try:
    try:
        # 如果 schema 为空但提供了 path/method，尝试从 DB 加载
        target_schema = request.param_schema
        if not target_schema and request.api_path:
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 尝试多条件查找
                query = "SELECT parameters, request_body FROM apis WHERE project_id = ? AND path = ?"
                args = [request.project_id, request.api_path]
                if request.method:
                    query += " AND method = ?"
                    args.append(request.method)
                
                cursor.execute(query, tuple(args))
                row = cursor.fetchone()
                conn.close()

                if row:
                    target_schema = {}
                    # 合并 parameters
                    if row['parameters']:
                        params = json.loads(row['parameters'])
                        for p in params:
                             if isinstance(p, dict) and 'name' in p:
                                 target_schema[p['name']] = p
                    
                    # 合并 request_body
                    if row['request_body']:
                        body = json.loads(row['request_body'])
                        # 尝试提取 properties
                        props = {}
                        if 'content' in body and 'application/json' in body['content']:
                             schema = body['content']['application/json'].get('schema', {})
                             props = schema.get('properties', {})
                        elif 'properties' in body:
                             props = body['properties']
                        
                        target_schema.update(props)
            except Exception as e:
                print(f"Schema lookup failed: {e}")
                # Fallback to empty schema

        result = await data_generator.generate_data(
            param_schema=target_schema,
            business_rules=request.business_rules,
            strategy=request.strategy,
            count=request.count
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === 断言生成相关 ===

@app.post("/api/v1/ai/generate-assertions")
async def generate_assertions(request: AssertionGenerationRequest):
    """
    智能断言生成
    
    根据接口信息和业务上下文生成断言规则
    """
    try:
        result = await assertion_generator.generate_assertions(
            api_info=request.api_info,
            business_context=request.business_context,
            test_data=request.test_data
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === 向量索引相关 ===

@app.post("/api/v1/vector/index")
async def index_item(request: VectorIndexRequest):
    """
    向量化索引
    
    将API、测试用例或场景向量化并索引
    """
    try:
        if request.item_type == "api":
            await vector_service.index_api(request.item_data)
        elif request.item_type == "test_case":
            await vector_service.index_test_case(request.item_data)
        elif request.item_type == "scenario":
            await vector_service.index_scenario(request.item_data)
        else:
            raise ValueError(f"不支持的类型: {request.item_type}")
        
        return {"status": "success", "message": "索引成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/vector/search")
async def semantic_search(request: SemanticSearchRequest):
    """
    语义搜索
    
    基于向量相似度搜索相关内容
    """
    try:
        results = await vector_service.semantic_search(
            query=request.query,
            limit=request.limit,
            filter_type=request.filter_type,
            project_id=request.project_id
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === RAG相关 ===

@app.post("/api/v1/rag/enhance-scenario")
async def enhance_scenario(request: RAGEnhanceRequest):
    """
    RAG增强场景理解
    
    使用检索增强生成技术，提供更丰富的上下文
    """
    try:
        result = await rag_engine.enhance_scenario_understanding(
            user_input=request.description,
            project_id=request.project_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === API管理相关 ===



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
