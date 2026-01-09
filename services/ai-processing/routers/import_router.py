"""
数据导入API端点
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1/import", tags=["数据导入"])

class ImportRequest(BaseModel):
    source_type: str  # swagger, postman, har
    source: str  # URL或文件路径
    project_id: str

class BatchImportRequest(BaseModel):
    sources: List[dict]
    project_id: str

@router.post("/swagger")
async def import_swagger(
    file: Optional[UploadFile] = File(None),
    source: Optional[str] = Form(None),
    project_id: str = Form("default-project")
):
    """导入Swagger文档 (支持URL或文件)"""
    from main import data_import_service
    import tempfile
    import os
    
    swagger_source = None
    temp_file_path = None
    
    if file:
        # 处理文件上传
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
            content = await file.read()
            tmp.write(content)
            temp_file_path = tmp.name
            swagger_source = temp_file_path
    elif source:
        # 处理 URL
        swagger_source = source
    
    if not swagger_source:
        raise HTTPException(status_code=400, detail="必须提供Swagger URL或上传JSON文件")

    try:
        result = await data_import_service.import_from_source(
            source_type="swagger",
            source=swagger_source,
            project_id=project_id
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        return result
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.post("/postman")
async def import_postman(file: UploadFile = File(...), project_id: str = ""):
    """导入Postman Collection文件"""
    from main import data_import_service
    import tempfile
    import os
    
    # 保存上传的文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = await data_import_service.import_from_source(
            source_type="postman",
            source=tmp_path,
            project_id=project_id
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        return result
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.post("/har")
async def import_har(file: UploadFile = File(...), project_id: str = ""):
    """导入HAR文件"""
    from main import data_import_service
    import tempfile
    import os
    
    # 保存上传的文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.har') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = await data_import_service.import_from_source(
            source_type="har",
            source=tmp_path,
            project_id=project_id
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        return result
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.post("/batch")
async def batch_import(request: BatchImportRequest):
    """批量导入"""
    from main import data_import_service
    
    result = await data_import_service.batch_import(
        sources=request.sources,
        project_id=request.project_id
    )
    
    return result

@router.get("/supported-types")
async def get_supported_types():
    """获取支持的数据源类型"""
    from adapters.data_source_adapter import AdapterFactory
    
    return {
        "types": AdapterFactory.get_supported_types()
    }
