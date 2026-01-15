from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
import pymysql
import pandas as pd
import json
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
    """根据客户配置创建子集数据"""
    if total_episodes <= 0:
        return
    
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    abbr = get_pinyin_abbr(media_name)
    content_type = data.get('category_level1_henan') or data.get('category_level1') or ''
    content_dir = get_content_dir(content_type, customer_code)
    
    for episode_num in range(1, total_episodes + 1):
        episode_name = f"{media_name}第{episode_num:02d}集"
        
        # 尝试从扫描结果匹配时长和文件大小
        cursor.execute(
            "SELECT duration_formatted, size_bytes FROM video_scan_result WHERE standard_episode_name = %s LIMIT 1",
            (episode_name,)
        )
        match = cursor.fetchone()
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
                episode_props[col_name] = ''  # MD5需要单独计算
            elif col_config.get('type') == 'episode_name_format':
                fmt = col_config.get('format', '{drama_name}第{ep}集')
                episode_props[col_name] = fmt.format(drama_name=media_name, ep=episode_num)
        
        cursor.execute(
            "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
            (drama_id, episode_name, json.dumps(episode_props, ensure_ascii=False))
        )


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


def _update_drama_for_customer(cursor, drama_id, data, media_name, customer_code):
    """更新指定客户的剧头和子集"""
    # 更新剧头
    dynamic_props = _build_drama_props_for_customer(data, media_name, customer_code)
    cursor.execute(
        "UPDATE drama_main SET drama_name = %s, dynamic_properties = %s WHERE drama_id = %s",
        (media_name, json.dumps(dynamic_props, ensure_ascii=False), drama_id)
    )
    
    # 重建子集
    cursor.execute("DELETE FROM drama_episode WHERE drama_id = %s", (drama_id,))
    total_episodes = int(data.get('episode_count') or 0)
    _create_episodes_for_customer(cursor, drama_id, media_name, total_episodes, data, customer_code)


def _delete_drama_and_episodes(cursor, drama_id):
    """删除剧头及其子集"""
    cursor.execute("DELETE FROM drama_episode WHERE drama_id = %s", (drama_id,))
    cursor.execute("DELETE FROM drama_main WHERE drama_id = %s", (drama_id,))


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
    """导出所有版权方数据为Excel文件"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM copyright_content ORDER BY id")
            items = cursor.fetchall()
        
        export_data = []
        for item in items:
            row = {}
            for db_col, cn_col in COPYRIGHT_EXPORT_COLUMNS.items():
                row[cn_col] = item.get(db_col, '')
            export_data.append(row)
        
        df = pd.DataFrame(export_data, columns=list(COPYRIGHT_EXPORT_COLUMNS.values()))
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='版权方数据', index=False)
            
            sheet = writer.book['版权方数据']
            sheet.row_dimensions[1].height = 30
            for idx, col in enumerate(df.columns, 1):
                col_letter = get_column_letter(idx)
                col_width = sum(2 if ord(c) > 127 else 1 for c in str(col))
                max_width = col_width
                for row_idx, value in enumerate(df[col], 2):
                    if value is not None:
                        data_width = sum(2 if ord(c) > 127 else 1 for c in str(value))
                        max_width = max(max_width, min(data_width, 50))
                        sheet.cell(row=row_idx, column=idx).alignment = Alignment(vertical='center')
                sheet.cell(row=1, column=idx).alignment = Alignment(vertical='center', horizontal='center')
                sheet.column_dimensions[col_letter].width = max_width * 1.2 + 2
        
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
    if 'media_name' not in data or not data['media_name']:
        raise HTTPException(status_code=400, detail="介质名称不能为空")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            media_name = data['media_name']
            
            # 1. 为所有启用的客户创建剧头和子集
            enabled_customers = get_enabled_customers()
            drama_ids = {}
            
            for customer_code in enabled_customers:
                drama_id = _create_drama_for_customer(cursor, data, media_name, customer_code)
                drama_ids[customer_code] = drama_id
            
            conn.commit()
            
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
            conn.commit()
            
            return {
                "code": 200, "message": "创建成功",
                "data": {
                    "copyright_id": cursor.lastrowid,
                    "drama_ids": drama_ids,
                    "customers_count": len(drama_ids)
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{item_id}")
async def update_copyright(item_id: int, data: Dict[str, Any] = Body(...)):
    """更新版权方数据，并同步更新所有关联的剧集和子集"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("SELECT * FROM copyright_content WHERE id = %s", (item_id,))
            item = cursor.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail="数据不存在")
            
            # 1. 更新版权方表
            update_parts, update_values = [], []
            for field in COPYRIGHT_FIELDS:
                if field in data:
                    update_parts.append(f"{field} = %s")
                    update_values.append(data[field])
            
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
            
            # 4. 更新所有已存在的客户剧头
            for customer_code, drama_id in drama_ids.items():
                if drama_id:
                    _update_drama_for_customer(cursor, drama_id, merged_data, media_name, customer_code)
            
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
            
            conn.commit()
            
            return {"code": 200, "message": "更新成功", "data": {"id": item_id, "drama_ids": drama_ids}}
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
            
            cursor.execute("SELECT id, drama_ids FROM copyright_content WHERE id = %s", (item_id,))
            item = cursor.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail="数据不存在")
            
            # 获取所有关联的 drama_ids
            drama_ids_raw = item.get('drama_ids')
            if isinstance(drama_ids_raw, str):
                drama_ids = json.loads(drama_ids_raw) if drama_ids_raw else {}
            elif isinstance(drama_ids_raw, dict):
                drama_ids = drama_ids_raw
            else:
                drama_ids = {}
            
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-generate/{customer_code}")
async def batch_generate_for_customer(customer_code: str):
    """为指定客户批量生成所有版权数据的剧头/子集（用于新增客户时补全）"""
    if customer_code not in CUSTOMER_CONFIGS:
        raise HTTPException(status_code=400, detail=f"未知的客户代码: {customer_code}")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("SELECT * FROM copyright_content")
            all_copyrights = cursor.fetchall()
            
            generated_count = 0
            skipped_count = 0
            batch_size = 50  # 每50条提交一次
            
            for i, copyright_data in enumerate(all_copyrights):
                # 转换 Decimal 类型
                copyright_data = _convert_row(copyright_data)
                
                # 获取现有的 drama_ids
                drama_ids_raw = copyright_data.get('drama_ids')
                if isinstance(drama_ids_raw, str):
                    drama_ids = json.loads(drama_ids_raw) if drama_ids_raw else {}
                elif isinstance(drama_ids_raw, dict):
                    drama_ids = drama_ids_raw
                else:
                    drama_ids = {}
                
                # 检查该客户是否已有剧头
                if customer_code in drama_ids and drama_ids[customer_code]:
                    skipped_count += 1
                    continue
                
                # 为该客户生成剧头+子集
                media_name = copyright_data.get('media_name')
                drama_id = _create_drama_for_customer(cursor, copyright_data, media_name, customer_code)
                drama_ids[customer_code] = drama_id
                
                # 更新关联关系
                cursor.execute(
                    "UPDATE copyright_content SET drama_ids = %s WHERE id = %s",
                    (json.dumps(drama_ids), copyright_data['id'])
                )
                generated_count += 1
                
                # 分批提交
                if generated_count % batch_size == 0:
                    conn.commit()
            
            conn.commit()
            
            return {
                "code": 200,
                "message": f"已为 {CUSTOMER_CONFIGS[customer_code]['name']} 生成 {generated_count} 条剧头数据，跳过 {skipped_count} 条已存在数据"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
