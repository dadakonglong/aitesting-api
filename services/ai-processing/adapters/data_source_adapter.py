"""
数据源适配器工厂
支持多种数据源格式的统一适配
"""
from abc import ABC, abstractmethod
from typing import List, Dict
import json
import httpx

class DataSourceAdapter(ABC):
    """数据源适配器基类"""
    
    @abstractmethod
    async def parse(self, source: any) -> List[Dict]:
        """解析数据源，返回统一的API格式"""
        pass
    
    @abstractmethod
    def validate(self, source: any) -> bool:
        """验证数据源格式"""
        pass

class SwaggerAdapter(DataSourceAdapter):
    """Swagger/OpenAPI适配器"""
    
    async def parse(self, source: str) -> List[Dict]:
        """解析Swagger文档"""
        # 1. 获取Swagger文档
        if source.startswith(('http://', 'https://')):
            spec = await self._fetch_swagger(source)
        else:
            spec = self._read_local_swagger(source)
        
        # 2. 解析为统一格式
        apis = []
        base_path = spec.get('basePath', '')
        
        for path, path_item in spec.get('paths', {}).items():
            for method, operation in path_item.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    apis.append(self._convert_to_standard(
                        base_path + path, method, operation, spec
                    ))
        
        return apis
    
    async def _fetch_swagger(self, url: str) -> Dict:
        """从URL获取Swagger文档"""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    def _read_local_swagger(self, file_path: str) -> Dict:
        """从本地文件读取Swagger文档"""
        import os
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到Swagger文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _convert_to_standard(self, path: str, method: str, operation: dict, spec: dict) -> dict:
        """转换为标准格式"""
        return {
            "id": f"{method.upper()}:{path}",
            "name": operation.get('summary', operation.get('operationId', '')),
            "path": path,
            "method": method.upper(),
            "description": operation.get('description', ''),
            "tags": operation.get('tags', []),
            "parameters": self._parse_parameters(operation.get('parameters', []), spec),
            "request_body": self._parse_request_body(operation.get('requestBody'), spec),
            "responses": self._parse_responses(operation.get('responses', {}), spec),
            "source": "swagger"
        }
    
    def _parse_parameters(self, parameters: List, spec: dict) -> List[Dict]:
        """解析参数"""
        parsed = []
        for param in parameters:
            # 处理$ref引用
            if '$ref' in param:
                param = self._resolve_ref(param['$ref'], spec)
            
            parsed.append({
                "name": param.get('name'),
                "in": param.get('in'),  # query, path, header, body
                "type": param.get('type', param.get('schema', {}).get('type')),
                "required": param.get('required', False),
                "description": param.get('description', ''),
                "schema": param.get('schema', {})
            })
        return parsed
    
    def _parse_request_body(self, request_body: Dict, spec: dict) -> Dict:
        """解析请求体"""
        if not request_body:
            return {}
        
        content = request_body.get('content', {})
        json_content = content.get('application/json', {})
        
        return {
            "required": request_body.get('required', False),
            "schema": json_content.get('schema', {})
        }
    
    def _parse_responses(self, responses: Dict, spec: dict) -> Dict:
        """解析响应"""
        parsed = {}
        for status_code, response in responses.items():
            content = response.get('content', {})
            json_content = content.get('application/json', {})
            
            parsed[status_code] = {
                "description": response.get('description', ''),
                "schema": json_content.get('schema', {})
            }
        return parsed
    
    def _resolve_ref(self, ref: str, spec: dict):
        """解析$ref引用"""
        # 简化实现，实际应该递归解析
        parts = ref.split('/')
        current = spec
        for part in parts[1:]:  # 跳过第一个'#'
            current = current.get(part, {})
        return current
    
    def validate(self, source: str) -> bool:
        """验证Swagger文档源"""
        return source.startswith('http') or source.endswith('.json')

class PostmanAdapter(DataSourceAdapter):
    """Postman Collection适配器"""
    
    async def parse(self, collection_path: str) -> List[Dict]:
        """解析Postman Collection"""
        with open(collection_path, 'r', encoding='utf-8') as f:
            collection = json.load(f)
        
        apis = []
        self._parse_items(collection.get('item', []), apis)
        return apis
    
    def _parse_items(self, items: List, apis: List, folder_path: str = ""):
        """递归解析Collection项"""
        for item in items:
            if 'request' in item:
                # 这是一个请求
                apis.append(self._convert_request(item, folder_path))
            elif 'item' in item:
                # 这是一个文件夹
                new_path = f"{folder_path}/{item['name']}" if folder_path else item['name']
                self._parse_items(item['item'], apis, new_path)
    
    def _convert_request(self, item: dict, folder_path: str) -> dict:
        """转换Postman请求为标准格式"""
        request = item['request']
        url = request.get('url', {})
        
        # 处理URL
        if isinstance(url, str):
            url_str = url
            path = url_str
        else:
            url_str = url.get('raw', '')
            path = '/' + '/'.join(url.get('path', []))
        
        return {
            "id": f"{request['method']}:{path}",
            "name": item.get('name', ''),
            "path": path,
            "method": request['method'],
            "description": item.get('request', {}).get('description', ''),
            "tags": [folder_path] if folder_path else [],
            "parameters": self._parse_postman_params(url, request),
            "request_body": self._parse_postman_body(request.get('body')),
            "source": "postman"
        }
    
    def _parse_postman_params(self, url: dict, request: dict) -> List[Dict]:
        """解析Postman参数"""
        params = []
        
        # Query参数
        if isinstance(url, dict):
            for query in url.get('query', []):
                params.append({
                    "name": query.get('key'),
                    "in": "query",
                    "type": "string",
                    "required": not query.get('disabled', False),
                    "description": query.get('description', '')
                })
        
        # Header参数
        for header in request.get('header', []):
            if not header.get('disabled', False):
                params.append({
                    "name": header.get('key'),
                    "in": "header",
                    "type": "string",
                    "required": False,
                    "description": header.get('description', '')
                })
        
        return params
    
    def _parse_postman_body(self, body: dict) -> Dict:
        """解析Postman请求体"""
        if not body:
            return {}
        
        mode = body.get('mode', 'raw')
        
        if mode == 'raw':
            try:
                raw_data = json.loads(body.get('raw', '{}'))
                return {"schema": raw_data}
            except:
                return {}
        elif mode == 'formdata':
            return {"schema": {"type": "formdata"}}
        
        return {}
    
    def validate(self, source: str) -> bool:
        """验证Postman文件"""
        return source.endswith('.json')

class HARAdapter(DataSourceAdapter):
    """HAR文件适配器"""
    
    async def parse(self, har_path: str) -> List[Dict]:
        """解析HAR文件"""
        with open(har_path, 'r', encoding='utf-8') as f:
            har = json.load(f)
        
        apis = []
        seen = set()  # 去重
        
        for entry in har['log']['entries']:
            request = entry['request']
            url = request['url']
            method = request['method']
            
            # 提取路径
            path = self._extract_path_from_url(url)
            api_id = f"{method}:{path}"
            
            # 去重
            if api_id in seen:
                continue
            seen.add(api_id)
            
            apis.append({
                "id": api_id,
                "name": self._extract_name_from_url(url),
                "path": path,
                "method": method,
                "description": "",
                "tags": [],
                "parameters": self._parse_har_params(request),
                "request_body": self._parse_har_body(request),
                "source": "har"
            })
        
        return apis
    
    def _extract_path_from_url(self, url: str) -> str:
        """从URL提取路径"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.path or '/'
    
    def _extract_name_from_url(self, url: str) -> str:
        """从URL提取名称"""
        path = self._extract_path_from_url(url)
        parts = path.strip('/').split('/')
        return parts[-1] if parts else 'unknown'
    
    def _parse_har_params(self, request: dict) -> List[Dict]:
        """解析HAR参数"""
        params = []
        
        # Query参数
        for query in request.get('queryString', []):
            params.append({
                "name": query['name'],
                "in": "query",
                "type": "string",
                "required": False,
                "description": ""
            })
        
        # Headers
        for header in request.get('headers', []):
            if header['name'].lower() not in ['host', 'user-agent', 'accept']:
                params.append({
                    "name": header['name'],
                    "in": "header",
                    "type": "string",
                    "required": False,
                    "description": ""
                })
        
        return params
    
    def _parse_har_body(self, request: dict) -> Dict:
        """解析HAR请求体"""
        post_data = request.get('postData', {})
        if not post_data:
            return {}
        
        mime_type = post_data.get('mimeType', '')
        text = post_data.get('text', '')
        
        if 'json' in mime_type and text:
            try:
                data = json.loads(text)
                return {"schema": data}
            except:
                pass
        
        return {}
    
    def validate(self, source: str) -> bool:
        """验证HAR文件"""
        return source.endswith('.har')

class AdapterFactory:
    """适配器工厂"""
    
    _adapters = {
        'swagger': SwaggerAdapter,
        'openapi': SwaggerAdapter,
        'postman': PostmanAdapter,
        'har': HARAdapter,
    }
    
    @classmethod
    def create(cls, source_type: str) -> DataSourceAdapter:
        """创建适配器"""
        adapter_class = cls._adapters.get(source_type.lower())
        if not adapter_class:
            raise ValueError(f"不支持的数据源类型: {source_type}")
        return adapter_class()
    
    @classmethod
    def register(cls, source_type: str, adapter_class: type):
        """注册新的适配器"""
        cls._adapters[source_type.lower()] = adapter_class
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """获取支持的数据源类型"""
        return list(cls._adapters.keys())
