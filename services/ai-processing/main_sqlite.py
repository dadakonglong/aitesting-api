from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn
import sqlite3
import os
import httpx
import urllib.parse
from typing import List, Dict, Optional, Any
from datetime import datetime
import re
from pydantic import BaseModel
from dotenv import load_dotenv
import numpy as np

# 加载环境变量
load_dotenv()

# 导入轻量级服务
try:
    from lightweight_services import LightweightKnowledgeGraph, LightweightVectorSearch
    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 轻量级服务导入失败: {e}")
    SERVICES_AVAILABLE = False

app = FastAPI(title="AI Testing API - Unified Edition")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路径配置
BASE_DIR = "D:/testc/aitesting-api"
DB_PATH = os.path.join(BASE_DIR, "data/apis.db")
KG_PATH = os.path.join(BASE_DIR, "data/knowledge_graph.pkl")
VECTOR_DB_PATH = os.path.join(BASE_DIR, "data/vectors.db")

# 功能开关配置
ENABLE_KNOWLEDGE_GRAPH = os.getenv("ENABLE_KNOWLEDGE_GRAPH", "true").lower() == "true"
ENABLE_VECTOR_SEARCH = os.getenv("ENABLE_VECTOR_SEARCH", "true").lower() == "true"

# ============= 模型适配层 =============

from openai import AsyncOpenAI

class AIProvider:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.default_provider = os.getenv("AI_PROVIDER", "openai").lower()

    def get_client(self, provider: str) -> AsyncOpenAI:
        """根据供应商获取对应的 SDK 客户端 (强制禁用代理以解决 SSL 错误)"""
        # 创建一个干净的 http_client
        http_client = httpx.AsyncClient(
            timeout=60.0,
            trust_env=False,  # 禁用系统代理
            verify=True       # 保持 SSL 验证
        )
        
        if provider == "deepseek":
            return AsyncOpenAI(
                api_key=self.deepseek_key,
                base_url=self.deepseek_base_url,
                http_client=http_client
            )
        else:
            return AsyncOpenAI(
                api_key=self.openai_key,
                http_client=http_client
            )

    async def chat(self, system_prompt: str, user_prompt: str, provider: str = None) -> Dict:
        """使用 OpenAI SDK 调用接口（兼容 DeepSeek）"""
        active_provider = provider or self.default_provider
        client = self.get_client(active_provider)
        model = self.deepseek_model if active_provider == "deepseek" else self.openai_model

        print(f"📡 SDK 调用开始 | Provider: {active_provider} | Model: {model}")
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            print(f"✅ AI 响应成功")
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"❌ AI 调用异常: {str(e)}")
            raise Exception(f"AI 服务不可用: {str(e)}")

ai_client = AIProvider()

# ============= 初始化知识图谱和向量检索服务 =============

kg_service = None
vector_service = None

if SERVICES_AVAILABLE:
    try:
        if ENABLE_KNOWLEDGE_GRAPH:
            kg_service = LightweightKnowledgeGraph(KG_PATH)
            print(f"✅ 知识图谱服务已启用: {kg_service.get_stats()}")
        else:
            print("ℹ️ 知识图谱服务已禁用")
        
        if ENABLE_VECTOR_SEARCH:
            vector_service = LightweightVectorSearch(VECTOR_DB_PATH)
            print(f"✅ 向量检索服务已启用: {vector_service.get_stats()}")
        else:
            print("ℹ️ 向量检索服务已禁用")
    except Exception as e:
        print(f"⚠️ 服务初始化失败: {e}")
        kg_service = None
        vector_service = None
else:
    print("ℹ️ 轻量级服务不可用,请安装依赖: pip install networkx faiss-cpu")

# ============= 数据库初始化 =============

def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # API 表 (增强版)
    cursor.execute('''CREATE TABLE IF NOT EXISTS apis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL,
        method TEXT NOT NULL,
        summary TEXT,
        description TEXT,
        base_url TEXT,
        parameters TEXT, -- JSON 存储
        request_body TEXT, -- JSON 存储
        project_id TEXT DEFAULT 'default-project',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 自动迁移旧库：增加缺失的列
    try:
        cursor.execute("ALTER TABLE apis ADD COLUMN base_url TEXT")
        cursor.execute("ALTER TABLE apis ADD COLUMN parameters TEXT")
        cursor.execute("ALTER TABLE apis ADD COLUMN request_body TEXT")
        cursor.execute("ALTER TABLE apis ADD COLUMN headers TEXT")  # 新增headers字段
    except:
        pass # 列已存在
    
    # 场景表
    cursor.execute('''CREATE TABLE IF NOT EXISTS scenarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        natural_language_input TEXT,
        project_id TEXT DEFAULT 'default-project',
        nlu_result TEXT,
        test_case_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 测试用例表 (步骤序列)
    cursor.execute('''CREATE TABLE IF NOT EXISTS test_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        steps TEXT, -- JSON 存储步骤
        project_id TEXT DEFAULT 'default-project',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 执行记录表
    cursor.execute('''CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_case_id INTEGER,
        status TEXT, -- success, fail, running
        results TEXT, -- JSON 存储各步详情
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 项目环境配置表
    cursor.execute('''CREATE TABLE IF NOT EXISTS project_environments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        env_name TEXT NOT NULL, -- 如 test, dev, prod
        base_url TEXT NOT NULL,
        is_default INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project_id, env_name)
    )''')
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库架构已就绪: {DB_PATH}")

init_database()

# ============= 向量生成辅助函数 =============

async def generate_embedding(text: str) -> Optional[np.ndarray]:
    """使用OpenAI Embedding API生成文本向量"""
    if not vector_service:
        return None
    
    try:
        client = ai_client.get_client(ai_client.default_provider)
        response = await client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        embedding = np.array(response.data[0].embedding, dtype=np.float32)
        return embedding
    except Exception as e:
        print(f"⚠️ 向量生成失败: {e}")
        return None

async def index_api_to_vector(api_id: str, api_info: dict):
    """将API信息向量化并索引"""
    if not vector_service:
        return
    
    try:
        # 构建API描述文本
        text_parts = [
            api_info.get('path', ''),
            api_info.get('method', ''),
            api_info.get('summary', ''),
            api_info.get('description', '')
        ]
        text = ' '.join([p for p in text_parts if p])
        
        # 生成向量
        embedding = await generate_embedding(text)
        if embedding is not None:
            vector_service.add_vector(api_id, embedding, api_info)
            print(f"📊 API已向量化: {api_info.get('path')}")
    except Exception as e:
        print(f"⚠️ API向量化失败: {e}")

def add_api_to_kg(api_id: str, api_info: dict):
    """将API添加到知识图谱"""
    if not kg_service:
        return
    
    try:
        kg_service.add_api(
            api_id,
            path=api_info.get('path'),
            method=api_info.get('method'),
            name=api_info.get('summary') or api_info.get('path'),
            project_id=api_info.get('project_id')
        )
    except Exception as e:
        print(f"⚠️ 添加到知识图谱失败: {e}")

# ============= 核心业务路由 =============

# --- 场景与用例生成 ---

class ScenarioCreateRequest(BaseModel):
    natural_language_input: str
    project_id: str = "default-project"

@app.post("/api/v1/scenarios")
async def create_scenario(req: ScenarioCreateRequest):
    """场景理解并搜索 API"""
    try:
        print(f"🔍 收到场景创建请求: {req.natural_language_input}")
        # 1. AI 理解意图
        system_prompt = "你是一个接口测试专家。请解析用户描述的测试场景，提取意图、涉及实体和动作序列。以 JSON 格式返回：{intent, entities, actions, expected_results}"
        nlu_result = await ai_client.chat(system_prompt, req.natural_language_input)
        print(f"✅ AI 理解完成: {nlu_result.get('intent')}")
        
        # 2. 保存场景
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scenarios (name, natural_language_input, nlu_result, project_id) VALUES (?, ?, ?, ?)",
            (nlu_result.get("intent", "未命名场景"), req.natural_language_input, json.dumps(nlu_result), req.project_id)
        )
        scenario_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"id": scenario_id, "name": nlu_result.get("intent"), "description": req.natural_language_input}
    except Exception as e:
        print(f"❌ 场景创建失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: int):
    """删除场景及其关联的测试用例"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取关联的 test_case_id
        cursor.execute("SELECT test_case_id FROM scenarios WHERE id = ?", (scenario_id,))
        row = cursor.fetchone()
        
        # 删除场景
        cursor.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
        
        # 如果有测试用例，也一并删除
        if row and row[0]:
            cursor.execute("DELETE FROM test_cases WHERE id = ?", (row[0],))
            
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 环境配置管理 ---

class EnvironmentBase(BaseModel):
    env_name: str
    base_url: str
    is_default: Optional[bool] = False

@app.get("/api/v1/projects/{project_id}/environments")
async def list_environments(project_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_environments WHERE project_id = ?", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/v1/projects/{project_id}/environments")
async def save_environment(project_id: str, env: EnvironmentBase):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # 如果标记为默认，先取消该项目其他默认
        if env.is_default:
            cursor.execute("UPDATE project_environments SET is_default = 0 WHERE project_id = ?", (project_id,))
            
        cursor.execute("""
            INSERT INTO project_environments (project_id, env_name, base_url, is_default)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(project_id, env_name) DO UPDATE SET
                base_url = excluded.base_url,
                is_default = excluded.is_default
        """, (project_id, env.env_name, env.base_url, 1 if env.is_default else 0))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
    return {"success": True}

@app.delete("/api/v1/projects/{project_id}/environments/{env_name}")
async def delete_environment(project_id: str, env_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_environments WHERE project_id = ? AND env_name = ?", (project_id, env_name))
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/api/v1/scenarios")
async def list_scenarios():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, t.steps as test_case_steps 
        FROM scenarios s 
        LEFT JOIN test_cases t ON s.test_case_id = t.id 
        ORDER BY s.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/v1/scenarios/{scenario_id}/generate-case")
async def generate_case(scenario_id: int):
    """从海量 API 中检索并智能编排用例链"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 获取场景信息
        cursor.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,))
        scenario = cursor.fetchone()
        if not scenario: raise HTTPException(status_code=404, detail="场景不存在")
        
        # 2. RAG: 简易语义检索 (包含完整参数和请求体以供 AI 精准识别)
        cursor.execute("""
            SELECT path, method, summary, description, base_url, parameters, request_body, headers 
            FROM apis 
            WHERE project_id = ?
        """, (scenario["project_id"],))
        rows_apis = cursor.fetchall()
        all_apis = [dict(row) for row in rows_apis]
        
        # 3. AI 编排
        system_prompt = """你是一个高级接口自动化专家。
        任务：根据给出的【业务意图】和【可用 API 列表】，自动识别出正确的调用链，并以 JSON 格式返回。
        要求：
        1. 识别参数依赖（如 A 接口返回的 id 是 B 接口的输入）。
        2. 生成完整的测试数据：
           - `params` 必须包含该 API 定义中 `request_body` 的所有字段。
           - 严禁返回空对象或仅包含映射字段。
           - 使用合理且真实的测试数据（如果是查询，使用典型值；如果是创建，使用随机但合理的姓名/手机号等）。
        3. **参数映射 (param_mappings) - 必须生成!**：
           - **每个步骤都必须包含 param_mappings 字段**(即使为空数组 [])
           - 识别参数依赖: 如果后续步骤需要前序步骤的返回值,必须配置映射
           - 即使字段值将从前序步骤提取，也必须在 `params` 中保留该字段，并填充占位符数据。
           - 映射关系必须准确指向前序步骤的 `from_field` 和当前步骤的 `to_field`。
           - 常见映射场景: 登录返回token → 后续请求使用token, 创建订单返回orderId → 查询订单使用orderId
        4. **Headers 继承 (重要!)**：
           - 如果 API 定义中有 `headers` 字段,必须在生成的步骤中包含相同的 headers。
           - 特别是 `Content-Type` 头,必须严格按照 API 定义设置。
        5. **自动生成逻辑断言 (关键!)**：
           - 类型 (type) 必须是以下之一：'status_code', 'field_value'。
           - **必需字段规则**：
             * 'status_code': 只需 type 和 expected
           - **字段路径格式 (field)**：
             * 使用点记号表示嵌套路径，如 "data.user.id"
             * 数组索引用数字，如 "data.list.0.name"
             * 常见响应结构: {"code": 0, "message": "success", "data": {...}}
           - **断言示例**：
             * 状态码: {"type": "status_code", "expected": 200, "description": "HTTP状态码应为200"}
             * 业务码: {"type": "field_value", "field": "code", "expected": 0, "description": "业务状态码应为0"}
             * 消息验证: {"type": "field_value", "field": "message", "expected": "success", "description": "消息应为success"}
            - **断言准确性要求 (重要!)**：
              * 断言必须符合API的实际功能,不要臆测不存在的字段
              * 例如: 点歌接口验证"点歌成功"而非"订单ID",搜索接口验证"歌曲列表"而非"订单列表"
              * 优先验证通用字段(code/message),避免验证不确定的业务字段
              * 如果不确定响应结构,只验证HTTP状态码和业务状态码
            - **每个步骤建议2-3个断言**: HTTP状态码(必需) + 业务状态码(推荐) + 消息验证(可选)
        请务必返回合法的 JSON 对象。
        格式示例：
        { 
          "scenario_name": "用户登录并查询信息", 
          "steps": [
            { 
              "step_order": 1, 
              "api_path": "/user/login", 
              "api_method": "POST", 
              "description": "用户登录", 
              "params": {"username": "test_user", "password": "123456"}, 
              "headers": {"Content-Type": "application/json"}, 
              "assertions": [
                {"type": "status_code", "expected": 200, "description": "HTTP状态码应为200"},
                {"type": "field_value", "field": "code", "expected": 0, "description": "业务状态码应为0"}
              ], 
              "param_mappings": [] 
            }
          ] 
        }"""
        
        
        user_prompt = f"意图: {scenario['nlu_result']}\n可用 API: {json.dumps(all_apis[:50])}" # 限制上下文
        case_result = await ai_client.chat(system_prompt, user_prompt)
        
        # 3.5 验证并修复断言配置
        def validate_and_fix_assertions(steps):
            """验证并修复断言配置,确保包含必需字段"""
            fixed_count = 0
            for step in steps:
                assertions = step.get("assertions", [])
                fixed_assertions = []
                
                for assertion in assertions:
                    assertion_type = assertion.get("type", "")
                    description = assertion.get("description", "").lower()
                    
                    # 检查必需字段
                    if assertion_type in ["field_exists", "field_value", "json_path"]:
                        if not assertion.get("field"):
                            print(f"⚠️ 警告: 步骤 {step.get('step_order')} 的 {assertion_type} 断言缺少 field 字段")
                            print(f"   断言配置: {assertion}")
                            print(f"   描述: {description}")
                            
                            field = None
                            
                            # 方法1: 根据期望值推测
                            if assertion_type == "field_value":
                                expected = assertion.get("expected") or assertion.get("expected_value")
                                if expected == 0 or expected == "0":
                                    field = "code"
                                    print(f"   ✅ 根据期望值推测: field='code'")
                                elif expected in ["success", "成功", "ok", "OK"]:
                                    field = "message"
                                    print(f"   ✅ 根据期望值推测: field='message'")
                            
                            # 方法2: 根据描述推测
                            if not field and description:
                                if "code" in description or "状态码" in description or "业务码" in description:
                                    field = "code"
                                    print(f"   ✅ 根据描述推测: field='code'")
                                elif "message" in description or "消息" in description or "msg" in description:
                                    field = "message"
                                    print(f"   ✅ 根据描述推测: field='message'")
                                elif "list" in description or "列表" in description or "数组" in description:
                                    field = "data.list"
                                    print(f"   ✅ 根据描述推测: field='data.list'")
                                elif "data" in description or "数据" in description:
                                    field = "data"
                                    print(f"   ✅ 根据描述推测: field='data'")
                                elif "token" in description or "令牌" in description:
                                    field = "data.token"
                                    print(f"   ✅ 根据描述推测: field='data.token'")
                            
                            # 方法3: 使用默认值
                            if not field:
                                field = "data"
                                print(f"   ⚠️ 无法推测,使用默认值: field='data'")
                            
                            assertion["field"] = field
                            fixed_count += 1
                    
                    # 确保expected字段存在
                    if "expected" not in assertion and "expected_value" in assertion:
                        assertion["expected"] = assertion["expected_value"]
                    
                    fixed_assertions.append(assertion)
                
                step["assertions"] = fixed_assertions
            
            if fixed_count > 0:
                print(f"📋 断言验证完成: 共修复 {fixed_count} 个不完整的断言配置")
            
            return steps
        
        # 验证并修复生成的步骤
        if "steps" in case_result:
            case_result["steps"] = validate_and_fix_assertions(case_result["steps"])
        
        # 4. 保存测试用例
        cursor.execute(
            "INSERT INTO test_cases (name, steps, project_id) VALUES (?, ?, ?)",
            (case_result.get("scenario_name"), json.dumps(case_result.get("steps")), scenario["project_id"])
        )
        case_id = cursor.lastrowid
        
        # 关联场景
        cursor.execute("UPDATE scenarios SET test_case_id = ? WHERE id = ?", (case_id, scenario_id))
        
        conn.commit()
        conn.close()
        # 兼容前端字段名
        case_result["name"] = case_result.get("scenario_name")
        return case_result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/test_cases/{test_case_id}/steps/{step_order}")
async def delete_test_step(test_case_id: int, step_order: int):
    """从测试用例中删除指定步骤并重新编排序号"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 获取当前步骤
        cursor.execute("SELECT steps FROM test_cases WHERE id = ?", (test_case_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="测试用例不存在")
        
        steps = json.loads(row["steps"])
        
        # 2. 过滤掉目标步骤
        new_steps = [s for s in steps if s.get("step_order") != step_order]
        
        if len(new_steps) == len(steps):
            conn.close()
            raise HTTPException(status_code=404, detail="指定步骤不存在")
            
        # 3. 重新编排序号
        for i, step in enumerate(new_steps, 1):
            step["step_order"] = i
            
        # 4. 写回数据库
        cursor.execute("UPDATE test_cases SET steps = ? WHERE id = ?", (json.dumps(new_steps), test_case_id))
        conn.commit()
        conn.close()
        
        return {"success": True, "message": f"已删除第 {step_order} 步，剩余 {len(new_steps)} 步", "steps": new_steps}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 执行引擎 ---

class ExecutionRequest(BaseModel):
    test_case_id: Optional[int] = None  # 可选,用于完整场景执行
    environment: str = "test"
    base_url: str = "http://localhost:8000"
    steps: Optional[List[Dict]] = None  # 可选,用于单步执行

class APICreateRequest(BaseModel):
    name: str
    method: str
    path: str
    description: Optional[str] = ""
    project_id: str = "default-project"
    base_url: Optional[str] = ""
    headers: Optional[Dict] = {}
    request_body: Optional[Dict] = {}
    parameters: Optional[List] = []

class CurlParseRequest(BaseModel):
    curl: str

def parse_curl_command(curl_command: str) -> Dict[str, Any]:
    import shlex
    try:
        # 预处理：去掉换行符和反斜杠连接
        curl_command = curl_command.replace('\\\n', ' ').replace('\\\r\n', ' ').strip()
        tokens = shlex.split(curl_command)
    except Exception as e:
        raise ValueError(f"cURL 解析失败 (shlex): {str(e)}")

    result = {
        "method": "GET",
        "url": "",
        "path": "",
        "base_url": "",
        "headers": {},
        "body": {},
        "parameters": [] # 新增：解析查询参数
    }

    i = 0
    is_get_mode = False
    while i < len(tokens):
        token = tokens[i]
        if token == "curl":
            i += 1
            continue
        if token in ["-X", "--request"]:
            if i + 1 < len(tokens):
                result["method"] = tokens[i+1].upper()
                i += 2
                continue
        if token in ["-G", "--get"]:
            is_get_mode = True
            i += 1
            continue
        if token in ["-u", "--user"]:
            if i + 1 < len(tokens):
                import base64
                auth_val = base64.b64encode(tokens[i+1].encode()).decode()
                result["headers"]["Authorization"] = f"Basic {auth_val}"
                i += 2
                continue
        if token in ["-H", "--header"]:
            if i + 1 < len(tokens):
                header_str = tokens[i+1]
                if ":" in header_str:
                    key, val = header_str.split(":", 1)
                    # 某些 header 不需要保留在定义中（如缓存头），但在解析阶段我们先保留，由执行引擎清洗
                    result["headers"][key.strip()] = val.strip()
                i += 2
                continue
        if token in ["-d", "--data", "--data-raw", "--data-binary", "--data-urlencoded", "--data-urlencode"]:
            if i + 1 < len(tokens):
                body_str = tokens[i + 1]
                if result["method"] == "GET" and not is_get_mode:
                    result["method"] = "POST"
                
                # 尝试解析 JSON
                try:
                    parsed_body = json.loads(body_str)
                    if isinstance(result["body"], dict):
                        result["body"].update(parsed_body)
                    else:
                        result["body"] = parsed_body
                except:
                    # 如果不是 JSON，尝试按 key=value 解析
                    if "=" in body_str:
                        params = urllib.parse.parse_qs(body_str)
                        body_params = {k: v[0] for k, v in params.items()}
                        if isinstance(result["body"], dict):
                            result["body"].update(body_params)
                        else:
                            result["body"] = body_params
                    else:
                        result["body"] = body_str
                i += 2
                continue
        if token in ["-F", "--form"]:
            if i + 1 < len(tokens):
                form_str = tokens[i + 1]
                if "=" in form_str:
                    parts = form_str.split("=", 1)
                    k, v = parts[0], parts[1]
                    if isinstance(result["body"], dict):
                        result["body"][k] = v
                result["method"] = "POST"
                i += 2
                continue
        if not token.startswith("-") and not result["url"]:
            full_url = token
            # 兼容不带 http 的写法
            if not re.match(r'https?://', full_url):
                full_url = "http://" + full_url
            
            result["url"] = full_url
            try:
                parsed = urllib.parse.urlparse(full_url)
                result["base_url"] = f"{parsed.scheme}://{parsed.netloc}"
                result["path"] = parsed.path
                # 解析 URL 中的查询参数
                if parsed.query:
                    qs = urllib.parse.parse_qs(parsed.query)
                    for k, v in qs.items():
                        result["parameters"].append({
                            "name": k,
                            "value": v[0],
                            "in": "query",
                            "required": False
                        })
            except:
                result["path"] = full_url
            i += 1
            continue
        i += 1
    
    # 如果是 GET 模式，将 body 合并到 parameters
    if is_get_mode and isinstance(result["body"], dict):
        for k, v in result["body"].items():
            result["parameters"].append({
                "name": k,
                "value": str(v),
                "in": "query",
                "required": False
            })
        result["body"] = {}
        result["method"] = "GET"

    return result

@app.post("/api/v1/executions")
async def execute_case(req: ExecutionRequest):
    """链式执行引擎：支持变量动态映射和 HTTP 发送"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # 1. 确定运行时的步骤数据
        case_info = None
        if req.steps:
            steps = req.steps
        else:
            if not req.test_case_id:
                raise HTTPException(status_code=400, detail="必须提供 test_case_id 或 steps")
            cursor.execute("SELECT * FROM test_cases WHERE id = ?", (req.test_case_id,))
            case_info = cursor.fetchone()
            if not case_info: 
                raise HTTPException(status_code=404, detail="用例不存在")
            steps = json.loads(case_info["steps"])
        
        context = {} # 存储运行时变量
        step_results = []
        
        async with httpx.AsyncClient(verify=False, timeout=30.0, follow_redirects=True) as client:
            for step in steps:
                step_order = step.get("step_order", 0)
                start_time = datetime.now()
                # 确定 Base URL: 环境选择器优先于接口定义的 base_url
                current_base_url = req.base_url.strip() if req.base_url else ""
                
                # 如果没有选环境，或者环境是默认的 localhost，则尝试取接口定义里的
                if not current_base_url or "localhost:8000" in current_base_url:
                    if step.get("base_url"):
                        current_base_url = step.get("base_url").strip()
                
                # 如果最终还是空的，给个默认
                if not current_base_url:
                    current_base_url = "http://localhost:8000"

                step_data = {
                    "step_order": step_order,
                    "url": "",
                    "method": step.get("api_method", "GET").upper(),
                    "request_data": step.get("params", {}),
                    "success": False,
                    "status_code": "Error",
                    "extractions": []
                }
                
                try:
                    # 变量替换与参数准备
                    api_path = step.get('api_path', '').strip()
                    
                    # 路径清洗：如果 api_path 里不小心带了域名（某些 cURL 导入或手动输入的误操作），尝试剥离它
                    if re.match(r'https?://', api_path):
                        parsed_path = urllib.parse.urlparse(api_path)
                        api_path = parsed_path.path
                        if parsed_path.query and not step.get("url_params"):
                            # 如果路径里有 query 且没定义参数，则保留（通过 safe_path 处理）
                            api_path = f"{parsed_path.path}?{parsed_path.query}"

                    normalized_api_path = api_path.split('?')[0].strip("/")
                    
                    # 确保 path 不带开头的斜杠，方便拼接
                    clean_path = api_path.lstrip('/')
                    safe_path = urllib.parse.quote(clean_path, safe="/?=&")
                    url = f"{current_base_url.rstrip('/')}/{safe_path}"
                    
                    params = step.get("params", {}).copy()
                    method = step_data["method"]
                    
                    # --- 参数自动补全逻辑 ---
                    # 如果 params 字段较少（可能是 AI 生成场景时丢失了字段），尝试从数据库拉取完整定义
                    if method.upper() == "POST" and len(params) < 5:
                        try:
                            proj_id = case_info["project_id"] if case_info else step.get("project_id", "")
                            cursor.execute("""
                                SELECT request_body FROM apis 
                                WHERE (path = ? OR path = ?) AND method = ? AND project_id = ?
                                LIMIT 1
                            """, (normalized_api_path, f"/{normalized_api_path}", method, proj_id))
                            api_row = cursor.fetchone()
                            if api_row and api_row["request_body"]:
                                rb_def = json.loads(api_row["request_body"])
                                if "content" in rb_def:
                                    for ct, content in rb_def["content"].items():
                                        props = content.get("schema", {}).get("properties", {})
                                        if props:
                                            full_params = {}
                                            for f_name, f_def in props.items():
                                                full_params[f_name] = f_def.get("example") if f_def.get("example") is not None else f_def.get("default", "")
                                            full_params.update(params) # 覆盖提取的值
                                            params = full_params
                                            print(f"📋 步骤 {step_order}: 已从数据库补全完整请求参数 (原始字段数: {len(step.get('params', {}))}, 补全后: {len(params)})")
                                            break
                        except Exception as e:
                            print(f"⚠️ 补齐参数失败: {e}")
                    # ----------------------

                    # 智能路径搜索与提取工具函数 (注入到 step 作用域)
                    def find_field_paths(data, target_field, current_path="", max_depth=5):
                        if max_depth <= 0: return []
                        paths = []
                        if isinstance(data, dict):
                            if target_field in data:
                                path = f"{current_path}.{target_field}" if current_path else target_field
                                paths.append(path)
                            for k, v in data.items():
                                new_path = f"{current_path}.{k}" if current_path else k
                                paths.extend(find_field_paths(v, target_field, new_path, max_depth - 1))
                        elif isinstance(data, list) and len(data) > 0:
                            new_path = f"{current_path}[0]" if current_path else "[0]"
                            paths.extend(find_field_paths(data[0], target_field, new_path, max_depth - 1))
                        return paths

                    def try_extract_with_path(data, path):
                        try:
                            curr = data
                            for part in path.replace('[', '.[').split('.'):
                                if not part: continue
                                if part.startswith('[') and part.endswith(']'):
                                    curr = curr[int(part[1:-1])]
                                elif part.isdigit():
                                    curr = curr[int(part)] if isinstance(curr, list) else curr.get(part)
                                else:
                                    curr = curr.get(part)
                                if curr is None: break
                            return curr
                        except: return None
                    
                    # 处理 URL 参数 (query 和 path)
                    query_params = {}
                    url_params_list = step.get("url_params", [])
                    print(f"   [DEBUG] 原始 params: {json.dumps(params, ensure_ascii=False)[:200]}")
                    print(f"   [DEBUG] 原始 url_params: {json.dumps(url_params_list, ensure_ascii=False)[:200]}")
                    if isinstance(url_params_list, list):
                        for p in url_params_list:
                            p_name = p.get("name")
                            p_in = p.get("in", "query")  # 默认为 query,防止 AI 生成时遗漏
                            p_val = p.get("value")
                            if p_val is None:
                                # 尝试获取默认值
                                schema = p.get("schema", {})
                                p_val = schema.get("default") if isinstance(schema, dict) else None
                            
                            if p_val is not None and p_name:
                                if p_in == "path":
                                    # 替换路径参数 {name} 或 :name
                                    url = url.replace(f"{{{p_name}}}", str(p_val))
                                    url = url.replace(f":{p_name}", str(p_val))
                                else:
                                    # 其他所有情况(query、空值、未定义等)都作为查询参数
                                    query_params[p_name] = p_val
                    elif isinstance(url_params_list, dict):
                        # 如果是字典,直接作为 query 参数
                        query_params.update(url_params_list)
                    print(f"   [DEBUG] 处理后 query_params: {json.dumps(query_params, ensure_ascii=False)}")

                    step_data["url"] = url
                    
                    # 处理headers (深度清洗系统干扰项)
                    headers = step.get("headers", {}).copy()
                    
                    # 核心清洗逻辑：剔除可能引发 304, 403, 411 或损坏响应的 Header
                    black_list = [
                        'host',                    # 必须剔除，否则跨环境执行会 403 (Host 不匹配)
                        'if-none-match',           # 必须剔除，否则会报 304 Not Modified
                        'if-modified-since',       # 必须剔除，同上
                        'content-length',          # 必须剔除，防止 Body 修改后长度校验失败
                        'connection',              # 交给 httpx
                        'accept-encoding',         # 交给 httpx (支持自动解压)
                        # 'content-type',          # [FIX] 不再剔除，允许表单等非 JSON 格式通过
                    ]
                    
                    # 转换为小写进行匹配并剔除
                    headers = {k: v for k, v in headers.items() if k.lower() not in black_list}
                    
                    # 强制注入非缓存头，确保获取实时数据
                    headers["Cache-Control"] = "no-cache"
                    headers["Pragma"] = "no-cache"
                    
                    # 处理参数映射(包括 headers中的变量替换)并记录提取过程
                    extractions = []
                    for mapping in step.get("param_mappings", []):
                        from_step_idx = mapping.get("from_step")
                        from_field = mapping.get("from_field")
                        to_field = mapping.get("to_field")
                        
                        # 初始化提取记录
                        extraction = {
                            "from_step": from_step_idx,
                            "from_field": from_field,
                            "to_field": to_field,
                            "extracted_value": None,
                            "success": False,
                            "error_msg": ""
                        }
                        
                        if from_step_idx is None or to_field is None:
                            extraction["error_msg"] = "参数映射配置不完整"
                            extractions.append(extraction)
                            continue
                        
                        from_data = context.get(f"step_{from_step_idx}", {}).get("response")
                        field_val = None
                        if from_data:
                            # 1. 尝试原始路径提取
                            field_val = try_extract_with_path(from_data, from_field)
                            
                            # 2. 如果失败，启动智能修复
                            if field_val is None:
                                print(f"🔧 智能修复 - 步骤 {step_order}: 路径 '{from_field}' 提取失败，开始智能搜索...")
                                target_node = from_field.split('.')[-1].replace('[', '').replace(']', '')
                                possible_paths = find_field_paths(from_data, target_node)
                                
                                # 评估并选择最优路径 (深度优先, 原始类型优先)
                                candidates = []
                                for p in possible_paths:
                                    v = try_extract_with_path(from_data, p)
                                    if v is not None:
                                        candidates.append({
                                            'path': p, 'val': v, 
                                            'depth': p.count('.') + p.count('['),
                                            'is_prim': isinstance(v, (str, int, float, bool))
                                        })
                                candidates.sort(key=lambda x: (not x['is_prim'], -x['depth']))
                                
                                if candidates:
                                    best = candidates[0]
                                    field_val = best['val']
                                    extraction["fixed_path"] = best['path']
                                    extraction["auto_fixed"] = True
                                    print(f"✅ 智能修复成功: 使用了路径 '{best['path']}'，提取到值: {field_val}")
                                else:
                                    extraction["error_msg"] = f"未能在响应中找到目标字段 '{target_node}'"
                                    print(f"❌ 智能修复失败: 无法找到字段 '{target_node}'")
                            
                            if field_val is not None:
                                extraction["extracted_value"] = field_val
                                extraction["success"] = True
                                # 填充到请求参数或 Headers
                                if to_field.startswith("headers."):
                                    headers[to_field.replace("headers.", "")] = field_val
                                elif to_field.startswith("params."):
                                    # 去掉 params. 前缀,直接填充到 params 字典
                                    params[to_field.replace("params.", "")] = field_val
                                else:
                                    params[to_field] = field_val
                        else:
                            extraction["error_msg"] = f"前序步骤 {from_step_idx} 的响应不存在"
                        
                        extractions.append(extraction)
                    
                    step_data["extractions"] = extractions
                    
                    # 处理headers中的变量引用 ${stepX.field}
                    for key, value in list(headers.items()):
                        if isinstance(value, str) and "${" in value:
                            matches = re.findall(r'\$\{step(\d+)\.(.+?)\}', value)
                            for step_idx, field_path in matches:
                                step_data_ref = context.get(f"step_{step_idx}", {}).get("response", {})
                                field_value = step_data_ref
                                for part in field_path.split('.'):
                                    if isinstance(field_value, dict):
                                        field_value = field_value.get(part)
                                    else:
                                        field_value = None
                                        break
                                if field_value:
                                    value = value.replace(f"${{step{step_idx}.{field_path}}}", str(field_value))
                            headers[key] = value

                    step_data["request_data"] = params
                    
                    # 2. 发送请求
                    print(f"🚀 执行步骤 {step_order}: {method} {url}")
                    print(f"   [DEBUG] Content-Type: {next((v for k, v in headers.items() if k.lower() == 'content-type'), 'None')}")
                    if query_params:
                        print(f"   查询参数: {json.dumps(query_params, ensure_ascii=False)}")
                    
                    # 智能判断发送模式 (JSON, Form, Data)
                    ct = next((v for k, v in headers.items() if k.lower() == 'content-type'), "").lower()
                    req_kwargs = {
                        "method": method,
                        "url": url,
                        "headers": headers,
                        "timeout": 30.0,
                        "follow_redirects": True,
                        # 修复: GET 请求合并 query 和 body 参数; 非 GET 请求只传 query 参数到 URL
                        "params": {**query_params, **params} if method == "GET" else query_params
                    }
                    print(f"   [DEBUG] 最终传给 httpx 的 params: {json.dumps(req_kwargs['params'], ensure_ascii=False)}")

                    if method != "GET":
                        if "application/x-www-form-urlencoded" in ct or "multipart/form-data" in ct:
                            # 表单模式
                            req_kwargs["data"] = params
                            print(f"   请求体 (Form): {json.dumps(params, ensure_ascii=False)[:200]}")
                        elif isinstance(params, (dict, list)):
                            # JSON 模式 (默认)
                            req_kwargs["json"] = params
                            print(f"   请求体 (JSON): {json.dumps(params, ensure_ascii=False)[:200]}")
                        else:
                            # 原始文本/字节
                            req_kwargs["content"] = str(params)
                            print(f"   请求体 (RAW): {str(params)[:200]}")
                    
                    try:
                        res = await client.request(**req_kwargs)
                        duration = (datetime.now() - start_time).total_seconds()
                        
                        print(f"   ✅ 响应: {res.status_code} ({duration:.2f}s)")
                        
                        # 3. 记录结果
                        res_content = res.text
                        try:
                            res_json = res.json()
                            res_content = res_json
                        except:
                            pass
                        
                        # 4. 执行断言验证
                        assertions_config = step.get("assertions", [])
                        assertion_results = []
                        
                        # 如果AI没有生成断言,添加默认断言
                        if not assertions_config:
                            assertions_config = [
                                {
                                    "type": "status_code",
                                    "operator": "equals",
                                    "expected_value": 200,
                                    "description": "状态码应为200"
                                },
                                {
                                    "type": "response_time",
                                    "operator": "less_than",
                                    "expected_value": 1000,
                                    "description": "响应时间应小于1秒"
                                }
                            ]
                        # 3. 执行断言
                        assertion_results = []
                        for assertion in assertions_config: # Changed from step.get("assertions", []) to assertions_config
                            # 动态修复断言配置(执行时修复,确保旧场景也能正常工作)
                            assertion_type = assertion.get("type", "")
                            description = assertion.get("description", "").lower()
                            
                            # 如果断言需要field字段但缺失,自动修复
                            if assertion_type in ["field_exists", "field_value", "json_path"]:
                                if not assertion.get("field"):
                                    field = None
                                    
                                    # 方法1: 根据期望值推测
                                    if assertion_type == "field_value":
                                        expected_val = assertion.get("expected") or assertion.get("expected_value")
                                        if expected_val == 0 or expected_val == "0":
                                            field = "code"
                                        elif expected_val in ["success", "成功", "ok", "OK"]:
                                            field = "message"
                                    
                                    # 方法2: 根据描述推测
                                    if not field and description:
                                        if "code" in description or "状态码" in description or "业务码" in description:
                                            field = "code"
                                        elif "message" in description or "消息" in description or "msg" in description:
                                            field = "message"
                                        elif "list" in description or "列表" in description or "数组" in description:
                                            field = "data.list"
                                        elif "订单" in description or "id" in description:
                                            field = "data.id"
                                        elif "data" in description or "数据" in description:
                                            field = "data"
                                        elif "token" in description or "令牌" in description:
                                            field = "data.token"
                                    
                                    # 方法3: 默认值
                                    if not field:
                                        field = "data"
                                    
                                    assertion["field"] = field
                                    print(f"   ⚙️ 运行时修复断言: {description} → field='{field}'")
                            
                            # ---------------------------------------------------------
                            # [新增] 智能字段映射 (Smart Field Mapping)
                            # 解决 API 字段不统一问题 (如 code vs errcode, message vs errmsg)
                            # ---------------------------------------------------------
                            current_field = assertion.get("field", "")
                            if isinstance(res_content, dict) and "." not in current_field:
                                # 只有当原字段在响应中不存在时才尝试映射
                                if current_field not in res_content:
                                    mapping = {
                                        "code": ["errcode", "RetCode", "status", "ret", "error_code"],
                                        "message": ["errmsg", "msg", "info", "error", "message", "desc"],
                                        "data": ["result", "content", "body", "list"]
                                    }
                                    
                                    if current_field in mapping:
                                        for alt in mapping[current_field]:
                                            if alt in res_content:
                                                assertion["field"] = alt
                                                print(f"   🔄 字段自动映射: {current_field} -> {alt}")
                                                break
                            # ---------------------------------------------------------
                            
                            # 支持expected和expected_value两种字段名
                            expected = assertion.get("expected") or assertion.get("expected_value")
                            description = assertion.get("description", "")
                            
                            result = {
                                "type": assertion_type,
                                "description": description,
                                "expected": expected,
                                "actual": None,
                                "passed": False
                            }
                            
                            try:
                                if assertion_type == "status_code":
                                    result["field"] = "HTTP状态码"
                                    result["operator"] = "等于"
                                    result["actual"] = res.status_code
                                    try:
                                        result["passed"] = (int(res.status_code) == int(expected))
                                    except:
                                        result["passed"] = (str(res.status_code) == str(expected))
                                
                                elif assertion_type == "response_time":
                                    result["field"] = "响应时间"
                                    result["operator"] = "小于"
                                    actual_ms = int(duration * 1000)
                                    result["actual"] = f"{actual_ms}ms"
                                    try:
                                        result["passed"] = (actual_ms <= int(expected))
                                    except:
                                        result["passed"] = False
                                
                                elif assertion_type == "field_exists":
                                    field = assertion.get("field", "")
                                    if isinstance(res_content, dict):
                                        # 支持嵌套字段,如 "data.user.id"
                                        field_exists = True
                                        current = res_content
                                        for part in field.split("."):
                                            if isinstance(current, dict) and part in current:
                                                current = current[part]
                                            else:
                                                field_exists = False
                                                break
                                        result["actual"] = field_exists
                                        result["passed"] = field_exists
                                    else:
                                        result["actual"] = False
                                        result["passed"] = False
                                
                                elif assertion_type in ["field_value", "json_path"]:
                                    # 支持 field, expression, path, json_path 等字段名
                                    field_raw = assertion.get("field") or assertion.get("expression") or assertion.get("path") or assertion.get("json_path", "")
                                    # 清理 JSONPath 前缀
                                    field = str(field_raw).strip()
                                    if field.startswith("$."): field = field[2:]
                                    elif field.startswith("$"): field = field[1:]
                                    
                                    if isinstance(res_content, dict):
                                        current = res_content
                                        parts = field.split(".")
                                        
                                        # 智能处理: 如果第一级是 'data' 但响应根部没有 'data'，尝试跳过它
                                        if parts and parts[0] == "data" and "data" not in current and len(parts) > 1:
                                            parts = parts[1:]
                                        
                                        for part in parts:
                                            # 处理函数如 length()
                                            if part.endswith("()"):
                                                func = part[:-2].lower()
                                                if func == "length":
                                                    current = len(current) if isinstance(current, (list, dict, str)) else 0
                                                    continue
                                            
                                            # 处理数组索引如 "data.list.0"
                                            if isinstance(current, list) and part.isdigit():
                                                idx = int(part)
                                                current = current[idx] if idx < len(current) else None
                                            elif isinstance(current, dict):
                                                # 尝试匹配原样 key
                                                if part in current:
                                                    current = current[part]
                                                # 尝试处理 songs vs song 这种单复数不一致情况 (简单的模糊匹配)
                                                elif part.endswith("s") and part[:-1] in current:
                                                    current = current[part[:-1]]
                                                else:
                                                    current = None
                                                    break
                                            else:
                                                current = None
                                                break
                                        
                                        result["actual"] = current
                                        
                                        # 如果没有提供 expected, 则退化为 field_exists 逻辑
                                        if expected is None:
                                            # 判定标准：不为 None 且（如果是列表则非空）
                                            result["passed"] = (current is not None and not (isinstance(current, list) and len(current) == 0))
                                            result["description"] = f"校验字段 {field_raw} 是否存在且不为空"
                                        else:
                                            # 统一转为字串比较，增强兼容性
                                            is_match = str(current) == str(expected)
                                            
                                            # [新增] 语义化宽松匹配 (针对 message 类字段)
                                            if not is_match and field in ["message", "msg", "errmsg", "error", "info", "desc"]:
                                                # 如果期望是 success 但实际是 "点歌成功" / "OK" 等
                                                expected_lower = str(expected).lower()
                                                current_str = str(current)
                                                
                                                if expected_lower in ["success", "ok"]:
                                                    if "成功" in current_str or "ok" in current_str.lower() or "success" in current_str.lower():
                                                        is_match = True
                                                        result["actual"] = f"{current_str} (语义匹配 Success)"
                                                
                                                # 如果实际值包含期望值 (如 "操作成功" 包含 "成功")
                                                elif str(expected) in current_str:
                                                    is_match = True
                                                    result["actual"] = f"{current_str} (包含期望值)"

                                            result["passed"] = is_match
                                    else:
                                        result["actual"] = None
                                        result["passed"] = False
                                
                                elif assertion_type == "response_contains":
                                    text = str(assertion.get("text", "") or expected or "")
                                    contains = text in str(res_content)
                                    result["actual"] = f"包含 '{text}'" if contains else "不包含"
                                    result["passed"] = contains
                                
                                else:
                                    # 未知或语义类型处理 (如 "登录成功")
                                    # 尝试 1: 在响应中查找相关关键字 (原逻辑)
                                    keywords = [assertion_type, description]
                                    matches = any(kw and kw in str(res_content) for kw in keywords)
                                    
                                    # 尝试 2: 语义化成功判定。如果断言涉及 "成功", "完成", "OK", "有效" 等
                                    success_keywords = ["成功", "完成", "OK", "有效", "success", "ok", "valid"]
                                    is_success_assertion = any(sk in assertion_type or sk in description for sk in success_keywords)
                                    
                                    if not matches and is_success_assertion:
                                        # 如果是成功类断言但没匹配到关键字，检查常见的成功标志
                                        if isinstance(res_content, dict):
                                            # 检查 code/status/success 等常见字段
                                            code = res_content.get("code")
                                            is_success_code = code in [0, 200, "0", "200"]
                                            is_success_bool = res_content.get("success") is True or res_content.get("status") in ["success", "ok"]
                                            
                                            if is_success_code or is_success_bool:
                                                matches = True
                                                result["actual"] = f"匹配业务成功标志 (code={code})" if is_success_code else "匹配业务成功状态"
                                    
                                    # 只有在 actual 还没被赋值(即未知断言类型)时，才使用模糊匹配的结果
                                    if result.get("actual") is None and assertion_type not in ["status_code", "field_value", "json_path", "field_exists", "response_contains"]:
                                        result["actual"] = "部分匹配" if matches else "无匹配"
                                        result["passed"] = matches if keywords else True
                                    if not matches:
                                        print(f"   ⚠️ 未知断言类型: {assertion_type}, 匹配失败")
                                
                            except Exception as e:
                                result["error"] = str(e)
                                result["passed"] = False
                            
                            assertion_results.append(result)
                        
                        # 判断步骤是否成功(所有断言都通过)
                        all_assertions_passed = all(a["passed"] for a in assertion_results)
                            
                        step_data.update({
                            "status_code": res.status_code,
                            "duration": duration,
                            "response": res_content,
                            "response_headers": dict(res.headers),  # 新增:响应头
                            "assertions": assertion_results,
                            "success": res.status_code < 400 and all_assertions_passed
                        })
                        context[f"step_{step_order}"] = step_data
                        step_results.append(step_data)
                        
                    except httpx.TimeoutException as e:
                        error_msg = f"请求超时: {repr(e)}"
                        print(f"   ❌ {error_msg}")
                        step_data["error"] = error_msg
                        step_results.append(step_data)
                    except httpx.ConnectError as e:
                        # ConnectError的str()可能为空,使用repr()获取详细信息
                        error_detail = str(e) if str(e) else repr(e)
                        error_msg = f"连接失败: {error_detail}"
                        print(f"   ❌ {error_msg}")
                        step_data["error"] = error_msg
                        step_results.append(step_data)
                    except httpx.HTTPStatusError as e:
                        error_msg = f"HTTP错误 {e.response.status_code}: {str(e)}"
                        print(f"   ❌ {error_msg}")
                        step_data["error"] = error_msg
                        step_results.append(step_data)
                    except Exception as e:
                        error_detail = str(e) if str(e) else repr(e)
                        error_msg = f"请求异常: {type(e).__name__}: {error_detail}"
                        print(f"   ❌ {error_msg}")
                        import traceback
                        traceback.print_exc()

                        step_data["error"] = error_msg
                        step_results.append(step_data)
                except Exception as e:
                    error_msg = f"步骤准备异常: {type(e).__name__}: {str(e)}"
                    print(f"❌ 步骤 {step_order} 运行异常: {error_msg}")
                    step_data["error"] = error_msg
                    # 即使出错也返回已准备好的 URL 和 Method，方便前端展示
                    step_results.append(step_data)

        # 4. 保存执行记录并判定总状态
        final_status = "success" if all(s.get("success", False) for s in step_results) else "failed"
        
        # 只有完整场景执行才保存到数据库
        if req.test_case_id:
            cursor.execute(
                "INSERT INTO executions (test_case_id, status, results) VALUES (?, ?, ?)",
                (req.test_case_id, final_status, json.dumps(step_results))
            )
            exec_id = cursor.lastrowid
            conn.commit()
        else:
            # 单步执行使用临时ID
            exec_id = 0
        
        return {"id": exec_id, "status": final_status, "results": step_results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# --- 导入与列表 (保持原有逻辑) ---

@app.get("/api/v1/projects")
async def list_projects():
    """获取系统中所有项目 ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT project_id FROM apis UNION SELECT DISTINCT project_id FROM scenarios")
    rows = cursor.fetchall()
    conn.close()
    return {"projects": [r[0] for r in rows if r[0]]}

@app.post("/api/v1/import/swagger")
async def import_swagger(project_id: str = Form("default-project"), source: str = Form(None), file: UploadFile = File(None)):
    try:
        swagger_data = None
        if source:
            async with httpx.AsyncClient() as client:
                res = await client.get(source)
                swagger_data = res.json()
        elif file:
            content = await file.read()
            swagger_data = json.loads(content)
        
        if not swagger_data: return {"success": False, "message": "无数据"}
        
        apis = []
        paths = swagger_data.get("paths", {})
        
        # 提取域名 (Base URL)
        servers = swagger_data.get("servers", [])
        base_url = servers[0].get("url", "") if servers else ""

        for path, methods in paths.items():
            # 提取路径级别的通用参数 (Path-level parameters)
            path_params = methods.get("parameters", [])
            
            for method, details in methods.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    # 合并路径级参数和方法级参数
                    all_params = path_params + details.get("parameters", [])
                    
                    # 1. 初始化 headers，添加标准 HTTP headers
                    headers = {
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "User-Agent": "API-Testing-Platform/1.0"
                    }
                    
                    # 如果有 base_url，添加 Host header
                    if base_url:
                        try:
                            from urllib.parse import urlparse
                            parsed = urlparse(base_url)
                            if parsed.netloc:
                                headers["Host"] = parsed.netloc
                        except:
                            pass
                    
                    url_params = []
                    
                    # 2. 处理 Swagger 中定义的 header parameters（会覆盖默认值）
                    for param in all_params:
                        param_in = param.get("in", "")
                        if param_in == "header":
                            headers[param.get("name")] = param.get("schema", {}).get("default", "")
                        else:
                            url_params.append({
                                "name": param.get("name"),
                                "in": param_in,
                                "required": param.get("required", False),
                                "schema": param.get("schema", {}),
                                "description": param.get("description", "")
                            })

                    # 3. 针对写操作自动补全 Content-Type
                    if method.lower() in ["post", "put", "patch"]:
                        # 默认值
                        headers["Content-Type"] = "application/json"
                        
                        request_body = details.get("requestBody", {})
                        if request_body:
                            content_types = request_body.get("content", {})
                            if content_types:
                                # 找到第一个非 null 的 content-type
                                for ct in content_types.keys():
                                    if ct and str(ct).lower() != "null":
                                        headers["Content-Type"] = ct
                                        break
                    
                    apis.append((
                        path, 
                        method.upper(), 
                        details.get("summary", ""), 
                        details.get("description", ""), 
                        base_url,
                        json.dumps(url_params),  # 只存储非header参数
                        json.dumps(details.get("requestBody", {})),
                        json.dumps(headers),  # 单独存储headers
                        project_id
                    ))
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apis WHERE project_id = ?", (project_id,))
        cursor.executemany("""
            INSERT INTO apis (path, method, summary, description, base_url, parameters, request_body, headers, project_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, apis)
        conn.commit()
        
        # 新增: 将导入的API添加到向量索引和知识图谱
        if vector_service or kg_service:
            cursor.execute("SELECT id, path, method, summary, description, project_id FROM apis WHERE project_id = ?", (project_id,))
            imported_apis = cursor.fetchall()
            
            for api_row in imported_apis:
                api_id = str(api_row[0])
                api_info = {
                    'path': api_row[1],
                    'method': api_row[2],
                    'summary': api_row[3],
                    'description': api_row[4],
                    'project_id': api_row[5]
                }
                
                # 添加到知识图谱
                add_api_to_kg(api_id, api_info)
                
                # 添加到向量索引
                await index_api_to_vector(api_id, api_info)
        
        conn.close()
        
        return {"success": True, "indexed": len(apis), "total": len(apis), "project_id": project_id}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/v1/parse/curl")
async def api_parse_curl(req: CurlParseRequest):
    """解析 cURL 命令为 API 定义"""
    try:
        result = parse_curl_command(req.curl)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/apis")
async def create_api(api: APICreateRequest):
    """手动创建 API 接口定义"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO apis (path, method, summary, description, base_url, parameters, request_body, headers, project_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            api.path, 
            api.method, 
            api.name, 
            api.description, 
            api.base_url,
            json.dumps(api.parameters),
            json.dumps(api.request_body),
            json.dumps(api.headers),
            api.project_id
        ))
        new_api_id = cursor.lastrowid
        conn.commit()
        return {"id": new_api_id, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/v1/apis/{api_id}")
async def update_api(api_id: int, api: APICreateRequest):
    """手动修改 API 接口定义"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE apis SET 
                path = ?, method = ?, summary = ?, description = ?, 
                base_url = ?, parameters = ?, request_body = ?, 
                headers = ?, project_id = ?
            WHERE id = ?
        """, (
            api.path, api.method, api.name, api.description, 
            api.base_url, json.dumps(api.parameters), 
            json.dumps(api.request_body), json.dumps(api.headers),
            api.project_id, api_id
        ))
        conn.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/v1/apis")
async def list_apis():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apis ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return {"apis": [
        {
            "id": r["id"], 
            "path": r["path"], 
            "method": r["method"], 
            "name": r["summary"] or r["path"], 
            "description": r["description"],
            "base_url": r["base_url"],
            "parameters": json.loads(r["parameters"] or "[]"),
            "request_body": json.loads(r["request_body"] or "{}"),
            "headers": json.loads(r["headers"] or "{}"),  # 添加headers字段
            "project_id": r["project_id"],
            "tags": []
        } for r in rows
    ]}

@app.delete("/api/v1/apis/{api_id}")
async def delete_api(api_id: str):
    """删除单个API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apis WHERE id = ?", (api_id,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted == 0:
            raise HTTPException(status_code=404, detail="API不存在")
        
        return {"success": True, "message": "API删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/apis/project/{project_id}")
async def delete_apis_by_project(project_id: str):
    """批量删除指定项目的所有API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apis WHERE project_id = ?", (project_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {"success": True, "deleted": deleted_count, "message": f"已删除 {deleted_count} 个API"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/import/postman")
async def import_postman(file: UploadFile = File(...), project_id: str = Form("default-project")):
    """导入Postman Collection文件"""
    import tempfile
    
    try:
        # 1. 保存上传的文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='wb') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # 2. 读取并解析Collection
        with open(tmp_path, 'r', encoding='utf-8') as f:
            collection = json.load(f)
        
        # 3. 解析Collection中的API
        apis = []
        _parse_postman_items(collection.get('item', []), apis, project_id)
        
        # 4. 保存到数据库
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 删除该项目的旧数据
        cursor.execute("DELETE FROM apis WHERE project_id = ?", (project_id,))
        
        # 插入新数据
        for api in apis:
            cursor.execute("""
                INSERT INTO apis (path, method, summary, description, base_url, parameters, request_body, headers, project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                api['path'],
                api['method'],
                api['name'],
                api.get('description', ''),
                api.get('base_url', ''),
                json.dumps(api.get('parameters', [])),
                json.dumps(api.get('request_body', {})),
                json.dumps(api.get('headers', {})),
                project_id
            ))
        
        conn.commit()
        conn.close()
        
        # 5. 清理临时文件
        os.remove(tmp_path)
        
        return {
            "success": True,
            "indexed": len(apis),
            "total": len(apis),
            "project_id": project_id
        }
        
    except Exception as e:
        print(f"❌ Postman导入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": str(e)
        }

def _parse_postman_items(items: List, apis: List, project_id: str, folder_path: str = ""):
    """递归解析Postman Collection项"""
    for item in items:
        if 'request' in item:
            # 这是一个请求
            api = _convert_postman_request(item, folder_path)
            apis.append(api)
        elif 'item' in item:
            # 这是一个文件夹
            new_path = f"{folder_path}/{item['name']}" if folder_path else item['name']
            _parse_postman_items(item['item'], apis, project_id, new_path)

def _convert_postman_request(item: dict, folder_path: str) -> dict:
    """转换Postman请求为标准格式"""
    request = item.get('request', {})
    url = request.get('url', {})
    
    # 处理URL
    if isinstance(url, str):
        path = url
        base_url = ""
    else:
        path = '/' + '/'.join(url.get('path', []))
        # 提取base_url
        protocol = url.get('protocol', 'http')
        host = url.get('host', [])
        if isinstance(host, list):
            base_url = f"{protocol}://{'.'.join(host)}"
        else:
            base_url = f"{protocol}://{host}"
    
    # 解析参数和Headers
    parameters = []
    headers = {}
    
    # Query参数
    if isinstance(url, dict):
        for query in url.get('query', []):
            if not query.get('disabled', False):
                parameters.append({
                    "name": query.get('key'),
                    "in": "query",
                    "type": "string",
                    "required": True,
                    "description": query.get('description', '')
                })
    
    # Header参数 - 单独提取为headers字典
    for header in request.get('header', []):
        if not header.get('disabled', False):
            headers[header.get('key')] = header.get('value', '')
    
    # 解析请求体
    request_body = {}
    body = request.get('body', {})
    if body:
        mode = body.get('mode', 'raw')
        if mode == 'raw':
            try:
                raw_data = json.loads(body.get('raw', '{}'))
                request_body = {"schema": raw_data}
            except:
                request_body = {}
        elif mode == 'formdata':
            request_body = {"schema": {"type": "formdata"}}
    
    return {
        "name": item.get('name', ''),
        "path": path,
        "method": request.get('method', 'GET'),
        "description": item.get('description', ''),
        "base_url": base_url,
        "parameters": parameters,
        "request_body": request_body,
        "headers": headers,
        "tags": [folder_path] if folder_path else []
    }

if __name__ == "__main__":
    print(f"🚀 启动统一后端 (Unified Backend)... 数据库: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)

