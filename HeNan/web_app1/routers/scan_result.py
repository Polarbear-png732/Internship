"""
视频扫描结果管理路由模块
提供扫描结果的CSV导入、查询、统计等功能
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional
import os
import shutil
import uuid

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
async def import_data(
    task_id: str,
    mode: str = Query("incremental", description="导入模式：incremental/overwrite/fill_missing")
):
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
    
    # 执行导入
    result = scan_result_service.import_data(task, parse_result["records"], mode=mode)
    
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
                "inserted_count": result.get("inserted_count", 0),
                "overwritten_count": result.get("overwritten_count", 0),
                "filled_count": result.get("filled_count", 0),
                "mode": result.get("mode", mode),
                "errors": result.get("errors", [])
            }
        }
    else:
        raise HTTPException(status_code=500, detail=result["error"])


@router.post("/shandong-md5/upload")
async def upload_shandong_md5(file: UploadFile = File(...)):
    """上传山东切片结果txt并回填扫描表空md5"""
    if not file.filename or not file.filename.lower().endswith('.txt'):
        raise HTTPException(status_code=400, detail="仅支持 .txt 文件")

    os.makedirs(scan_result_service.upload_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    file_path = os.path.join(
        scan_result_service.upload_dir,
        f"md5_{uuid.uuid4().hex}_{safe_name}"
    )

    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = scan_result_service.import_shandong_md5_file(file_path)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error") or "处理失败")

        return {
            "code": 200,
            "message": "山东MD5回填完成",
            "data": result.get("data", {})
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理山东MD5文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


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
