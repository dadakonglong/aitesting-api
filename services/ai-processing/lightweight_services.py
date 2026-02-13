"""
轻量级知识图谱和向量检索服务
使用NetworkX和FAISS实现,无需额外的数据库服务
"""

import networkx as nx
import faiss
import numpy as np
import pickle
import json
import sqlite3
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LightweightKnowledgeGraph:
    """轻量级知识图谱服务,使用NetworkX替代Neo4j"""
    
    def __init__(self, db_path: str):
        """
        初始化知识图谱
        
        Args:
            db_path: 图谱数据文件路径(.pkl格式)
        """
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self.load_graph()
        logger.info(f"知识图谱已加载: {len(self.graph.nodes)} 个节点, {len(self.graph.edges)} 条边")
    
    def add_api(self, api_id: str, **attributes):
        """
        添加API节点
        
        Args:
            api_id: API唯一标识
            **attributes: API属性(path, method, name等)
        """
        self.graph.add_node(api_id, **attributes, node_type='api')
        self.save_graph()
        logger.debug(f"添加API节点: {api_id}")

    def ensure_api_node(self, api_id: str, **attributes):
        """若节点不存在则添加，存在则跳过（用于导入时建节点，不覆盖）"""
        if api_id not in self.graph:
            self.add_api(api_id, **attributes)
    
    def add_dependency(
        self,
        from_api: str,
        to_api: str,
        field_mapping: Dict = None,
        source_type: str = "execution",
        source_id: Any = None,
        success: bool = True,
        **attributes,
    ):
        """
        添加API依赖关系
        
        Args:
            from_api: 源API ID
            to_api: 目标API ID
            field_mapping: 字段映射关系
            source_type: 来源类型 execution|doc|manual
            source_id: 来源ID（如 execution_id, test_case_id）
            success: 本次是否成功，用于更新 success_count
            **attributes: 其他属性
        """
        if from_api not in self.graph:
            logger.warning(f"API节点不存在: {from_api}，跳过依赖记录")
            return
        if to_api not in self.graph:
            logger.warning(f"API节点不存在: {to_api}，跳过依赖记录")
            return
        
        fm = field_mapping or {}
        if self.graph.has_edge(from_api, to_api):
            edge = self.graph[from_api][to_api]
            edge['count'] = edge.get('count', 0) + 1
            edge['last_used'] = datetime.now().isoformat()
            if success:
                edge['success_count'] = edge.get('success_count', 0) + 1
            else:
                # 阶段四：失败时降低置信度，便于低质量边自动淡出
                edge['success_count'] = max(0, edge.get('success_count', 0) - 1)
            # 合并 field_mapping（新映射覆盖旧）
            existing_fm = edge.get('field_mapping') or {}
            existing_fm.update(fm)
            edge['field_mapping'] = existing_fm
            if source_id:
                edge['last_source_id'] = source_id
            if source_type:
                edge['source_type'] = source_type
        else:
            self.graph.add_edge(
                from_api, to_api,
                field_mapping=fm,
                count=1,
                success_count=1 if success else 0,
                source_type=source_type or "execution",
                source_id=source_id,
                created_at=datetime.now().isoformat(),
                last_used=datetime.now().isoformat(),
                **attributes,
            )
        
        self.save_graph()
        logger.debug(f"添加依赖关系: {from_api} -> {to_api}")

    def remove_dependency(self, from_api: str, to_api: str) -> bool:
        """删除一条依赖边，用于管理修正。返回是否删除了边。"""
        if not self.graph.has_edge(from_api, to_api):
            return False
        self.graph.remove_edge(from_api, to_api)
        self.save_graph()
        logger.debug(f"删除依赖关系: {from_api} -> {to_api}")
        return True

    def remove_node(self, api_id: str) -> bool:
        """删除节点及其所有连边，用于按项目重建时先清空。"""
        if api_id not in self.graph:
            return False
        self.graph.remove_node(api_id)
        self.save_graph()
        logger.debug(f"删除节点: {api_id}")
        return True

    def list_project_node_ids(self, project_id: str) -> List[str]:
        """返回所有以 project_id: 开头的节点 ID 列表。"""
        prefix = f"{project_id}:"
        return [n for n in self.graph.nodes() if isinstance(n, str) and n.startswith(prefix)]

    def export_project_subgraph(self, project_id: str) -> Dict:
        """导出某项目相关的节点与边（节点 ID 以 project_id: 开头），便于人工检查或备份。"""
        prefix = f"{project_id}:"
        nodes = []
        for nid, attrs in self.graph.nodes(data=True):
            if isinstance(nid, str) and nid.startswith(prefix):
                nodes.append({"id": nid, **{k: v for k, v in attrs.items() if k != "node_type"}})
        edges = []
        for u, v in self.graph.edges():
            if isinstance(u, str) and isinstance(v, str) and u.startswith(prefix) and v.startswith(prefix):
                edge = self.graph[u][v]
                edges.append({
                    "from": u,
                    "to": v,
                    "field_mapping": edge.get("field_mapping", {}),
                    "count": edge.get("count", 0),
                    "success_count": edge.get("success_count", 0),
                    "confidence": round((edge.get("success_count", 0) or 0) / max(1, edge.get("count", 1)), 2),
                })
        return {"project_id": project_id, "nodes": nodes, "edges": edges}
    
    def get_dependencies(self, api_id: str, limit: int = 5) -> List[Dict]:
        """
        获取API的依赖关系(按使用频率排序)
        
        Args:
            api_id: API ID
            limit: 返回数量限制
            
        Returns:
            依赖关系列表
        """
        if api_id not in self.graph:
            return []
        
        dependencies = []
        for target in self.graph.successors(api_id):
            edge_data = self.graph[api_id][target]
            dependencies.append({
                'target_api': target,
                'field_mapping': edge_data.get('field_mapping', {}),
                'count': edge_data.get('count', 0),
                'last_used': edge_data.get('last_used'),
                **self.graph.nodes[target]
            })
        
        # 按使用频率排序
        dependencies.sort(key=lambda x: x.get('count', 0), reverse=True)
        return dependencies[:limit]
    
    def get_api_info(self, api_id: str) -> Optional[Dict]:
        """获取API节点信息"""
        if api_id not in self.graph:
            return None
        return dict(self.graph.nodes[api_id])
    
    def find_path(self, from_api: str, to_api: str) -> Optional[List[str]]:
        """
        查找两个API之间的调用路径
        
        Args:
            from_api: 起始API
            to_api: 目标API
            
        Returns:
            API ID列表,表示调用路径
        """
        try:
            return nx.shortest_path(self.graph, from_api, to_api)
        except nx.NetworkXNoPath:
            return None
    
    def get_stats(self) -> Dict:
        """获取图谱统计信息"""
        return {
            'total_apis': len(self.graph.nodes),
            'total_dependencies': len(self.graph.edges),
            'avg_dependencies': len(self.graph.edges) / len(self.graph.nodes) if len(self.graph.nodes) > 0 else 0
        }

    def get_edges_for_prompt(
        self,
        project_id: str,
        apis_for_prompt: List[Dict],
        min_confidence: float = 0.5,
        limit: int = 50,
    ) -> List[Dict]:
        """
        获取与当前候选 API 相关的依赖边，用于生成场景时的上下文增强。
        只返回两端节点都在 apis_for_prompt 中的边，且 success_count/count >= min_confidence。
        """
        if not apis_for_prompt or not project_id:
            return []
        node_ids = set()
        for a in apis_for_prompt:
            m = str(a.get("method") or "GET").strip().upper()
            p = str(a.get("path") or "").strip()
            if p:
                node_ids.add(f"{project_id}:{m}:{p}")
        if not node_ids:
            return []
        edges_out = []
        for u, v in self.graph.edges():
            if u not in node_ids or v not in node_ids:
                continue
            edge = self.graph[u][v]
            count = edge.get("count") or 0
            if count <= 0:
                continue
            success_count = edge.get("success_count", 0)
            confidence = success_count / count
            if confidence < min_confidence:
                continue
            edges_out.append({
                "from_api": u,
                "to_api": v,
                "field_mapping": edge.get("field_mapping") or {},
                "confidence": round(confidence, 2),
                "count": count,
            })
        edges_out.sort(key=lambda x: (-x["confidence"], -x["count"]))
        return edges_out[:limit]

    def get_predecessors(
        self,
        api_id: str,
        min_confidence: float = 0.5,
        limit: int = 5,
    ) -> List[Dict]:
        """
        获取「谁在调用当前 API 之前」的前置依赖（入边）。
        用于执行时补全 param_mappings 或单接口流水线解析依赖链。
        """
        if api_id not in self.graph:
            return []
        out = []
        for from_api in self.graph.predecessors(api_id):
            edge = self.graph[from_api][api_id]
            count = edge.get("count") or 0
            if count <= 0:
                continue
            success_count = edge.get("success_count", 0)
            confidence = success_count / count
            if confidence < min_confidence:
                continue
            node_attrs = dict(self.graph.nodes[from_api])
            out.append({
                "from_api": from_api,
                "field_mapping": edge.get("field_mapping") or {},
                "confidence": round(confidence, 2),
                "path": node_attrs.get("path", ""),
                "method": node_attrs.get("method", "GET"),
            })
        out.sort(key=lambda x: (-x["confidence"],))
        return out[:limit]

    def save_graph(self):
        """持久化图谱到文件"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, 'wb') as f:
                pickle.dump(self.graph, f)
        except Exception as e:
            logger.error(f"保存知识图谱失败: {e}")
    
    def load_graph(self):
        """从文件加载图谱"""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'rb') as f:
                    self.graph = pickle.load(f)
            else:
                self.graph = nx.DiGraph()
                logger.info("创建新的知识图谱")
        except Exception as e:
            logger.error(f"加载知识图谱失败: {e}, 创建新图谱")
            self.graph = nx.DiGraph()


class LightweightVectorSearch:
    """轻量级向量检索服务,使用FAISS替代Qdrant"""
    
    def __init__(self, db_path: str, dimension: int = 1536):
        """
        初始化向量检索服务
        
        Args:
            db_path: SQLite数据库路径
            dimension: 向量维度(OpenAI embedding默认1536)
        """
        self.db_path = db_path
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.id_map = {}  # vector_id -> api_id
        self.conn = None
        self.init_db()
        self.load_index()
        logger.info(f"向量检索已初始化: {self.index.ntotal} 个向量")
    
    def init_db(self):
        """初始化SQLite数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_id TEXT UNIQUE,
                vector BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def add_vector(self, api_id: str, vector: np.ndarray, metadata: Dict):
        """
        添加向量
        
        Args:
            api_id: API唯一标识
            vector: 向量数组
            metadata: API元数据
        """
        try:
            # 确保向量维度正确
            if vector.shape[0] != self.dimension:
                logger.error(f"向量维度不匹配: {vector.shape[0]} != {self.dimension}")
                return
            
            # 添加到FAISS索引
            vector_id = self.index.ntotal
            self.index.add(vector.reshape(1, -1).astype('float32'))
            self.id_map[vector_id] = api_id
            
            # 存储到SQLite
            self.conn.execute("""
                INSERT OR REPLACE INTO vectors (api_id, vector, metadata)
                VALUES (?, ?, ?)
            """, (api_id, vector.tobytes(), json.dumps(metadata, ensure_ascii=False)))
            self.conn.commit()
            
            logger.debug(f"添加向量: {api_id}")
        except Exception as e:
            logger.error(f"添加向量失败: {e}")
    
    def search(self, query_vector: np.ndarray, k: int = 10, threshold: float = 0.5) -> List[Dict]:
        """
        向量搜索
        
        Args:
            query_vector: 查询向量
            k: 返回数量
            threshold: 相似度阈值(0-1)
            
        Returns:
            搜索结果列表
        """
        if self.index.ntotal == 0:
            logger.warning("向量索引为空")
            return []
        
        try:
            # 确保向量维度正确
            if query_vector.shape[0] != self.dimension:
                logger.error(f"查询向量维度不匹配: {query_vector.shape[0]} != {self.dimension}")
                return []
            
            # FAISS搜索
            distances, indices = self.index.search(
                query_vector.reshape(1, -1).astype('float32'), 
                min(k, self.index.ntotal)
            )
            
            results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx == -1:  # FAISS返回-1表示无效结果
                    continue
                
                if idx in self.id_map:
                    api_id = self.id_map[idx]
                    # 转换距离为相似度分数(0-1)
                    score = 1 / (1 + float(dist))
                    
                    # 过滤低分结果
                    if score < threshold:
                        continue
                    
                    # 从数据库获取元数据
                    cursor = self.conn.execute(
                        "SELECT metadata FROM vectors WHERE api_id = ?", (api_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        metadata = json.loads(row['metadata'])
                        results.append({
                            'api_id': api_id,
                            'score': score,
                            'distance': float(dist),
                            **metadata
                        })
            
            return results
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM vectors")
        count = cursor.fetchone()['count']
        return {
            'total_vectors': self.index.ntotal,
            'db_records': count,
            'dimension': self.dimension
        }
    
    def load_index(self):
        """从数据库重建FAISS索引"""
        try:
            cursor = self.conn.execute("SELECT id, api_id, vector FROM vectors ORDER BY id")
            for row in cursor:
                vector_id = row['id'] - 1  # FAISS索引从0开始
                api_id = row['api_id']
                vector = np.frombuffer(row['vector'], dtype=np.float32)
                
                if vector.shape[0] == self.dimension:
                    self.index.add(vector.reshape(1, -1))
                    self.id_map[vector_id] = api_id
            
            logger.info(f"从数据库重建索引: {self.index.ntotal} 个向量")
        except Exception as e:
            logger.error(f"加载索引失败: {e}")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


# 使用示例
if __name__ == "__main__":
    # 测试知识图谱
    kg = LightweightKnowledgeGraph("data/knowledge_graph.pkl")
    kg.add_api("api1", path="/user/login", method="POST", name="用户登录")
    kg.add_api("api2", path="/user/profile", method="GET", name="获取用户信息")
    kg.add_dependency("api1", "api2", field_mapping={"token": "Authorization"})
    
    print("知识图谱统计:", kg.get_stats())
    print("API1的依赖:", kg.get_dependencies("api1"))
    
    # 测试向量检索
    vs = LightweightVectorSearch("data/vectors.db")
    
    # 模拟向量(实际使用时应该用OpenAI Embedding)
    test_vector = np.random.rand(1536).astype('float32')
    vs.add_vector("api1", test_vector, {"path": "/user/login", "method": "POST"})
    
    # 搜索
    results = vs.search(test_vector, k=5)
    print("搜索结果:", results)
    print("向量检索统计:", vs.get_stats())
    
    vs.close()
