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
    get_image_url, get_media_url, format_duration, format_datetime
)
from config import COPYRIGHT_FIELDS, CUSTOMER_CONFIGS, get_enabled_customers
from models import CopyrightCreate, CopyrightUpdate, CopyrightResponse

router = APIRouter(prefix="/api/copyright", tags=["版权管理"])


def _convert_decimal(obj):
    """将 Decimal 转换为 float，用于 JSON 序列化"""
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def _convert_row(row):
    """转换数据库行中的 Decimal 类型"""
    if not row:
        return row
    return {k: _convert_decimal(v) for k, v in row.items()}


# 导出 Excel 的列名映射
COPYRIGHT_EXPORT_COLUMNS = {
    'id': '序号',
    'upstream_copyright': '上游版权方',
    'media_name': '介质名称',
    'category_level1': '一级分类',
    'category_level2': '二级分类',
    'category_level1_henan': '一级分类-河南',
    'category_level2_henan': '二级分类-河南',
    'episode_count': '集数',
    'single_episode_duration': '单集时长',
    'total_duration': '总时长',
    'production_year': '出品年代',
    'production_region': '出品地区',
    'language': '语言',
    'language_henan': '语言-河南',
    'country': '国家',
    'director': '导演',
    'screenwriter': '编剧',
    'cast_members': '主演',
    'recommendation': '推荐语',
    'synopsis': '简介',
    'keywords': '关键词',
    'video_quality': '视频质量',
    'license_number': '许可证号',
    'rating': '评分',
    'exclusive_status': '独家状态',
    'copyright_start_date': '版权开始日期',
    'copyright_end_date': '版权结束日期',
    'category_level2_shandong': '二级分类-山东',
    'authorization_region': '授权区域',
    'authorization_platform': '授权平台',
    'cooperation_mode': '合作方式'
}


# ============================================================
# 多客户剧头/子集生成函数
# ============================================================

def _build_drama_props_for_customer(data, media_name, customer_code):
    """根据客户配置构建剧头动态属性"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    abbr = get_pinyin_abbr(media_name)
    props = {}
    
    for col_config in config.get('drama_columns', []):
        col_name = col_config['col']
        
        # 跳过数据库字段（drama_id, drama_name）
        if 'field' in col_config:
            continue
        
        # 固定值
        if 'value' in col_config:
            props[col_name] = col_config['value']
        # 从版权数据取值
        elif 'source' in col_config:
            value = _convert_decimal(data.get(col_config['source']))
            if value is None or value == '':
                value = col_config.get('default', '')
            # 处理后缀
            if value and col_config.get('suffix'):
                value = str(value) + col_config['suffix']
            # 处理日期格式
            if col_config.get('format') == 'datetime':
                value = format_datetime(value)
            props[col_name] = value
        # 特殊类型
        elif col_config.get('type') == 'image':
            image_type = col_config.get('image_type', 'vertical')
            props[col_name] = get_image_url(abbr, image_type, customer_code)
        elif col_config.get('type') == 'product_category':
            content_type = data.get('category_level1_henan') or data.get('category_level1') or ''
            props[col_name] = get_product_category(content_type, customer_code)
        elif col_config.get('type') == 'is_multi_episode':
            total = int(data.get('episode_count') or 0)
            props[col_name] = 1 if total > 1 else 0
        elif col_config.get('type') == 'total_duration_seconds':
            # 计算总时长（秒）
            props[col_name] = int(_convert_decimal(data.get('total_duration')) or 0)
        elif col_config.get('type') == 'pinyin_abbr':
            props[col_name] = abbr
        elif col_config.get('type') == 'sequence':
            props[col_name] = None  # 序号在导出时生成
    
    return props


def _create_episodes_for_customer(cursor, drama_id, media_name, total_episodes, data, customer_code):
    """根据客户配置创建子集数据（使用批量插入）"""
    if total_episodes <= 0:
        return 0
    
    return _batch_create_episodes(cursor, drama_id, media_name, 1, total_episodes, data, customer_code)


def _create_drama_for_customer(cursor, data, media_name, customer_code):
    """为指定客户创建剧头和子集，返回drama_id"""
    # 创建剧头
    dynamic_props = _build_drama_props_for_customer(data, media_name, customer_code)
    cursor.execute(
        "INSERT INTO drama_main (customer_code, drama_name, dynamic_properties) VALUES (%s, %s, %s)",
        (customer_code, media_name, json.dumps(dynamic_props, ensure_ascii=False))
    )
    drama_id = cursor.lastrowid
    
    # 创建子集
    total_episodes = int(data.get('episode_count') or 0)
    _create_episodes_for_customer(cursor, drama_id, media_name, total_episodes, data, customer_code)
    
    return drama_id


def _update_drama_for_customer(
    cursor, 
    drama_id: int, 
    data: dict, 
    media_name: str, 
    customer_code: str,
    old_episode_count: int = None,
    old_media_name: str = None
) -> dict:
    """更新指定客户的剧头和子集（增量更新）
    
    Args:
        cursor: 数据库游标
        drama_id: 剧头ID
        data: 版权数据
        media_name: 新介质名称
        customer_code: 客户代码
        old_episode_count: 原集数（如果为None则从数据库查询）
        old_media_name: 原介质名称（如果为None则不检测名称变化）
    
    Returns:
        dict: 包含操作统计信息
    """
    stats = {'added': 0, 'deleted': 0, 'updated': 0}
    
    # 更新剧头
    dynamic_props = _build_drama_props_for_customer(data, media_name, customer_code)
    cursor.execute(
        "UPDATE drama_main SET drama_name = %s, dynamic_properties = %s WHERE drama_id = %s",
        (media_name, json.dumps(dynamic_props, ensure_ascii=False), drama_id)
    )
    
    # 获取原集数（如果未提供）
    if old_episode_count is None:
        old_episode_count = _get_current_episode_count(cursor, drama_id)
    
    new_episode_count = int(data.get('episode_count') or 0)
    
    # 检测介质名称变化
    if old_media_name and old_media_name != media_name:
        # 介质名称变化，更新所有子集的属性
        updated = _update_episode_properties(
            cursor, drama_id, old_media_name, media_name, data, customer_code
        )
        stats['updated'] = updated
    
    # 增量更新子集
    episode_stats = _update_episodes_incremental(
        cursor, drama_id, old_episode_count, new_episode_count,
        media_name, data, customer_code
    )
    stats['added'] = episode_stats['added']
    stats['deleted'] = episode_stats['deleted']
    
    return stats


def _delete_drama_and_episodes(cursor, drama_id):
    """删除剧头及其子集"""
    cursor.execute("DELETE FROM drama_episode WHERE drama_id = %s", (drama_id,))
    cursor.execute("DELETE FROM drama_main WHERE drama_id = %s", (drama_id,))


def _get_current_episode_count(cursor, drama_id: int) -> int:
    """获取指定剧头的当前子集数量
    
    Args:
        cursor: 数据库游标
        drama_id: 剧头ID
    
    Returns:
        int: 子集数量
    """
    cursor.execute("SELECT COUNT(*) as count FROM drama_episode WHERE drama_id = %s", (drama_id,))
    result = cursor.fetchone()
    return result['count'] if result else 0


def _update_episodes_incremental(
    cursor, 
    drama_id: int, 
    old_count: int, 
    new_count: int, 
    media_name: str, 
    data: dict, 
    customer_code: str
) -> dict:
    """增量更新子集数据
    
    Args:
        cursor: 数据库游标
        drama_id: 剧头ID
        old_count: 原集数
        new_count: 新集数
        media_name: 介质名称
        data: 版权数据
        customer_code: 客户代码
    
    Returns:
        dict: 包含 added, deleted, updated 数量的统计信息
    """
    stats = {'added': 0, 'deleted': 0, 'updated': 0}
    
    if old_count == new_count:
        # 集数不变，不操作子集表
        return stats
    elif old_count < new_count:
        # 集数增加，追加新子集
        added = _batch_create_episodes(
            cursor, drama_id, media_name, 
            old_count + 1, new_count, 
            data, customer_code
        )
        stats['added'] = added
    else:
        # 集数减少，删除多余子集
        cursor.execute(
            """DELETE FROM drama_episode 
               WHERE drama_id = %s 
               AND JSON_EXTRACT(dynamic_properties, '$.集数') > %s""",
            (drama_id, new_count)
        )
        stats['deleted'] = old_count - new_count
    
    return stats


def _batch_create_episodes(
    cursor,
    drama_id: int,
    media_name: str,
    start_episode: int,
    end_episode: int,
    data: dict,
    customer_code: str
) -> int:
    """批量创建子集数据
    
    Args:
        cursor: 数据库游标
        drama_id: 剧头ID
        media_name: 介质名称
        start_episode: 起始集数（包含）
        end_episode: 结束集数（包含）
        data: 版权数据
        customer_code: 客户代码
    
    Returns:
        int: 创建的子集数量
    """
    if start_episode > end_episode:
        return 0
    
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    abbr = get_pinyin_abbr(media_name)
    content_type = data.get('category_level1_henan') or data.get('category_level1') or ''
    content_dir = get_content_dir(content_type, customer_code)
    
    # 批量查询所有需要的扫描结果
    episode_names = [f"{media_name}第{ep:02d}集" for ep in range(start_episode, end_episode + 1)]
    placeholders = ','.join(['%s'] * len(episode_names))
    cursor.execute(
        f"SELECT standard_episode_name, duration_formatted, size_bytes FROM video_scan_result WHERE standard_episode_name IN ({placeholders})",
        episode_names
    )
    scan_results = {row['standard_episode_name']: row for row in cursor.fetchall()}
    
    # 构建批量插入数据
    insert_data = []
    for episode_num in range(start_episode, end_episode + 1):
        episode_name = f"{media_name}第{episode_num:02d}集"
        
        # 从扫描结果获取时长和文件大小
        match = scan_results.get(episode_name)
        duration = match['duration_formatted'] if match and match.get('duration_formatted') else 0
        file_size = int(match['size_bytes']) if match and match.get('size_bytes') else 0
        
        # 构建子集动态属性
        episode_props = {}
        for col_config in config.get('episode_columns', []):
            col_name = col_config['col']
            
            if 'field' in col_config:
                continue
            
            if 'value' in col_config:
                episode_props[col_name] = col_config['value']
            elif col_config.get('type') == 'media_url':
                episode_props[col_name] = get_media_url(abbr, episode_num, content_dir, customer_code)
            elif col_config.get('type') == 'episode_num':
                episode_props[col_name] = episode_num
            elif col_config.get('type') == 'duration':
                episode_props[col_name] = duration
            elif col_config.get('type') == 'duration_minutes':
                episode_props[col_name] = format_duration(duration, 'minutes') if duration else 0
            elif col_config.get('type') == 'duration_hhmmss':
                episode_props[col_name] = format_duration(duration, 'HH:MM:SS') if duration else '00:00:00'
            elif col_config.get('type') == 'file_size':
                episode_props[col_name] = file_size
            elif col_config.get('type') == 'md5':
                episode_props[col_name] = ''
            elif col_config.get('type') == 'episode_name_format':
                fmt = col_config.get('format', '{drama_name}第{ep}集')
                episode_props[col_name] = fmt.format(drama_name=media_name, ep=episode_num)
        
        insert_data.append((drama_id, episode_name, json.dumps(episode_props, ensure_ascii=False)))
    
    # 批量插入
    if insert_data:
        cursor.executemany(
            "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
            insert_data
        )
    
    return len(insert_data)


def _update_episode_properties(
    cursor,
    drama_id: int,
    old_media_name: str,
    new_media_name: str,
    data: dict,
    customer_code: str
) -> int:
    """更新所有子集的动态属性（当介质名称变化时）
    
    Args:
        cursor: 数据库游标
        drama_id: 剧头ID
        old_media_name: 原介质名称
        new_media_name: 新介质名称
        data: 版权数据
        customer_code: 客户代码
    
    Returns:
        int: 更新的子集数量
    """
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    old_abbr = get_pinyin_abbr(old_media_name)
    new_abbr = get_pinyin_abbr(new_media_name)
    content_type = data.get('category_level1_henan') or data.get('category_level1') or ''
    content_dir = get_content_dir(content_type, customer_code)
    
    # 获取所有子集
    cursor.execute(
        "SELECT episode_id, episode_name, dynamic_properties FROM drama_episode WHERE drama_id = %s",
        (drama_id,)
    )
    episodes = cursor.fetchall()
    
    if not episodes:
        return 0
    
    # 批量更新数据
    update_data = []
    for ep in episodes:
        # 从旧的 episode_name 提取集数
        old_ep_name = ep['episode_name']
        # 尝试从名称中提取集数，格式如 "介质名称第01集"
        episode_num = 1
        if old_ep_name and '第' in old_ep_name and '集' in old_ep_name:
            try:
                num_str = old_ep_name.split('第')[-1].split('集')[0]
                episode_num = int(num_str)
            except (ValueError, IndexError):
                pass
        
        # 新的 episode_name
        new_ep_name = f"{new_media_name}第{episode_num:02d}集"
        
        # 更新动态属性中的媒体地址
        props = json.loads(ep['dynamic_properties']) if ep['dynamic_properties'] else {}
        for col_config in config.get('episode_columns', []):
            col_name = col_config['col']
            if col_config.get('type') == 'media_url':
                props[col_name] = get_media_url(new_abbr, episode_num, content_dir, customer_code)
            elif col_config.get('type') == 'episode_name_format':
                fmt = col_config.get('format', '{drama_name}第{ep}集')
                props[col_name] = fmt.format(drama_name=new_media_name, ep=episode_num)
        
        update_data.append((new_ep_name, json.dumps(props, ensure_ascii=False), ep['episode_id']))
    
    # 批量更新
    if update_data:
        cursor.executemany(
            "UPDATE drama_episode SET episode_name = %s, dynamic_properties = %s WHERE episode_id = %s",
            update_data
        )
    
    return len(update_data)


# ============================================================
# API 路由
# ============================================================

@router.get("")
async def get_copyright_list(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取版权方数据列表"""
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
            
            return {
                "code": 200, "message": "success",
                "data": {"list": items, "total": total, "page": page, "page_size": page_size,
                        "total_pages": (total + page_size - 1) // page_size}
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_copyright_to_excel():
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
            
            # 设置列宽（固定宽度，不逐单元格计算）
            col_widths = {
                '序号': 8, '上游版权方': 15, '介质名称': 25, '一级分类': 10, '二级分类': 10,
                '一级分类-河南': 12, '二级分类-河南': 12, '集数': 8, '单集时长': 10, '总时长': 10,
                '出品年代': 10, '出品地区': 10, '语言': 10, '语言-河南': 10, '国家': 10,
                '导演': 15, '编剧': 15, '主演': 20, '推荐语': 30, '简介': 40,
                '关键词': 20, '视频质量': 10, '许可证号': 15, '评分': 8, '独家状态': 10,
                '版权开始日期': 15, '版权结束日期': 15, '二级分类-山东': 15,
                '授权区域': 12, '授权平台': 12, '合作方式': 12
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
async def get_customer_list():
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
async def get_copyright_detail(item_id: int):
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
async def create_copyright(data: Dict[str, Any] = Body(...)):
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
async def update_copyright(item_id: int, data: Dict[str, Any] = Body(...)):
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
async def delete_copyright(item_id: int):
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
async def execute_import(task_id: str, background_tasks: BackgroundTasks):
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
async def get_import_status(task_id: str):
    """获取导入任务状态（非SSE方式）
    
    返回当前任务状态，用于轮询
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
            "errors": task.errors[:50] if task.status in [ImportStatus.COMPLETED, ImportStatus.FAILED] else []
        }
    }
