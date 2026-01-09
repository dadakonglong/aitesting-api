"""
向量化服务
提供接口、测试用例的向量化和语义搜索功能
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from openai import AsyncOpenAI
from typing import List, Dict, Optional
import hashlib

class VectorService:
    def __init__(self, qdrant_url: str, openai_api_key: str):
        self.qdrant = QdrantClient(url=qdrant_url)
        self.openai = AsyncOpenAI(api_key=openai_api_key)
        self.collection_name = "api_knowledge"
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dim = 1536
        
        self._init_collection()
    
    def _init_collection(self):
        """初始化向量集合"""
        try:
            self.qdrant.get_collection(self.collection_name)
        except:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
    
    async def embed_text(self, text: str) -> List[float]:
        """文本向量化"""
        response = await self.openai.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    async def index_api(self, api: Dict):
        """索引API"""
        text = self._build_api_text(api)
        vector = await self.embed_text(text)
        point_id = self._generate_id(api['id'])
        
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "type": "api",
                        "api_id": api['id'],
                        "name": api['name'],
                        "path": api['path'],
                        "method": api['method'],
                        "description": api.get('description', ''),
                        "tags": api.get('tags', []),
                        "project_id": api.get('project_id', ''),
                    }
                )
            ]
        )
    
    async def index_test_case(self, test_case: Dict):
        """索引测试用例"""
        text = self._build_test_case_text(test_case)
        vector = await self.embed_text(text)
        point_id = self._generate_id(test_case['id'])
        
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "type": "test_case",
                        "test_case_id": test_case['id'],
                        "name": test_case['name'],
                        "description": test_case.get('description', ''),
                        "project_id": test_case.get('project_id', ''),
                    }
                )
            ]
        )
    
    async def index_scenario(self, scenario: Dict):
        """索引场景"""
        text = self._build_scenario_text(scenario)
        vector = await self.embed_text(text)
        point_id = self._generate_id(scenario['id'])
        
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "type": "scenario",
                        "scenario_id": scenario['id'],
                        "name": scenario['name'],
                        "description": scenario.get('description', ''),
                        "project_id": scenario.get('project_id', ''),
                    }
                )
            ]
        )
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filter_type: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Dict]:
        """语义搜索"""
        query_vector = await self.embed_text(query)
        
        must_conditions = []
        if filter_type:
            must_conditions.append(
                FieldCondition(key="type", match=MatchValue(value=filter_type))
            )
        if project_id:
            must_conditions.append(
                FieldCondition(key="project_id", match=MatchValue(value=project_id))
            )
        
        search_filter = Filter(must=must_conditions) if must_conditions else None
        
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=search_filter
        )
        
        return [
            {
                "score": hit.score,
                "type": hit.payload['type'],
                "payload": hit.payload
            }
            for hit in results
        ]
    
    def _build_api_text(self, api: Dict) -> str:
        """构建API文本描述"""
        parts = [
            f"接口名称: {api['name']}",
            f"请求方法: {api['method']}",
            f"路径: {api['path']}",
        ]
        if api.get('description'):
            parts.append(f"描述: {api['description']}")
        return "\n".join(parts)
    
    def _build_test_case_text(self, test_case: Dict) -> str:
        """构建测试用例文本描述"""
        parts = [f"测试用例: {test_case['name']}"]
        if test_case.get('description'):
            parts.append(f"描述: {test_case['description']}")
        return "\n".join(parts)
    
    def _build_scenario_text(self, scenario: Dict) -> str:
        """构建场景文本描述"""
        parts = [f"测试场景: {scenario['name']}"]
        if scenario.get('description'):
            parts.append(f"描述: {scenario['description']}")
        return "\n".join(parts)
    
    def _generate_id(self, item_id: str) -> str:
        """生成向量点ID"""
        return hashlib.md5(item_id.encode()).hexdigest()
    
    def list_apis(self, project_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """获取所有已索引的API列表"""
        must_conditions = [
            FieldCondition(key="type", match=MatchValue(value="api"))
        ]
        if project_id:
            must_conditions.append(
                FieldCondition(key="project_id", match=MatchValue(value=project_id))
            )
        
        search_filter = Filter(must=must_conditions)
        
        # 使用 scroll 方法获取所有点
        results, _ = self.qdrant.scroll(
            collection_name=self.collection_name,
            scroll_filter=search_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        return [
            {
                "id": point.payload.get('api_id'),
                "name": point.payload.get('name'),
                "method": point.payload.get('method'),
                "path": point.payload.get('path'),
                "description": point.payload.get('description', ''),
                "tags": point.payload.get('tags', []),
                "project_id": point.payload.get('project_id', '')
            }
            for point in results
        ]
