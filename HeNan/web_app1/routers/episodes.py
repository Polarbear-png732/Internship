from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
import pymysql
import json

from database import get_db
from utils import build_episode_dict
from config import EPISODE_DYNAMIC_FIELDS

router = APIRouter(prefix="/api/dramas", tags=["子集管理"])


@router.get("/{drama_id}/episodes")
async def get_drama_episodes(drama_id: int):
    """获取剧集的子集列表"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id", (drama_id,))
            episodes = cursor.fetchall()
            return {"code": 200, "message": "success", "data": [build_episode_dict(ep) for ep in episodes]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{drama_id}/episodes")
async def create_episode(drama_id: int, episode_data: Dict[str, Any] = Body(...)):
    """创建子集"""
    if '节目名称' not in episode_data or not episode_data['节目名称']:
        raise HTTPException(status_code=400, detail="节目名称不能为空")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM drama_main WHERE drama_id = %s", (drama_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="剧集不存在")
            
            episode_name = episode_data['节目名称']
            dynamic_props = {f: episode_data[f] for f in EPISODE_DYNAMIC_FIELDS if f in episode_data}
            
            cursor.execute(
                "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
                (drama_id, episode_name, json.dumps(dynamic_props, ensure_ascii=False) if dynamic_props else None)
            )
            conn.commit()
            return {"code": 200, "message": "创建成功", "data": {"episode_id": cursor.lastrowid}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{drama_id}/episodes/{episode_id}")
async def update_episode(drama_id: int, episode_id: int, episode_data: Dict[str, Any] = Body(...)):
    """更新子集"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM drama_episode WHERE episode_id = %s AND drama_id = %s", (episode_id, drama_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="子集不存在")
            
            dynamic_props = {f: episode_data[f] for f in EPISODE_DYNAMIC_FIELDS if f in episode_data}
            update_fields, update_values = [], []
            
            if '节目名称' in episode_data:
                update_fields.append("episode_name = %s")
                update_values.append(episode_data['节目名称'])
            if dynamic_props:
                update_fields.append("dynamic_properties = %s")
                update_values.append(json.dumps(dynamic_props, ensure_ascii=False))
            
            if update_fields:
                update_values.append(episode_id)
                cursor.execute(f"UPDATE drama_episode SET {', '.join(update_fields)} WHERE episode_id = %s", update_values)
                conn.commit()
            
            return {"code": 200, "message": "更新成功", "data": {"episode_id": episode_id}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{drama_id}/episodes/{episode_id}")
async def delete_episode(drama_id: int, episode_id: int):
    """删除子集"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM drama_episode WHERE episode_id = %s AND drama_id = %s", (episode_id, drama_id))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="子集不存在")
            
            cursor.execute("DELETE FROM drama_episode WHERE episode_id = %s", (episode_id,))
            conn.commit()
            return {"code": 200, "message": "删除成功", "data": {"episode_id": episode_id}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
