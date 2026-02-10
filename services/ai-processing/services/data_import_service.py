"""
数据导入服务
处理各种数据源的导入和索引
"""
from typing import Dict, List
from adapters.data_source_adapter import AdapterFactory
from services.vector_service import VectorService
import logging

logger = logging.getLogger(__name__)

import sqlite3
import json
import os

class DataImportService:
    """数据导入服务"""
    
    def __init__(self, vector_service: VectorService, db_path: str = None):
        self.vector_service = vector_service
        self.db_path = db_path
        
        # 自动查找 DB_PATH (如果未提供)
        if not self.db_path:
             current_dir = os.path.dirname(os.path.abspath(__file__)) 
             services_dir = os.path.dirname(os.path.dirname(current_dir))
             root_dir = os.path.dirname(services_dir)
             self.db_path = os.path.join(root_dir, "data", "apis.db")

    async def import_from_source(
        self,
        source_type: str,
        source: str,
        project_id: str
    ) -> Dict:
        """
        从数据源导入接口 (保存到 SQLite 并尝试向量化)
        """
        try:
            # 1. 创建适配器
            adapter = AdapterFactory.create(source_type)
            
            # 2. 验证数据源
            if not adapter.validate(source):
                raise ValueError(f"无效的数据源: {source}")
            
            # 3. 解析数据
            logger.info(f"开始解析{source_type}数据源: {source}")
            apis = await adapter.parse(source)
            logger.info(f"解析完成，共{len(apis)}个接口")
            
            # 4. 数据增强
            enhanced_apis = await self._enhance_apis(apis, project_id)
            
            # 5. 保存到 SQLite
            sqlite_count = 0
            if self.db_path:
                try:
                    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                    conn = sqlite3.connect(self.db_path)
                    c = conn.cursor()
                    
                    # 检查是否有 name 列 (main_sqlite logic)
                    c.execute("PRAGMA table_info(apis)")
                    columns = [info[1] for info in c.fetchall()]
                    has_name_col = "name" in columns

                    for api in enhanced_apis:
                        # 检查是否存在 (path, method, project_id)
                        c.execute("SELECT id FROM apis WHERE path=? AND method=? AND project_id=?", 
                                  (api['path'], api['method'], project_id))
                        row = c.fetchone()
                        
                        params_json = json.dumps(api.get('parameters', []))
                        body_json = json.dumps(api.get('request_body', {}))
                        
                        if row:
                            # 更新
                            if has_name_col:
                                c.execute("""UPDATE apis SET 
                                    name=?, description=?, parameters=?, request_body=?
                                    WHERE id=?""", 
                                    (api['name'], api['description'], params_json, body_json, row[0]))
                            else:
                                c.execute("""UPDATE apis SET 
                                    summary=?, description=?, parameters=?, request_body=?
                                    WHERE id=?""", 
                                    (api['name'], api['description'], params_json, body_json, row[0]))
                        else:
                            # 插入
                            if has_name_col:
                                c.execute("""INSERT INTO apis 
                                    (path, method, name, description, parameters, request_body, project_id)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                    (api['path'], api['method'], api['name'], api['description'], 
                                     params_json, body_json, project_id))
                            else:
                                c.execute("""INSERT INTO apis 
                                    (path, method, summary, description, parameters, request_body, project_id)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                    (api['path'], api['method'], api['name'], api['description'], 
                                     params_json, body_json, project_id))
                        sqlite_count += 1
                    
                    conn.commit()
                    conn.close()
                    logger.info(f"SQLite保存完成: {sqlite_count} 条")
                except Exception as e:
                    logger.error(f"SQLite保存失败: {e}")
            
            # 6. 向量化并索引
            indexed_count = 0
            logger.info("开始向量化索引...")
            if self.vector_service and getattr(self.vector_service, 'enabled', True):
                for api in enhanced_apis:
                    await self.vector_service.index_api(api)
                    indexed_count += 1
                logger.info("向量化索引完成")
            else:
                 logger.warning("向量化服务不可用，跳过索引")
            
            return {
                "success": True, 
                "total": len(apis), 
                "indexed": sqlite_count, 
                "source_type": source_type,
                "project_id": project_id
            }
            
        except Exception as e:
            logger.error(f"导入失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "total": 0,
                "indexed": 0
            }
    
    async def _enhance_apis(self, apis: List[Dict], project_id: str) -> List[Dict]:
        """增强API数据"""
        enhanced = []
        for api in apis:
            # 添加项目ID
            api['project_id'] = project_id
            
            # 确保有ID
            if not api.get('id'):
                api['id'] = f"{api['method']}:{api['path']}"
            
            # 如果没有描述，使用名称
            if not api.get('description'):
                api['description'] = api.get('name', '')
            
            enhanced.append(api)
        
        return enhanced
    
    async def batch_import(
        self,
        sources: List[Dict],
        project_id: str
    ) -> Dict:
        """批量导入"""
        results = []
        total_success = 0
        total_failed = 0
        
        for source_config in sources:
            result = await self.import_from_source(
                source_type=source_config['type'],
                source=source_config['source'],
                project_id=project_id
            )
            results.append(result)
            
            if result['success']:
                total_success += result['indexed']
            else:
                total_failed += 1
        
        return {
            "total_sources": len(sources),
            "success_sources": len(sources) - total_failed,
            "failed_sources": total_failed,
            "total_apis": total_success,
            "details": results
        }
