from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import sqlite3
import json
import os

router = APIRouter(prefix="/api/v1/apis", tags=["API管理"])

# 智能查找 DB_PATH
# 优先查找项目根目录下的 data/apis.db (main_sqlite.py 逻辑)
# 其次查找 services/data/apis.db (main.py 逻辑)
current_dir = os.path.dirname(os.path.abspath(__file__)) # services/ai-processing/routers
ai_proc_dir = os.path.dirname(current_dir) # services/ai-processing
services_dir = os.path.dirname(ai_proc_dir) # services
root_dir = os.path.dirname(services_dir) # root

DB_PATH_ROOT = os.path.join(root_dir, "data", "apis.db")
DB_PATH_SERVICES = os.path.join(services_dir, "data", "apis.db")

if os.path.exists(os.path.dirname(DB_PATH_ROOT)):
    DB_PATH = DB_PATH_ROOT
elif os.path.exists(os.path.dirname(DB_PATH_SERVICES)):
    DB_PATH = DB_PATH_SERVICES
else:
    # 默认 fallback
    DB_PATH = DB_PATH_ROOT

print(f"API Management using DB: {DB_PATH}")

class APIModel(BaseModel):
    name: str
    method: str
    path: str
    description: Optional[str] = ""
    project_id: str = "default-project"
    base_url: Optional[str] = ""
    headers: Optional[Dict] = {}
    request_body: Optional[Union[Dict, str]] = {}
    parameters: Optional[Union[List, str, Dict]] = []
    tags: Optional[List[str]] = []

def get_db():
    # 确保目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.get("")
async def list_apis(project_id: Optional[str] = None, limit: int = 100):
    """
    获取API列表 (从SQLite读取)
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        print(f"DEBUG: list_apis called with project_id={project_id}, limit={limit}")
        print(f"DEBUG: Using DB_PATH={DB_PATH}")
        
        # 确保表存在 (防止 main_sqlite.py 尚未初始化)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='apis'")
        if not cursor.fetchone():
             print("DEBUG: Table 'apis' does not exist")
             conn.close()
             return {"total": 0, "apis": []}

        query = "SELECT * FROM apis"
        args = []
        
        if project_id:
            query += " WHERE project_id = ?"
            args.append(project_id)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        args.append(limit)
        
        print(f"DEBUG: Executing query: {query} with args: {args}")
        cursor.execute(query, tuple(args))
        rows = cursor.fetchall()
        print(f"DEBUG: Found {len(rows)} rows")
        conn.close()
        
        apis = []
        for row in rows:
            api = dict(row)
            # 兼容性处理：如果没有 name 字段，使用 summary 填充
            if 'name' not in api or not api['name']:
                api['name'] = api.get('summary') or api.get('path', 'Untitled API')
            
            # 解析 JSON 字段
            for field in ['parameters', 'request_body', 'headers']:
                 if api.get(field):
                     try:
                         api[field] = json.loads(api[field])
                     except:
                         api[field] = {} if field != 'parameters' else []
            apis.append(api)
            
        return {"total": len(apis), "apis": apis}
    except Exception as e:
        print(f"List APIs Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_api(api: APIModel, background_tasks: BackgroundTasks):
    """
    创建API
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 序列化 JSON 字段
        parameters_json = "[]"
        if isinstance(api.parameters, list):
            parameters_json = json.dumps(api.parameters, ensure_ascii=False)
        elif isinstance(api.parameters, dict):
            # 如果是字典，可能是用户误填 {}，或者单项参数
            if not api.parameters:
                parameters_json = "[]"
            else:
                parameters_json = json.dumps([api.parameters], ensure_ascii=False)
        elif isinstance(api.parameters, str):
            try:
                 parsed = json.loads(api.parameters)
                 if isinstance(parsed, list):
                     parameters_json = api.parameters
                 elif isinstance(parsed, dict):
                     parameters_json = json.dumps([parsed] if parsed else [], ensure_ascii=False)
                 else:
                     parameters_json = "[]"
            except:
                 parameters_json = "[]"
        
        # 处理 request_body: 可能是 Dict 或 str
        parameters_json = json.dumps(api.parameters, ensure_ascii=False)
        
        # 处理 request_body: 可能是 Dict 或 str
        if isinstance(api.request_body, str):
            # 尝试解析为 JSON
            try:
                rb = json.loads(api.request_body)
                if isinstance(rb, dict):
                    request_body_json = api.request_body # 已经是 JSON string
                else:
                    # 比如是 list 或 invalid type，强制转 dict 结构或保持 string
                    request_body_json = json.dumps(rb, ensure_ascii=False)
            except:
                # 解析失败，可能是 form data (key=val)，尝试简单的转换或封装
                # 简单起见，如果非 JSON 字符串，封装为 {"content": ...} 以满足 Dict 约束
                # 或者尝试解析 query string
                try:
                    from urllib.parse import parse_qs
                    qs = parse_qs(api.request_body)
                    # parse_qs 返回 {k: [v]}, 简化为 {k: v[0]}
                    flat_qs = {k: v[0] for k, v in qs.items()}
                    if flat_qs:
                         request_body_json = json.dumps(flat_qs, ensure_ascii=False)
                    else:
                         request_body_json = json.dumps({"raw_content": api.request_body}, ensure_ascii=False)
                except:
                    request_body_json = json.dumps({"raw_content": api.request_body}, ensure_ascii=False)
        else:
            request_body_json = json.dumps(api.request_body, ensure_ascii=False)
            
        headers_json = json.dumps(api.headers, ensure_ascii=False)
        headers_json = json.dumps(api.headers, ensure_ascii=False)
        
        # 兼容性：检查是否存在 name 列，没有则存入 summary
        cursor.execute("PRAGMA table_info(apis)")
        columns = [info[1] for info in cursor.fetchall()]
        has_name_col = "name" in columns
        
        if has_name_col:
            cursor.execute(
                """
                INSERT INTO apis (name, method, path, description, project_id, base_url, parameters, request_body, headers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (api.name, api.method, api.path, api.description, api.project_id, api.base_url, parameters_json, request_body_json, headers_json)
            )
        else:
            # 存入 summary
            cursor.execute(
                """
                INSERT INTO apis (summary, method, path, description, project_id, base_url, parameters, request_body, headers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (api.name, api.method, api.path, api.description, api.project_id, api.base_url, parameters_json, request_body_json, headers_json)
            )
            
        api_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # 尝试更新向量 (如果可用)
        try:
            from main import vector_service
            api_data = api.dict()
            api_data['id'] = str(api_id)
            background_tasks.add_task(vector_service.index_api, api_data)
        except ImportError:
            pass # main.py 可能未运行或 vector_service 不可用
        except Exception as e:
            print(f"Vector Index Error: {e}")
        
        return {"success": True, "id": str(api_id), "message": "API创建成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{api_id}")
async def get_api(api_id: int):
    """
    获取单个API详情
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM apis WHERE id = ?", (api_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="API不存在")
            
        api = dict(row)
        if 'name' not in api or not api['name']:
            api['name'] = api.get('summary') or api.get('path', 'Untitled API')
            
        for field in ['parameters', 'request_body', 'headers']:
             if api.get(field):
                 try:
                     api[field] = json.loads(api[field])
                 except:
                     api[field] = {} if field != 'parameters' else []
        return api
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{api_id}")
async def update_api(api_id: int, api: APIModel, background_tasks: BackgroundTasks):
    """
    更新API
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 检查是否存在
        cursor.execute("SELECT id FROM apis WHERE id = ?", (api_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="API不存在")
        
        parameters_json = "[]"
        if isinstance(api.parameters, list):
            parameters_json = json.dumps(api.parameters, ensure_ascii=False)
        elif isinstance(api.parameters, dict):
            if not api.parameters:
                parameters_json = "[]"
            else:
                parameters_json = json.dumps([api.parameters], ensure_ascii=False)
        elif isinstance(api.parameters, str):
            try:
                 parsed = json.loads(api.parameters)
                 if isinstance(parsed, list):
                     parameters_json = api.parameters
                 elif isinstance(parsed, dict):
                     parameters_json = json.dumps([parsed] if parsed else [], ensure_ascii=False)
                 else:
                     parameters_json = "[]"
            except:
                 parameters_json = "[]"
        
        # 处理 request_body: 可能是 Dict 或 str (复用逻辑)
        parameters_json = json.dumps(api.parameters, ensure_ascii=False)
        
        # 处理 request_body: 可能是 Dict 或 str (复用逻辑)
        if isinstance(api.request_body, str):
            try:
                rb = json.loads(api.request_body)
                if isinstance(rb, dict):
                    request_body_json = api.request_body
                else:
                    request_body_json = json.dumps(rb, ensure_ascii=False)
            except:
                try:
                    from urllib.parse import parse_qs
                    qs = parse_qs(api.request_body)
                    flat_qs = {k: v[0] for k, v in qs.items()}
                    if flat_qs:
                         request_body_json = json.dumps(flat_qs, ensure_ascii=False)
                    else:
                         request_body_json = json.dumps({"raw_content": api.request_body}, ensure_ascii=False)
                except:
                    request_body_json = json.dumps({"raw_content": api.request_body}, ensure_ascii=False)
        else:
            request_body_json = json.dumps(api.request_body, ensure_ascii=False)
            
        headers_json = json.dumps(api.headers, ensure_ascii=False)
        headers_json = json.dumps(api.headers, ensure_ascii=False)
        
        # 兼容性：检查是否存在 name 列
        cursor.execute("PRAGMA table_info(apis)")
        columns = [info[1] for info in cursor.fetchall()]
        has_name_col = "name" in columns
        
        if has_name_col:
            cursor.execute(
                """
                UPDATE apis 
                SET name=?, method=?, path=?, description=?, project_id=?, base_url=?, parameters=?, request_body=?, headers=?
                WHERE id = ?
                """,
                (api.name, api.method, api.path, api.description, api.project_id, api.base_url, parameters_json, request_body_json, headers_json, api_id)
            )
        else:
            cursor.execute(
                """
                UPDATE apis 
                SET summary=?, method=?, path=?, description=?, project_id=?, base_url=?, parameters=?, request_body=?, headers=?
                WHERE id = ?
                """,
                (api.name, api.method, api.path, api.description, api.project_id, api.base_url, parameters_json, request_body_json, headers_json, api_id)
            )
            
        conn.commit()
        conn.close()
        
        # 尝试更新向量
        try:
            from main import vector_service
            api_data = api.dict()
            api_data['id'] = str(api_id)
            background_tasks.add_task(vector_service.index_api, api_data)
        except:
            pass
        
        return {"success": True, "id": str(api_id), "message": "API更新成功"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{api_id}")
async def delete_api(api_id: int, background_tasks: BackgroundTasks):
    """
    删除API
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM apis WHERE id = ?", (api_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="API不存在")
            
        conn.commit()
        conn.close()
        
        # 尝试删除向量
        try:
            from main import vector_service
            background_tasks.add_task(vector_service.delete_api, str(api_id))
        except:
            pass
        
        return {"success": True, "message": "API已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
