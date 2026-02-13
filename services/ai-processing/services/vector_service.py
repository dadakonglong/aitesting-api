"""
向量化服务
提供接口、测试用例的向量化和语义搜索功能
"""
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
except ImportError:
    QdrantClient = None
    Distance = None
    VectorParams = None
    PointStruct = None
    Filter = None
    FieldCondition = None
    MatchValue = None
    
from openai import AsyncOpenAI
from typing import List, Dict, Optional
import hashlib
import logging

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(
        self,
        qdrant_url: str,
        openai_api_key: str,
        qdrant_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        embedding_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_api_key: Optional[str] = None,
    ):
        """
        embedding_base_url: 专用于向量化的 API 地址。若不设则使用 openai_base_url。
        DeepSeek 等仅提供对话接口，不提供 embedding，请设为 OpenAI 或其它支持 embedding 的地址（如 https://api.openai.com/v1）。
        embedding_model: 向量化模型名，默认 text-embedding-3-small。
        embedding_api_key: 专用于向量化的 API Key；不设则使用 openai_api_key。
        """
        self.enabled = False
        if QdrantClient is None:
            logger.warning("QdrantClient库未安装，向量服务将不可用。请安装 qdrant-client。")
            return

        try:
            kwargs = {"url": qdrant_url}
            if qdrant_api_key:
                kwargs["api_key"] = qdrant_api_key
            self.qdrant = QdrantClient(**kwargs)
            base = embedding_base_url or openai_base_url
            client_kwargs = {"api_key": embedding_api_key or openai_api_key}
            if base:
                client_kwargs["base_url"] = base
            if httpx is not None:
                client_kwargs["http_client"] = httpx.AsyncClient(
                    timeout=60.0,
                    trust_env=False,
                    verify=True,
                )
            self.openai = AsyncOpenAI(**client_kwargs)
            self.collection_name = "api_knowledge"
            self.embedding_model = embedding_model or "text-embedding-3-small"
            self.embedding_dim = 1536
            self.enabled = True

            self._init_collection()
        except Exception as e:
            logger.error(f"向量服务初始失败: {e}")
            self.enabled = False
    
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
        if not self.enabled or not self.openai:
            return []
        try:
            response = await self.openai.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(
                f"Embedding failed: {e}. "
                "若对话使用 DeepSeek(OPENAI_BASE_URL)，向量化需单独配置：在 .env 中设置 EMBEDDING_BASE_URL=https://api.openai.com/v1 和有效的 OPENAI_API_KEY（或 EMBEDDING_API_KEY），并确保网络可访问。"
            )
            return []
    
    async def index_api(self, api: Dict):
        """索引API（api 可含 name 或 summary，id 可为 int）"""
        if not self.enabled: return
        
        try:
            name = api.get('name') or api.get('summary', '')
            text = self._build_api_text({**api, "name": name})
            vector = await self.embed_text(text)
            if not vector: return

            point_id = self._generate_id(str(api['id']))
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "type": "api",
                            "api_id": api['id'],
                            "name": name,
                            "path": api.get('path', ''),
                            "method": api.get('method', ''),
                            "description": api.get('description', ''),
                            "tags": api.get('tags', []),
                            "project_id": str(api.get('project_id', '')),
                        }
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Index API failed: {e}")
    
    async def index_test_case(self, test_case: Dict):
        """索引测试用例"""
        if not self.enabled: return
        try:
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
        except Exception as e:
            logger.error(f"Index test case failed: {e}")
    
    async def index_scenario(self, scenario: Dict):
        """索引场景"""
        if not self.enabled: return
        try:
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
        except Exception as e:
            logger.error(f"Index scenario failed: {e}")
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filter_type: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Dict]:
        """语义搜索"""
        if not self.enabled: return []
        try:
            query_vector = await self.embed_text(query)
            if not query_vector: return []
            
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
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _build_api_text(self, api: Dict) -> str:
        """构建API文本描述（name 可为 name 或 summary）"""
        name = api.get('name') or api.get('summary', '')
        parts = [
            f"接口: {name}",
            f"方法: {api.get('method', '')}",
            f"路径: {api.get('path', '')}",
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
    
    def _generate_id(self, item_id) -> str:
        """生成向量点ID（接受 int 或 str）"""
        return hashlib.md5(str(item_id).encode()).hexdigest()
    
    def list_apis(self, project_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """获取所有已索引的API列表"""
        if not self.enabled: return []
        try:
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
        except Exception as e:
            logger.error(f"List APIs failed: {e}")
            return []

    def delete_api(self, api_id: str):
        """删除API索引"""
        if not self.enabled: return
        try:
            point_id = self._generate_id(api_id)
            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
        except Exception as e:
            logger.error(f"Delete API failed: {e}")
