from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any
import pymysql
import json

from database import get_db
from utils import get_pinyin_abbr, get_content_dir, get_product_category
from config import COPYRIGHT_FIELDS

router = APIRouter(prefix="/api/copyright", tags=["版权管理"])


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


def _build_drama_props(data, media_name):
    """构建剧头动态属性"""
    content_type = data.get('category_level1_henan') or "电视剧"
    abbr = get_pinyin_abbr(media_name)
    
    return {
        '作者列表': data.get('director') or "暂无",
        '清晰度': 1,
        '语言': data.get('language_henan') or data.get('language') or "简体中文",
        '主演': data.get('cast_members') or "",
        '内容类型': content_type,
        '上映年份': int(data['production_year']) if data.get('production_year') else None,
        '关键字': data.get('keywords') or "",
        '评分': float(data['rating']) if data.get('rating') else None,
        '推荐语': data.get('recommendation') or "",
        '总集数': int(data['episode_count']) if data.get('episode_count') else 0,
        '产品分类': get_product_category(content_type),
        '竖图': f"http://36.133.168.235:18181/img/{abbr}_st.jpg",
        '描述': data.get('synopsis') or "",
        '横图': f"http://36.133.168.235:18181/img/{abbr}_ht.jpg",
        '版权': 1,
        '二级分类': data.get('category_level2_henan') or ""
    }


def _create_episodes(cursor, drama_id, media_name, total_episodes, content_type):
    """创建子集数据"""
    if total_episodes <= 0:
        return
    
    abbr = get_pinyin_abbr(media_name)
    content_dir = get_content_dir(content_type)
    
    for episode_num in range(1, total_episodes + 1):
        episode_name = f"{media_name}第{episode_num:02d}集"
        media_url = f"ftp://ftpmediazjyd:rD2q0y1M5eI@36.133.168.235:2121/media/hnyd/{content_dir}/{abbr}/{abbr}{episode_num:03d}.ts"
        
        cursor.execute(
            "SELECT duration_formatted, size_bytes FROM video_scan_result WHERE standard_episode_name = %s LIMIT 1",
            (episode_name,)
        )
        match = cursor.fetchone()
        duration = match['duration_formatted'] if match and match['duration_formatted'] else 0
        file_size = int(match['size_bytes']) if match and match['size_bytes'] else 0
        
        episode_props = {
            '媒体拉取地址': media_url, '媒体类型': 1, '编码格式': 1,
            '集数': episode_num, '时长': duration, '文件大小': file_size
        }
        cursor.execute(
            "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
            (drama_id, episode_name, json.dumps(episode_props, ensure_ascii=False))
        )


@router.post("")
async def create_copyright(data: Dict[str, Any] = Body(...)):
    """创建版权方数据，并自动创建对应的剧头和子集"""
    if 'media_name' not in data or not data['media_name']:
        raise HTTPException(status_code=400, detail="介质名称不能为空")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            media_name = data['media_name']
            
            # 1. 创建剧头
            dynamic_props = _build_drama_props(data, media_name)
            cursor.execute(
                "INSERT INTO drama_main (customer_id, drama_name, dynamic_properties) VALUES (NULL, %s, %s)",
                (media_name, json.dumps(dynamic_props, ensure_ascii=False))
            )
            conn.commit()
            new_drama_id = cursor.lastrowid
            
            # 2. 创建子集
            total_episodes = int(data['episode_count']) if data.get('episode_count') else 0
            content_type = data.get('category_level1_henan') or "电视剧"
            _create_episodes(cursor, new_drama_id, media_name, total_episodes, content_type)
            conn.commit()
            
            # 3. 插入版权方数据
            insert_fields, insert_values = ['drama_id'], [new_drama_id]
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
                "data": {"copyright_id": cursor.lastrowid, "drama_id": new_drama_id, "episodes_created": total_episodes}
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{item_id}")
async def update_copyright(item_id: int, data: Dict[str, Any] = Body(...)):
    """更新版权方数据，并同步更新关联的剧集和子集"""
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
                conn.commit()
            
            # 2. 同步更新剧集
            drama_id = item.get('drama_id')
            if drama_id:
                merged_data = dict(item)
                merged_data.update(data)
                media_name = merged_data.get('media_name')
                
                dynamic_props = _build_drama_props(merged_data, media_name)
                cursor.execute(
                    "UPDATE drama_main SET drama_name = %s, dynamic_properties = %s WHERE drama_id = %s",
                    (media_name, json.dumps(dynamic_props, ensure_ascii=False), drama_id)
                )
                conn.commit()
                
                # 3. 重建子集
                total_episodes = int(merged_data['episode_count']) if merged_data.get('episode_count') else 0
                if total_episodes > 0:
                    cursor.execute("DELETE FROM drama_episode WHERE drama_id = %s", (drama_id,))
                    content_type = merged_data.get('category_level1_henan') or "电视剧"
                    _create_episodes(cursor, drama_id, media_name, total_episodes, content_type)
                    conn.commit()
            
            return {"code": 200, "message": "更新成功", "data": {"id": item_id, "drama_id": drama_id}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{item_id}")
async def delete_copyright(item_id: int):
    """删除版权方数据及关联的剧集和子集"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("SELECT id, drama_id FROM copyright_content WHERE id = %s", (item_id,))
            item = cursor.fetchone()
            if not item:
                raise HTTPException(status_code=404, detail="数据不存在")
            
            drama_id = item.get('drama_id')
            if drama_id:
                cursor.execute("DELETE FROM drama_episode WHERE drama_id = %s", (drama_id,))
                cursor.execute("DELETE FROM drama_main WHERE drama_id = %s", (drama_id,))
            
            cursor.execute("DELETE FROM copyright_content WHERE id = %s", (item_id,))
            conn.commit()
            
            return {"code": 200, "message": "删除成功", "data": {"id": item_id, "drama_id": drama_id}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
