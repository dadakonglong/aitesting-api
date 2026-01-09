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
app.include_router(import_router.router)

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
            project_id=request.project_id
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
        result = await data_generator.generate_data(
            param_schema=request.param_schema,
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

@app.get("/api/v1/apis")
async def list_apis(project_id: Optional[str] = None, limit: int = 100):
    """
    获取已导入的API列表
    
    返回所有已索引到向量数据库的API
    """
    try:
        apis = vector_service.list_apis(project_id=project_id, limit=limit)
        return {
            "total": len(apis),
            "apis": apis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
