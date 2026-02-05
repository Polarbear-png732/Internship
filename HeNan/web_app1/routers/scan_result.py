"""
视频扫描结果管理路由模块
提供扫描结果的CSV导入、查询、统计、清空等功能
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional
import os
import shutil

from services.scan_result_service import scan_result_service, ScanImportStatus
from logging_config import logger

router = APIRouter(prefix="/api/scan-result", tags=["扫描结果管理"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传扫描结果文件
    
    - **file**: 支持 CSV (.csv) / Excel (.xlsx, .xls) 格式
    
    返回:
    - task_id: 任务ID
    - total_rows: 总行数
    """
    # 验证文件
    is_valid, error_msg = scan_result_service.validate_file(
        file.filename, 
        file.size if hasattr(file, 'size') else 0
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # 保存文件
    file_path = os.path.join(scan_result_service.upload_dir, f"scan_{file.filename}")
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
    
    # 创建任务并解析
    task = scan_result_service.create_task(file_path)
    parse_result = scan_result_service.parse_csv(task)
    
    if not parse_result["success"]:
        # 清理文件
        try:
            os.remove(file_path)
        except:
            pass
        raise HTTPException(status_code=400, detail=parse_result["error"])
    
    return {
        "code": 200,
        "message": "文件上传成功",
        "data": {
            "task_id": task.task_id,
            "total_rows": parse_result["total_rows"],
            "columns": parse_result["columns"]
        }
    }


@router.post("/import/{task_id}")
async def import_data(task_id: str):
    """
    执行增量导入
    
    - **task_id**: 上传时返回的任务ID
    
    注意：采用增量导入模式，跳过已存在的记录（基于file_name + source_folder判重）
    """
    task = scan_result_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    
    if task.status == ScanImportStatus.RUNNING:
        raise HTTPException(status_code=400, detail="任务正在执行中")
    
    # 重新解析CSV获取记录
    parse_result = scan_result_service.parse_csv(task)
    if not parse_result["success"]:
        raise HTTPException(status_code=400, detail=parse_result["error"])
    
    # 执行增量导入
    result = scan_result_service.import_data(task, parse_result["records"])
    
    # 清理临时文件
    try:
        os.remove(task.file_path)
    except:
        pass
    
    if result["success"]:
        return {
            "code": 200,
            "message": result["message"],
            "data": {
                "total": result["total"],
                "success_count": result["success_count"],
                "skipped_count": result["skipped_count"],
                "failed_count": result["failed_count"],
                "errors": result.get("errors", [])
            }
        }
    else:
        raise HTTPException(status_code=500, detail=result["error"])


@router.get("/list")
async def get_scan_results(
    keyword: Optional[str] = Query(None, description="搜索关键词（文件名/剧集名）"),
    source_folder: Optional[str] = Query(None, description="来源文件夹"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    查询扫描结果列表
    
    - **keyword**: 搜索关键词，匹配文件名或剧集名
    - **source_folder**: 按来源文件夹筛选
    - **page**: 页码
    - **page_size**: 每页数量
    """
    result = scan_result_service.search(keyword, source_folder, page, page_size)
    
    if result["success"]:
        return {
            "code": 200,
            "message": "success",
            "data": result["data"]
        }
    else:
        raise HTTPException(status_code=500, detail=result["error"])


@router.get("/stats")
async def get_stats():
    """
    获取扫描结果统计信息
    
    返回:
    - total: 总记录数
    - by_folder: 按文件夹分组统计
    - by_source_file: 按剧集名分组统计（前20）
    """
    result = scan_result_service.get_stats()
    
    if result["success"]:
        return {
            "code": 200,
            "message": "success",
            "data": result["data"]
        }
    else:
        raise HTTPException(status_code=500, detail=result["error"])


@router.delete("/clear")
async def clear_all():
    """
    清空所有扫描结果
    
    ⚠️ 警告：此操作不可恢复
    """
    result = scan_result_service.clear_all()
    
    if result["success"]:
        return {
            "code": 200,
            "message": result["message"]
        }
    else:
        raise HTTPException(status_code=500, detail=result["error"])


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = scan_result_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "code": 200,
        "data": {
            "task_id": task.task_id,
            "status": task.status.value,
            "total_rows": task.total_rows,
            "processed_rows": task.processed_rows,
            "success_count": task.success_count,
            "skipped_count": task.skipped_count,
            "failed_count": task.failed_count
        }
    }
