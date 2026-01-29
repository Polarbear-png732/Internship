"""
版权方数据管理路由模块
提供版权内容的增删改查、Excel批量导入导出、剧头子集生成等核心功能
支持异步导入、实时进度推送（SSE）和多客户数据同步
"""
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
import pymysql
import pandas as pd
import json
import time
from decimal import Decimal
from io import BytesIO
from urllib.parse import quote
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

from database import get_db
from utils import (
    get_pinyin_abbr, get_content_dir, get_product_category,
    get_image_url, get_media_url, format_duration, format_datetime, get_genre
)
from config import COPYRIGHT_FIELDS, CUSTOMER_CONFIGS, get_enabled_customers
from models import CopyrightCreate, CopyrightUpdate, CopyrightResponse

# 从服务层导入
from services.copyright_service import (
    CopyrightDramaService, CopyrightQueryService,
    COPYRIGHT_EXPORT_COLUMNS, convert_decimal, convert_row
)
from services.cache_service import get_cache, CacheKeys

router = APIRouter(prefix="/api/copyright", tags=["版权管理"])

# 获取缓存实例
cache = get_cache()

# 为了向后兼容，保留对服务层函数的引用（使用服务层的静态方法）
_convert_decimal = convert_decimal
_convert_row = convert_row
_build_drama_props_for_customer = CopyrightDramaService.build_drama_props_for_customer
_create_episodes_for_customer = CopyrightDramaService.create_episodes_for_customer
_create_drama_for_customer = CopyrightDramaService.create_drama_for_customer
_update_drama_for_customer = CopyrightDramaService.update_drama_for_customer
_delete_drama_and_episodes = CopyrightDramaService.delete_drama_and_episodes
_get_current_episode_count = CopyrightDramaService.get_current_episode_count
_update_episodes_incremental = CopyrightDramaService.update_episodes_incremental
_batch_create_episodes = CopyrightDramaService.batch_create_episodes
_update_episode_properties = CopyrightDramaService.update_episode_properties


# ============================================================
# API 路由
# ============================================================

@router.get("")
def get_copyright_list(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取版权方数据列表（带缓存）"""
    # 尝试从缓存获取
    cache_key = f"{CacheKeys.COPYRIGHT_LIST}:{keyword or ''}:{page}:{page_size}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            where_clause, params = "", []
            if keyword:
                where_clause = "WHERE media_name LIKE %s"
                params.append(f"%{keyword}%")
            
            cursor.execute(f"SELECT COUNT(*) as total FROM copyright_content {where_clause}", params)
            total = cursor.fetchone()['total']
            
            offset = (page - 1) * page_size
            cursor.execute(f"SELECT * FROM copyright_content {where_clause} ORDER BY id DESC LIMIT %s OFFSET %s",
                          params + [page_size, offset])
            items = cursor.fetchall()
            
            result = {
                "code": 200, "message": "success",
                "data": {"list": items, "total": total, "page": page, "page_size": page_size,
                        "total_pages": (total + page_size - 1) // page_size}
            }
            
            # 缓存结果（仅缓存第一页和无关键词的查询）
            if page == 1 and not keyword:
                cache.set(cache_key, result, ttl=60)  # 缓存1分钟
            
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/template")
def download_import_template():
    """下载版权方数据导入模板（只有表头的Excel文件）"""
    try:
        # 使用导出的列名顺序创建空的DataFrame，只有表头
        columns = list(COPYRIGHT_EXPORT_COLUMNS.values())
        
        df = pd.DataFrame(columns=columns)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='版权方数据模板', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['版权方数据模板']
            
            # 设置列宽
            col_widths = {
                '上游版权方': 15, 
                '介质名称': 25, 
                '一级分类': 10, 
                '二级分类': 10, 
                '一级分类-河南标准': 15, 
                '二级分类-河南标准': 15, 
                '集数': 8, 
                '单集时长（分）': 12, 
                '总时长（分）': 12, 
                '出品年代': 10, 
                '首播日期': 12,
                '授权区域（全国/单独沟通）': 20, 
                '授权平台（IPTV、OTT、小屏、待沟通）': 30, 
                '合作方式（采买/分成）': 18, 
                '制作地区': 12,
                '语言': 10, 
                '语言-河南标准': 15, 
                '国别': 10,
                '导演': 15, 
                '编剧': 15, 
                '主演\\嘉宾\\主持人': 20, 
                '作者': 15,
                '推荐语/一句话介绍': 30, 
                '简介': 40, 
                '关键字': 15, 
                '标清\\高清\\4K\\3D\\杜比': 15, 
                '发行许可编号\\备案号等': 20, 
                '行业内相关网站的评级、评分（骨朵\\艺恩\\猫眼\\豆瓣\\时光网\\百度\\其他主流视频网站等评分': 35,
                '独家\\非独': 10, 
                '版权开始时间': 12, 
                '版权结束时间': 12,
                '二级分类-山东': 15,
            }
            
            # 应用列宽
            for i, col_name in enumerate(columns):
                width = col_widths.get(col_name, 12)
                worksheet.set_column(i, i, width)
            
            # 设置表头格式
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#E0E7FF',
                'border': 1,
                'text_wrap': True,
                'valign': 'vcenter',
                'align': 'center'
            })
            
            for col_num, value in enumerate(columns):
                worksheet.write(0, col_num, value, header_format)
            
            # 设置首行高度
            worksheet.set_row(0, 30)
        
        output.seek(0)
        filename_encoded = quote('版权方数据导入模板.xlsx')
        
        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename*=UTF-8\'\'{filename_encoded}'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成模板失败: {str(e)}")


@router.get("/export")
def export_copyright_to_excel():
    """导出所有版权方数据为Excel文件（高性能版本）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM copyright_content ORDER BY id")
            items = cursor.fetchall()
        
        export_data = []
        for item in items:
            row = {}
            for db_col, cn_col in COPYRIGHT_EXPORT_COLUMNS.items():
                value = item.get(db_col, '')
                
                # 将单集时长和总时长转换为整数
                if db_col in ['single_episode_duration', 'total_duration']:
                    if value is not None and value != '':
                        try:
                            # 转换为整数（四舍五入）
                            value = int(round(float(value)))
                        except (ValueError, TypeError):
                            value = ''
                    else:
                        value = ''
                
                # 截断过长的文本
                if value and isinstance(value, str) and len(value) > 100:
                    value = value[:100] + '...'
                    
                row[cn_col] = value
            export_data.append(row)
        
        df = pd.DataFrame(export_data, columns=list(COPYRIGHT_EXPORT_COLUMNS.values()))
        
        output = BytesIO()
        # 使用 xlsxwriter 引擎，性能更好
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='版权方数据', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['版权方数据']
            
            # 设置列宽（按照数据库表结构顺序，不包含序号(自定义)）
            col_widths = {
                '序号': 8, 
                '上游版权方': 15, 
                '介质名称': 25, 
                '一级分类': 10, 
                '二级分类': 10, 
                '一级分类-河南标准': 15, 
                '二级分类-河南标准': 15, 
                '集数': 8, 
                '单集时长（分）': 12, 
                '总时长（分）': 12, 
                '出品年代': 10, 
                '首播日期': 12,
                '授权区域（全国/单独沟通）': 20, 
                '授权平台（IPTV、OTT、小屏、待沟通）': 30, 
                '合作方式（采买/分成）': 18, 
                '制作地区': 12,
                '语言': 10, 
                '语言-河南标准': 15, 
                '国别': 10,
                '导演': 15, 
                '编剧': 15, 
                '主演\\嘉宾\\主持人': 20, 
                '作者': 15,
                '推荐语/一句话介绍': 30, 
                '简介': 40, 
                '关键字': 20, 
                '标清\\高清\\4K\\3D\\杜比': 18, 
                '发行许可编号\\备案号等': 20, 
                '行业内相关网站的评级、评分（骨朵\\艺恩\\猫眼\\豆瓣\\时光网\\百度\\其他主流视频网站等评分': 50, 
                '独家\\非独': 12, 
                '版权开始时间': 15, 
                '版权结束时间': 15, 
                '二级分类-山东': 15
            }
            
            for idx, col_name in enumerate(df.columns):
                width = col_widths.get(col_name, 15)
                worksheet.set_column(idx, idx, width)
            
            # 设置表头格式
            header_format = workbook.add_format({
                'bold': True, 'align': 'center', 'valign': 'vcenter',
                'bg_color': '#4472C4', 'font_color': 'white', 'border': 1
            })
            for idx, col_name in enumerate(df.columns):
                worksheet.write(0, idx, col_name, header_format)
            
            # 冻结首行
            worksheet.freeze_panes(1, 0)
        
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote('版权方数据.xlsx')}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers")
def get_customer_list():
    """获取所有客户配置列表"""
    customers = []
    for code, config in CUSTOMER_CONFIGS.items():
        customers.append({
            'code': code,
            'name': config['name'],
            'is_enabled': config.get('is_enabled', True)
        })
    return {"code": 200, "data": customers}


@router.get("/{item_id}")
def get_copyright_detail(item_id: int):
    """获取版权方数据详情"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM copyright_content WHERE id = %s", (item_id,))
            item = cursor.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail="数据不存在")
            return {"code": 200, "message": "success", "data": item}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_copyright(data: Dict[str, Any] = Body(...)):
    """创建版权方数据，自动为所有启用的客户生成剧头和子集"""
    start_time = time.time()
    
    if 'media_name' not in data or not data['media_name']:
        raise HTTPException(status_code=400, detail="介质名称不能为空")
    
    media_name = data['media_name']
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            try:
                # 1. 为所有启用的客户创建剧头和子集
                enabled_customers = get_enabled_customers()
                drama_ids = {}
                total_episodes = int(data.get('episode_count') or 0)
                
                for customer_code in enabled_customers:
                    drama_id = _create_drama_for_customer(cursor, data, media_name, customer_code)
                    drama_ids[customer_code] = drama_id
                
                # 2. 插入版权方数据
                insert_fields = ['drama_ids']
                insert_values = [json.dumps(drama_ids)]
                
                for field in COPYRIGHT_FIELDS:
                    if field in data and data[field] is not None:
                        insert_fields.append(field)
                        insert_values.append(data[field])
                
                cursor.execute(
                    f"INSERT INTO copyright_content ({', '.join(insert_fields)}) VALUES ({', '.join(['%s'] * len(insert_fields))})",
                    insert_values
                )
                
                copyright_id = cursor.lastrowid
                conn.commit()
                
                elapsed_time = time.time() - start_time
                return {
                    "code": 200, "message": "创建成功",
                    "data": {
                        "copyright_id": copyright_id,
                        "drama_ids": drama_ids,
                        "customers_count": len(drama_ids),
                        "elapsed_time": f"{elapsed_time:.3f}s"
                    }
                }
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{item_id}")
def update_copyright(item_id: int, data: Dict[str, Any] = Body(...)):
    """更新版权方数据，并同步更新所有关联的剧集和子集（增量更新，事务保护）"""
    start_time = time.time()
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 获取原数据
            cursor.execute("SELECT * FROM copyright_content WHERE id = %s", (item_id,))
            item = cursor.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail="数据不存在")
            
            # 保存原数据用于增量更新比较
            old_media_name = item.get('media_name')
            old_episode_count = int(item.get('episode_count') or 0)
            
            try:
                # 1. 更新版权方表
                update_parts, update_values = [], []
                changed_fields = {}
                for field in COPYRIGHT_FIELDS:
                    if field in data:
                        update_parts.append(f"{field} = %s")
                        update_values.append(data[field])
                        # 记录变更字段
                        if item.get(field) != data[field]:
                            changed_fields[field] = {'old': item.get(field), 'new': data[field]}
                
                if update_parts:
                    update_values.append(item_id)
                    cursor.execute(f"UPDATE copyright_content SET {', '.join(update_parts)} WHERE id = %s", update_values)
                
                # 2. 合并数据
                merged_data = dict(item)
                merged_data.update(data)
                media_name = merged_data.get('media_name')
                
                # 3. 获取现有的 drama_ids
                drama_ids_raw = item.get('drama_ids')
                if isinstance(drama_ids_raw, str):
                    drama_ids = json.loads(drama_ids_raw) if drama_ids_raw else {}
                elif isinstance(drama_ids_raw, dict):
                    drama_ids = drama_ids_raw
                else:
                    drama_ids = {}
                
                # 4. 更新所有已存在的客户剧头（增量更新）
                total_stats = {'dramas_updated': 0, 'episodes_added': 0, 'episodes_deleted': 0, 'episodes_updated': 0}
                
                for customer_code, drama_id in drama_ids.items():
                    if drama_id:
                        stats = _update_drama_for_customer(
                            cursor, drama_id, merged_data, media_name, customer_code,
                            old_episode_count=old_episode_count,
                            old_media_name=old_media_name
                        )
                        total_stats['dramas_updated'] += 1
                        total_stats['episodes_added'] += stats.get('added', 0)
                        total_stats['episodes_deleted'] += stats.get('deleted', 0)
                        total_stats['episodes_updated'] += stats.get('updated', 0)
                
                # 5. 为新启用的客户创建剧头（如果有）
                enabled_customers = get_enabled_customers()
                for customer_code in enabled_customers:
                    if customer_code not in drama_ids:
                        new_drama_id = _create_drama_for_customer(cursor, merged_data, media_name, customer_code)
                        drama_ids[customer_code] = new_drama_id
                
                # 6. 更新 drama_ids
                cursor.execute(
                    "UPDATE copyright_content SET drama_ids = %s WHERE id = %s",
                    (json.dumps(drama_ids), item_id)
                )
                
                # 单一事务提交
                conn.commit()
                
                elapsed_time = time.time() - start_time
                return {
                    "code": 200, 
                    "message": "更新成功", 
                    "data": {
                        "id": item_id, 
                        "drama_ids": drama_ids,
                        "stats": total_stats,
                        "elapsed_time": f"{elapsed_time:.3f}s"
                    }
                }
                
            except Exception as e:
                # 事务回滚
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{item_id}")
def delete_copyright(item_id: int):
    """删除版权方数据及所有关联的剧集和子集"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("SELECT id, media_name, drama_ids FROM copyright_content WHERE id = %s", (item_id,))
            item = cursor.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail="数据不存在")
            
            media_name = item.get('media_name')
            
            # 获取所有关联的 drama_ids
            drama_ids_raw = item.get('drama_ids')
            if isinstance(drama_ids_raw, str):
                drama_ids = json.loads(drama_ids_raw) if drama_ids_raw else {}
            elif isinstance(drama_ids_raw, dict):
                drama_ids = drama_ids_raw
            else:
                drama_ids = {}
            
            try:
                # 删除所有关联的剧头和子集
                deleted_dramas = []
                for customer_code, drama_id in drama_ids.items():
                    if drama_id:
                        _delete_drama_and_episodes(cursor, drama_id)
                        deleted_dramas.append(drama_id)
                
                # 删除版权数据
                cursor.execute("DELETE FROM copyright_content WHERE id = %s", (item_id,))
                conn.commit()
                
                return {
                    "code": 200, "message": "删除成功",
                    "data": {"id": item_id, "deleted_dramas": deleted_dramas}
                }
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Excel批量导入API
# ============================================================

from fastapi import UploadFile, File, BackgroundTasks
import asyncio
import os
import sys

# 添加父目录到路径以导入services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.import_service import ExcelImportService, ImportStatus

# 创建导入服务实例
import_service = ExcelImportService(upload_dir="temp/uploads")


@router.post("/import/upload")
async def upload_excel_for_import(file: UploadFile = File(...)):
    """上传Excel文件并返回数据预览
    
    接收Excel文件，解析内容并返回预览数据和统计信息
    """
    # 验证文件
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    is_valid, error_msg = import_service.validate_file(file.filename, file_size)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # 保存文件
    os.makedirs("temp/uploads", exist_ok=True)
    file_path = f"temp/uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)
    
    try:
        # 创建任务
        task = import_service.create_task(file_path)
        
        # 解析Excel
        parse_result = import_service.parse_excel(task)
        if not parse_result.get("success"):
            raise HTTPException(status_code=400, detail=parse_result.get("error"))
        
        # 验证数据
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            validate_result = import_service.validate_data(task, cursor)
        
        if not validate_result.get("success"):
            raise HTTPException(status_code=400, detail=validate_result.get("error"))
        
        return {
            "code": 200,
            "message": "文件解析成功",
            "data": validate_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")


@router.post("/import/execute/{task_id}")
def execute_import(task_id: str, background_tasks: BackgroundTasks):
    """执行导入任务
    
    启动异步导入任务，返回任务ID
    """
    task = import_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == ImportStatus.RUNNING:
        raise HTTPException(status_code=400, detail="任务正在执行中")
    
    if task.valid_data is None or len(task.valid_data) == 0:
        raise HTTPException(status_code=400, detail="没有有效数据可导入")
    
    # 在后台执行导入
    background_tasks.add_task(_run_import_task, task_id)
    
    return {
        "code": 200,
        "message": "导入任务已启动",
        "data": {
            "task_id": task_id,
            "total_rows": len(task.valid_data)
        }
    }


async def _run_import_task(task_id: str):
    """后台执行导入任务"""
    import asyncio
    
    task = import_service.get_task(task_id)
    if not task:
        return
    
    try:
        # 在线程池中执行同步的数据库操作
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_import_task, task_id)
    except Exception as e:
        task.status = ImportStatus.FAILED
        task.errors.append({"message": f"导入失败: {str(e)}"})


def _sync_import_task(task_id: str):
    """同步执行导入任务"""
    task = import_service.get_task(task_id)
    if not task:
        return
    
    try:
        with get_db() as conn:
            import_service.execute_import_sync(task, conn)
    except Exception as e:
        task.status = ImportStatus.FAILED
        task.errors.append({"message": f"导入失败: {str(e)}"})


@router.get("/import/progress/{task_id}")
async def get_import_progress(task_id: str):
    """获取导入进度（SSE流）
    
    返回SSE流，实时推送导入进度
    """
    task = import_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    async def event_generator():
        """SSE事件生成器"""
        last_processed = 0
        
        while True:
            # 检查任务状态
            if task.status == ImportStatus.COMPLETED:
                # 发送完成事件
                result = {
                    "inserted": task.success_count,
                    "skipped": task.skipped_count,
                    "failed": task.failed_count,
                    "elapsed": str(task.completed_at - task.created_at) if task.completed_at else "0s",
                    "errors": task.errors[:50]
                }
                yield f"event: complete\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
                break
            
            elif task.status == ImportStatus.FAILED:
                # 发送错误事件
                error_msg = task.errors[-1].get("message", "未知错误") if task.errors else "未知错误"
                yield f"event: error\ndata: {json.dumps({'message': error_msg}, ensure_ascii=False)}\n\n"
                break
            
            elif task.status == ImportStatus.RUNNING:
                # 发送进度事件
                if task.processed_rows != last_processed:
                    last_processed = task.processed_rows
                    total = task.total_rows or 1
                    progress = {
                        "current": task.processed_rows,
                        "total": total,
                        "success": task.success_count,
                        "failed": task.failed_count,
                        "skipped": task.skipped_count,
                        "percentage": int(task.processed_rows / total * 100)
                    }
                    yield f"event: progress\ndata: {json.dumps(progress, ensure_ascii=False)}\n\n"
            
            await asyncio.sleep(0.5)  # 每0.5秒检查一次
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/import/status/{task_id}")
def get_import_status(task_id: str):
    """获取导入任务状态（非SSE方式）
    
    返回当前任务状态，用于轮询
    包含子集生成进度信息
    """
    task = import_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    total = task.total_rows or 1
    
    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "status": task.status.value,
            "current": task.processed_rows,
            "total": task.total_rows,
            "success": task.success_count,
            "failed": task.failed_count,
            "skipped": task.skipped_count,
            "percentage": int(task.processed_rows / total * 100) if task.total_rows > 0 else 0,
            "errors": task.errors[:50] if task.status in [ImportStatus.COMPLETED, ImportStatus.FAILED] else [],
            # 新增：子集生成进度
            "episode_generation_status": getattr(task, 'episode_generation_status', ''),
            "episode_generation_progress": getattr(task, 'episode_generation_progress', 0)
        }
    }
