"""
数据导入服务
处理各种数据源的导入和索引
"""
from typing import Dict, List
from adapters.data_source_adapter import AdapterFactory
from services.vector_service import VectorService
import logging

logger = logging.getLogger(__name__)

class DataImportService:
    """数据导入服务"""
    
    def __init__(self, vector_service: VectorService):
        self.vector_service = vector_service
    
    async def import_from_source(
        self,
        source_type: str,
        source: str,
        project_id: str
    ) -> Dict:
        """
        从数据源导入接口
        
        Args:
            source_type: 数据源类型 (swagger, postman, har)
            source: 数据源（URL或文件路径）
            project_id: 项目ID
            
        Returns:
            导入结果统计
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
            
            # 5. 向量化并索引
            logger.info("开始向量化索引...")
            for api in enhanced_apis:
                await self.vector_service.index_api(api)
            logger.info("向量化索引完成")
            
            return {
                "success": True,
                "total": len(apis),
                "indexed": len(enhanced_apis),
                "source_type": source_type,
                "project_id": project_id
            }
            
        except Exception as e:
            logger.error(f"导入失败: {str(e)}")
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
