from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
import pymysql
import pandas as pd
import json
from io import BytesIO
from urllib.parse import quote
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

from database import get_db
from utils import parse_json, build_drama_dict, build_episode_dict
from config import DRAMA_HEADER_COLUMNS, SUBSET_COLUMNS, DRAMA_DYNAMIC_FIELDS

router = APIRouter(prefix="/api/dramas", tags=["剧集管理"])


@router.get("")
async def get_dramas(
    customer_id: Optional[int] = Query(None, description="客户ID"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取剧集列表"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            where_conditions, params = [], []
            if customer_id:
                where_conditions.append("customer_id = %s")
                params.append(customer_id)
            if keyword:
                where_conditions.append("drama_name LIKE %s")
                params.append(f"%{keyword}%")
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            cursor.execute(f"SELECT COUNT(*) as total FROM drama_main {where_clause}", params)
            total = cursor.fetchone()['total']
            
            offset = (page - 1) * page_size
            cursor.execute(f"""
                SELECT drama_id, customer_id, drama_name, dynamic_properties, created_at, updated_at
                FROM drama_main {where_clause} ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, params + [page_size, offset])
            dramas = cursor.fetchall()
            
            for drama in dramas:
                drama['dynamic_properties'] = parse_json(drama)
            
            return {
                "code": 200, "message": "success",
                "data": {
                    "list": dramas, "total": total, "page": page,
                    "page_size": page_size, "total_pages": (total + page_size - 1) // page_size
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-name")
async def get_drama_by_name(name: str = Query(..., description="剧集名称")):
    """根据剧集名称获取剧集详情（包含子集）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("SELECT * FROM drama_main WHERE drama_name = %s", (name,))
            drama = cursor.fetchone()
            if not drama:
                raise HTTPException(status_code=404, detail="未找到该剧集")
            
            header_dict = build_drama_dict(drama)
            
            cursor.execute("SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id", (drama['drama_id'],))
            episodes = cursor.fetchall()
            
            episode_list = []
            for i, episode in enumerate(episodes, 1):
                ep_data = build_episode_dict(episode)
                ep_data['子集id'] = i
                episode_list.append(ep_data)
            
            return {"code": 200, "message": "success", "data": {"header": header_dict, "episodes": episode_list}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{drama_id}")
async def get_drama_detail(drama_id: int):
    """获取剧集详细信息"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM drama_main WHERE drama_id = %s", (drama_id,))
            drama = cursor.fetchone()
            if not drama:
                raise HTTPException(status_code=404, detail="剧集不存在")
            return {"code": 200, "message": "success", "data": build_drama_dict(drama)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_drama(drama_data: Dict[str, Any] = Body(...)):
    """创建剧头"""
    if '剧集名称' not in drama_data or not drama_data['剧集名称']:
        raise HTTPException(status_code=400, detail="剧集名称不能为空")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            drama_name = drama_data['剧集名称']
            customer_id = drama_data.get('customer_id')
            dynamic_props = {f: drama_data[f] for f in DRAMA_DYNAMIC_FIELDS if f in drama_data}
            
            cursor.execute(
                "INSERT INTO drama_main (customer_id, drama_name, dynamic_properties) VALUES (%s, %s, %s)",
                (customer_id, drama_name, json.dumps(dynamic_props, ensure_ascii=False) if dynamic_props else None)
            )
            conn.commit()
            return {"code": 200, "message": "创建成功", "data": {"drama_id": cursor.lastrowid}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{drama_id}")
async def delete_drama(drama_id: int):
    """删除剧头"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT drama_id FROM drama_main WHERE drama_id = %s", (drama_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="剧集不存在")
            cursor.execute("DELETE FROM drama_main WHERE drama_id = %s", (drama_id,))
            conn.commit()
            return {"code": 200, "message": "删除成功", "data": {"drama_id": drama_id}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{drama_id}")
async def update_drama(drama_id: int, drama_data: Dict[str, Any] = Body(...)):
    """更新剧集信息"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT drama_id FROM drama_main WHERE drama_id = %s", (drama_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="剧集不存在")
            
            dynamic_props = {f: drama_data[f] for f in DRAMA_DYNAMIC_FIELDS if f in drama_data}
            update_fields, update_values = [], []
            
            if '剧集名称' in drama_data:
                update_fields.append("drama_name = %s")
                update_values.append(drama_data['剧集名称'])
            if dynamic_props:
                update_fields.append("dynamic_properties = %s")
                update_values.append(json.dumps(dynamic_props, ensure_ascii=False))
            
            if not update_fields:
                return {"code": 400, "message": "没有提供要更新的字段", "data": None}
            
            update_values.append(drama_id)
            cursor.execute(f"UPDATE drama_main SET {', '.join(update_fields)} WHERE drama_id = %s", update_values)
            conn.commit()
            return {"code": 200, "message": "更新成功", "data": {"drama_id": drama_id}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{drama_id}/export")
async def export_drama_to_excel(drama_id: int):
    """导出剧集数据为Excel文件"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM drama_main WHERE drama_id = %s", (drama_id,))
            drama = cursor.fetchone()
            if not drama:
                raise HTTPException(status_code=404, detail="剧集不存在")
            
            drama_name = drama['drama_name']
            props = parse_json(drama)
            
            header_dict = build_drama_dict(drama, props)
            header_dict['剧头id'] = ''
            header_df = pd.DataFrame([header_dict], columns=DRAMA_HEADER_COLUMNS)
            
            cursor.execute("SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id", (drama['drama_id'],))
            episodes = cursor.fetchall()
            
            episode_list = []
            for episode in episodes:
                ep_data = build_episode_dict(episode)
                ep_data['子集id'] = ''
                episode_list.append(ep_data)
            subset_df = pd.DataFrame(episode_list, columns=SUBSET_COLUMNS)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            header_df.to_excel(writer, sheet_name='剧头', index=False)
            subset_df.to_excel(writer, sheet_name='子集', index=False)
            
            workbook = writer.book
            for sheet_name, df in [('剧头', header_df), ('子集', subset_df)]:
                sheet = workbook[sheet_name]
                sheet.row_dimensions[1].height = 30
                for idx, col in enumerate(df.columns, 1):
                    col_letter = get_column_letter(idx)
                    col_width = sum(2 if ord(c) > 127 else 1 for c in str(col))
                    max_width = col_width
                    for row_idx, value in enumerate(df[col], 2):
                        if value is not None:
                            data_width = sum(2 if ord(c) > 127 else 1 for c in str(value))
                            max_width = max(max_width, data_width)
                            sheet.cell(row=row_idx, column=idx).alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
                    sheet.cell(row=1, column=idx).alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
                    sheet.column_dimensions[col_letter].width = max_width * 1.3 + 3
        
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'{drama_name}_数据.xlsx')}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
