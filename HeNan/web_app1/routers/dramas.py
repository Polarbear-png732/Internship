"""
剧集管理路由模块
提供剧头（剧集主信息）的查询、导出、编辑和删除功能
支持多客户配置驱动的字段映射和Excel导出格式定制
"""
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, List
import pymysql
import pandas as pd
import json
from io import BytesIO
from urllib.parse import quote
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

from database import get_db
from utils import parse_json, get_pinyin_abbr, get_image_url
from config import CUSTOMER_CONFIGS

# 从服务层导入
from services.drama_service import (
    JIANGSU_HEADERS, JIANGSU_COL_WIDTHS,
    build_drama_display_dict as _build_drama_display_dict,
    build_drama_display_dict_fast as _build_drama_display_dict_fast,
    build_episode_display_dict as _build_episode_display_dict,
    build_episode_display_dict_fast as _build_episode_display_dict_fast,
    get_column_names as _get_column_names,
    build_picture_data as _build_picture_data,
    build_picture_data_fast as _build_picture_data_fast,
    preprocess_dramas, preprocess_episodes, group_episodes_by_drama
)
from services.export_service import ExcelExportService

router = APIRouter(prefix="/api/dramas", tags=["剧集管理"])


@router.get("")
def get_dramas(
    customer_code: Optional[str] = Query(None, description="客户代码"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取剧集列表"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            where_conditions, params = [], []
            if customer_code:
                where_conditions.append("customer_code = %s")
                params.append(customer_code)
            if keyword:
                where_conditions.append("drama_name LIKE %s")
                params.append(f"%{keyword}%")
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            cursor.execute(f"SELECT COUNT(*) as total FROM drama_main {where_clause}", params)
            total = cursor.fetchone()['total']
            
            offset = (page - 1) * page_size
            cursor.execute(f"""
                SELECT drama_id, customer_id, customer_code, drama_name, dynamic_properties, created_at, updated_at
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
def get_drama_by_name(
    name: str = Query(..., description="剧集名称"),
    customer_code: str = Query('henan_mobile', description="客户代码")
):
    """根据剧集名称获取剧集详情（包含子集），按客户格式返回"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 查找指定客户的剧头
            cursor.execute(
                "SELECT * FROM drama_main WHERE drama_name = %s AND customer_code = %s",
                (name, customer_code)
            )
            drama = cursor.fetchone()
            
            if not drama:
                raise HTTPException(status_code=404, detail=f"未找到该剧集（客户: {customer_code}）")
            
            # 按客户格式构建剧头数据
            header_dict = _build_drama_display_dict(drama, customer_code)
            
            # 获取子集
            cursor.execute(
                "SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id",
                (drama['drama_id'],)
            )
            episodes = cursor.fetchall()
            
            # 按客户格式构建子集数据
            episode_list = []
            for i, episode in enumerate(episodes, 1):
                ep_data = _build_episode_display_dict(episode, customer_code, drama['drama_name'])
                episode_list.append(ep_data)
            
            # 获取列名配置
            drama_columns = _get_column_names(customer_code, 'drama')
            episode_columns = _get_column_names(customer_code, 'episode')
            
            return {
                "code": 200, "message": "success",
                "data": {
                    "header": header_dict,
                    "episodes": episode_list,
                    "drama_columns": drama_columns,
                    "episode_columns": episode_columns,
                    "customer_code": customer_code,
                    "customer_name": CUSTOMER_CONFIGS.get(customer_code, {}).get('name', '')
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/columns/{customer_code}")
def get_customer_columns(customer_code: str):
    """获取指定客户的列配置"""
    if customer_code not in CUSTOMER_CONFIGS:
        raise HTTPException(status_code=404, detail=f"未知的客户代码: {customer_code}")
    
    config = CUSTOMER_CONFIGS[customer_code]
    return {
        "code": 200,
        "data": {
            "customer_code": customer_code,
            "customer_name": config['name'],
            "drama_columns": _get_column_names(customer_code, 'drama'),
            "episode_columns": _get_column_names(customer_code, 'episode'),
            "export_sheets": config.get('export_sheets', ['剧头', '子集'])
        }
    }


@router.get("/{drama_id}")
def get_drama_detail(drama_id: int):
    """获取剧集详细信息"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM drama_main WHERE drama_id = %s", (drama_id,))
            drama = cursor.fetchone()
            if not drama:
                raise HTTPException(status_code=404, detail="剧集不存在")
            
            customer_code = drama.get('customer_code', 'henan_mobile')
            return {
                "code": 200, "message": "success",
                "data": _build_drama_display_dict(drama, customer_code)
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{drama_id}/export")
def export_drama_to_excel(drama_id: int):
    """导出单个剧集数据为Excel文件（按该剧集所属客户的格式）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM drama_main WHERE drama_id = %s", (drama_id,))
            drama = cursor.fetchone()
            if not drama:
                raise HTTPException(status_code=404, detail="剧集不存在")
            
            customer_code = drama.get('customer_code', 'henan_mobile')
            config = CUSTOMER_CONFIGS.get(customer_code, {})
            drama_name = drama['drama_name']
            
            # 构建剧头数据
            header_dict = _build_drama_display_dict(drama, customer_code)
            drama_columns = _get_column_names(customer_code, 'drama')
            
            # 江苏新媒体：设置序号为1，sId留空
            if customer_code == 'jiangsu_newmedia':
                header_dict['vod_no'] = 1  # 单个剧集导出，序号为1
                header_dict['sId'] = None  # sId留空
            elif drama_columns and drama_columns[0] in header_dict:
                # 其他客户：清空ID字段
                header_dict[drama_columns[0]] = ''
            
            header_df = pd.DataFrame([header_dict], columns=drama_columns)
            
            # 获取子集
            cursor.execute(
                "SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id",
                (drama['drama_id'],)
            )
            episodes = cursor.fetchall()
            
            episode_columns = _get_column_names(customer_code, 'episode')
            episode_list = []
            for i, episode in enumerate(episodes, 1):
                ep_data = _build_episode_display_dict(episode, customer_code)
                
                # 江苏新媒体：设置序号，vod_no关联剧头序号，sId和pId留空
                if customer_code == 'jiangsu_newmedia':
                    ep_data['vod_info_no'] = i  # 子集序号
                    ep_data['vod_no'] = 1       # 关联剧头序号（单个剧集导出为1）
                    ep_data['sId'] = None       # 剧头Id留空
                    ep_data['pId'] = None       # 子集Id留空
                elif episode_columns and episode_columns[0] in ep_data:
                    # 其他客户：清空ID字段
                    ep_data[episode_columns[0]] = ''
                
                episode_list.append(ep_data)
            subset_df = pd.DataFrame(episode_list, columns=episode_columns)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            header_df.to_excel(writer, sheet_name='剧头', index=False)
            subset_df.to_excel(writer, sheet_name='子集', index=False)
            
            # 江苏新媒体需要图片表
            if customer_code == 'jiangsu_newmedia':
                picture_data = _build_picture_data(drama, customer_code)
                # 填充图片序号
                for i, pic in enumerate(picture_data, 1):
                    pic['picture_no'] = i
                    pic['vod_no'] = 1  # 关联剧头序号（单个剧集导出为1）
                picture_columns = [col['col'] for col in config.get('picture_columns', [])]
                picture_df = pd.DataFrame(picture_data, columns=picture_columns)
                picture_df.to_excel(writer, sheet_name='图片', index=False)
            
            # 江苏新媒体使用特殊的两行表头格式
            if customer_code == 'jiangsu_newmedia':
                ExcelExportService.format_jiangsu_excel(writer)
            else:
                ExcelExportService.format_excel_sheets(writer, customer_code)
        
        output.seek(0)
        customer_name = config.get('name', '')
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'{drama_name}_{customer_name}.xlsx')}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/customer/{customer_code}")
def export_customer_dramas(customer_code: str):
    """导出指定客户的所有剧集数据为Excel文件（性能优化版：批量查询子集）"""
    if customer_code not in CUSTOMER_CONFIGS:
        raise HTTPException(status_code=404, detail=f"未知的客户代码: {customer_code}")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 获取该客户的所有剧头
            cursor.execute(
                "SELECT * FROM drama_main WHERE customer_code = %s ORDER BY drama_id",
                (customer_code,)
            )
            dramas = cursor.fetchall()
            
            if not dramas:
                raise HTTPException(status_code=404, detail=f"该客户暂无剧集数据")
            
            config = CUSTOMER_CONFIGS[customer_code]
            drama_columns = _get_column_names(customer_code, 'drama')
            episode_columns = _get_column_names(customer_code, 'episode')
            drama_col_configs = config.get('drama_columns', [])
            episode_col_configs = config.get('episode_columns', [])
            
            # 【性能优化】批量查询所有子集，避免 N+1 查询
            drama_ids = [d['drama_id'] for d in dramas]
            if drama_ids:
                placeholders = ','.join(['%s'] * len(drama_ids))
                cursor.execute(
                    f"SELECT * FROM drama_episode WHERE drama_id IN ({placeholders}) ORDER BY drama_id, episode_id",
                    drama_ids
                )
                all_episodes_raw = cursor.fetchall()
            else:
                all_episodes_raw = []
            
            # 【性能优化】预解析所有 JSON
            for drama in dramas:
                drama['_parsed_props'] = parse_json(drama)
                drama['_pinyin_abbr'] = get_pinyin_abbr(drama.get('drama_name', ''))
            
            for episode in all_episodes_raw:
                episode['_parsed_props'] = parse_json(episode)
            
            # 【性能优化】按 drama_id 分组子集
            episodes_by_drama = {}
            for episode in all_episodes_raw:
                drama_id = episode['drama_id']
                if drama_id not in episodes_by_drama:
                    episodes_by_drama[drama_id] = []
                episodes_by_drama[drama_id].append(episode)
            
            # 构建剧头数据
            drama_list = []
            all_episodes = []
            all_pictures = []
            
            drama_sequence = 0
            episode_sequence = 0
            picture_sequence = 0
            
            for drama in dramas:
                drama_sequence += 1
                header_dict = _build_drama_display_dict_fast(drama, customer_code, drama_col_configs)
                
                # 处理序号字段
                first_col = drama_columns[0] if drama_columns else None
                if first_col and 'vod_no' in first_col.lower() or first_col == '序号':
                    header_dict[first_col] = drama_sequence
                else:
                    header_dict[first_col] = ''
                
                # 江苏新媒体: sId字段留空
                if customer_code == 'jiangsu_newmedia' and 'sId' in header_dict:
                    header_dict['sId'] = None
                
                drama_list.append(header_dict)
                
                # 【性能优化】从预查询的数据中获取子集
                episodes = episodes_by_drama.get(drama['drama_id'], [])
                
                for episode in episodes:
                    episode_sequence += 1
                    ep_data = _build_episode_display_dict_fast(episode, customer_code, episode_col_configs)
                    
                    # 处理序号字段
                    first_ep_col = episode_columns[0] if episode_columns else None
                    if first_ep_col:
                        if 'vod_info_no' in first_ep_col.lower() or first_ep_col == '序号':
                            ep_data[first_ep_col] = episode_sequence
                        else:
                            ep_data[first_ep_col] = ''
                    
                    # 处理剧头序号关联
                    if 'vod_no' in episode_columns:
                        ep_data['vod_no'] = drama_sequence
                    
                    # 江苏新媒体: sId和pId字段留空
                    if customer_code == 'jiangsu_newmedia':
                        if 'sId' in ep_data:
                            ep_data['sId'] = None
                        if 'pId' in ep_data:
                            ep_data['pId'] = None
                    
                    all_episodes.append(ep_data)
                
                # 江苏新媒体的图片数据
                if customer_code == 'jiangsu_newmedia':
                    abbr = drama.get('_pinyin_abbr', get_pinyin_abbr(drama['drama_name']))
                    for pic in _build_picture_data_fast(abbr):
                        picture_sequence += 1
                        pic['picture_no'] = picture_sequence
                        pic['vod_no'] = drama_sequence
                        all_pictures.append(pic)
            
            # 创建DataFrame
            drama_df = pd.DataFrame(drama_list, columns=drama_columns)
            episode_df = pd.DataFrame(all_episodes, columns=episode_columns)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            drama_df.to_excel(writer, sheet_name='剧头', index=False)
            episode_df.to_excel(writer, sheet_name='子集', index=False)
            
            if customer_code == 'jiangsu_newmedia' and all_pictures:
                picture_columns = [col['col'] for col in config.get('picture_columns', [])]
                picture_df = pd.DataFrame(all_pictures, columns=picture_columns)
                picture_df.to_excel(writer, sheet_name='图片', index=False)
            
            # 江苏新媒体使用特殊的两行表头格式
            if customer_code == 'jiangsu_newmedia':
                ExcelExportService.format_jiangsu_excel(writer)
            else:
                ExcelExportService.format_excel_sheets(writer, customer_code)
        
        output.seek(0)
        customer_name = config.get('name', '')
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'{customer_name}_注入表.xlsx')}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/batch/jiangsu_newmedia")
def export_jiangsu_batch(drama_names: list = Body(..., embed=True)):
    """
    批量导出江苏新媒体剧集
    
    参数：
    - drama_names: 剧集名称列表，例如：["剧集1", "剧集2", "剧集3"]
    
    返回：Excel文件（包含剧头、子集、图片三个sheet）
    """
    customer_code = 'jiangsu_newmedia'
    
    if not drama_names or len(drama_names) == 0:
        raise HTTPException(status_code=400, detail="请提供至少一个剧集名称")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 构建查询条件：查找江苏新媒体客户的指定剧集
            placeholders = ','.join(['%s'] * len(drama_names))
            query = f"""
                SELECT * FROM drama_main 
                WHERE customer_code = %s AND drama_name IN ({placeholders})
                ORDER BY drama_id
            """
            cursor.execute(query, (customer_code, *drama_names))
            dramas = cursor.fetchall()
            
            if not dramas:
                raise HTTPException(
                    status_code=404, 
                    detail=f"未找到匹配的江苏新媒体剧集。请检查剧集名称是否正确。"
                )
            
            # 检查是否有剧集未找到
            found_names = {d['drama_name'] for d in dramas}
            missing_names = set(drama_names) - found_names
            if missing_names:
                print(f"警告：以下剧集未找到: {', '.join(missing_names)}")
            
            config = CUSTOMER_CONFIGS[customer_code]
            drama_columns = _get_column_names(customer_code, 'drama')
            episode_columns = _get_column_names(customer_code, 'episode')
            
            # 批量查询所有子集（性能优化：一次查询替代N次查询）
            drama_ids = [d['drama_id'] for d in dramas]
            placeholders_episodes = ','.join(['%s'] * len(drama_ids))
            cursor.execute(
                f"SELECT * FROM drama_episode WHERE drama_id IN ({placeholders_episodes}) ORDER BY drama_id, episode_id",
                drama_ids
            )
            all_episodes_raw = cursor.fetchall()
            
            # 预解析所有JSON（性能优化：避免重复解析）
            for drama in dramas:
                drama['_parsed_props'] = parse_json(drama)
            
            for episode in all_episodes_raw:
                episode['_parsed_props'] = parse_json(episode)
            
            # 预计算所有拼音缩写（性能优化：避免重复计算）
            for drama in dramas:
                drama['_pinyin_abbr'] = get_pinyin_abbr(drama['drama_name'])
            
            # 按drama_id分组子集
            episodes_by_drama = {}
            for episode in all_episodes_raw:
                drama_id = episode['drama_id']
                if drama_id not in episodes_by_drama:
                    episodes_by_drama[drama_id] = []
                episodes_by_drama[drama_id].append(episode)
            
            # 预获取配置（避免重复查询）
            config = CUSTOMER_CONFIGS[customer_code]
            drama_columns = _get_column_names(customer_code, 'drama')
            episode_columns = _get_column_names(customer_code, 'episode')
            drama_col_configs = config.get('drama_columns', [])
            episode_col_configs = config.get('episode_columns', [])
            
            # 构建剧头数据
            drama_list = []
            all_episodes = []
            all_pictures = []
            
            drama_sequence = 0
            episode_sequence = 0
            picture_sequence = 0
            
            for drama in dramas:
                drama_sequence += 1
                # 使用预获取的配置构建剧头数据
                header_dict = _build_drama_display_dict_fast(drama, customer_code, drama_col_configs)
                
                # 设置序号
                header_dict['vod_no'] = drama_sequence
                header_dict['sId'] = None  # sId留空
                
                drama_list.append(header_dict)
                
                # 获取该剧集的子集（从已查询的数据中获取）
                episodes = episodes_by_drama.get(drama['drama_id'], [])
                
                for episode in episodes:
                    episode_sequence += 1
                    # 使用预获取的配置构建子集数据
                    ep_data = _build_episode_display_dict_fast(episode, customer_code, episode_col_configs)
                    
                    # 设置序号
                    ep_data['vod_info_no'] = episode_sequence
                    ep_data['vod_no'] = drama_sequence  # 关联剧头序号
                    ep_data['sId'] = None  # sId留空
                    ep_data['pId'] = None  # pId留空
                    
                    all_episodes.append(ep_data)
                
                # 图片数据 - 使用快速版本，直接使用预计算的拼音缩写
                abbr = drama['_pinyin_abbr']
                for pic in _build_picture_data_fast(abbr):
                    picture_sequence += 1
                    pic['picture_no'] = picture_sequence
                    pic['vod_no'] = drama_sequence
                    all_pictures.append(pic)
            
            # 创建DataFrame
            drama_df = pd.DataFrame(drama_list, columns=drama_columns)
            episode_df = pd.DataFrame(all_episodes, columns=episode_columns)
            picture_columns = [col['col'] for col in config.get('picture_columns', [])]
            picture_df = pd.DataFrame(all_pictures, columns=picture_columns)
        
        # 生成Excel（改用xlsxwriter，减少大数据量下的写入耗时）
        output = ExcelExportService.build_jiangsu_excel_fast(drama_df, episode_df, picture_df)
        
        # 生成文件名
        if len(dramas) == 1:
            filename = f"江苏新媒体_{dramas[0]['drama_name']}_注入表.xlsx"
        else:
            filename = f"江苏新媒体_批量导出_{len(dramas)}个剧集.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/export/batch/xinjiang_telecom")
def export_xinjiang_batch(drama_names: list = Body(..., embed=True)):
    """
    批量导出新疆电信剧集
    
    参数：
    - drama_names: 剧集名称列表，例如：["剧集1", "剧集2", "剧集3"]
    
    返回：Excel文件（包含剧头、子集两个sheet）
    """
    customer_code = 'xinjiang_telecom'
    
    if not drama_names or len(drama_names) == 0:
        raise HTTPException(status_code=400, detail="请提供至少一个剧集名称")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 构建查询条件：查找新疆电信客户的指定剧集
            placeholders = ','.join(['%s'] * len(drama_names))
            query = f"""
                SELECT * FROM drama_main 
                WHERE customer_code = %s AND drama_name IN ({placeholders})
                ORDER BY drama_id
            """
            cursor.execute(query, (customer_code, *drama_names))
            dramas = cursor.fetchall()
            
            if not dramas:
                raise HTTPException(
                    status_code=404, 
                    detail=f"未找到匹配的新疆电信剧集。请检查剧集名称是否正确。"
                )
            
            # 检查是否有剧集未找到
            found_names = {d['drama_name'] for d in dramas}
            missing_names = set(drama_names) - found_names
            if missing_names:
                print(f"警告：以下剧集未找到: {', '.join(missing_names)}")
            
            config = CUSTOMER_CONFIGS[customer_code]
            drama_columns = _get_column_names(customer_code, 'drama')
            episode_columns = _get_column_names(customer_code, 'episode')
            
            # 批量查询所有子集（性能优化：一次查询替代N次查询）
            drama_ids = [d['drama_id'] for d in dramas]
            placeholders_episodes = ','.join(['%s'] * len(drama_ids))
            cursor.execute(
                f"SELECT * FROM drama_episode WHERE drama_id IN ({placeholders_episodes}) ORDER BY drama_id, episode_id",
                drama_ids
            )
            all_episodes_raw = cursor.fetchall()
            
            # 预解析所有JSON（性能优化：避免重复解析）
            for drama in dramas:
                drama['_parsed_props'] = parse_json(drama)
            
            for episode in all_episodes_raw:
                episode['_parsed_props'] = parse_json(episode)
            
            # 按drama_id分组子集
            episodes_by_drama = {}
            for episode in all_episodes_raw:
                drama_id = episode['drama_id']
                if drama_id not in episodes_by_drama:
                    episodes_by_drama[drama_id] = []
                episodes_by_drama[drama_id].append(episode)
            
            # 预获取配置（避免重复查询）
            drama_col_configs = config.get('drama_columns', [])
            episode_col_configs = config.get('episode_columns', [])
            
            # 构建剧头数据
            drama_list = []
            all_episodes = []
            
            for drama in dramas:
                # 使用预获取的配置构建剧头数据
                header_dict = _build_drama_display_dict_fast(drama, customer_code, drama_col_configs)
                drama_list.append(header_dict)
                
                # 获取该剧集的子集（从已查询的数据中获取）
                episodes = episodes_by_drama.get(drama['drama_id'], [])
                
                for episode in episodes:
                    # 使用预获取的配置构建子集数据
                    ep_data = _build_episode_display_dict_fast(episode, customer_code, episode_col_configs)
                    all_episodes.append(ep_data)
            
            # 创建DataFrame
            drama_df = pd.DataFrame(drama_list, columns=drama_columns)
            episode_df = pd.DataFrame(all_episodes, columns=episode_columns)
        
        # 生成Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            drama_df.to_excel(writer, sheet_name='剧头', index=False)
            episode_df.to_excel(writer, sheet_name='子集', index=False)
            ExcelExportService.format_excel_sheets(writer, customer_code)
        
        output.seek(0)
        
        # 生成文件名
        customer_name = config.get('name', '新疆电信')
        if len(dramas) == 1:
            filename = f"{customer_name}_{dramas[0]['drama_name']}_注入表.xlsx"
        else:
            filename = f"{customer_name}_批量导出_{len(dramas)}个剧集.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.delete("/{drama_id}")
def delete_drama(drama_id: int):
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


@router.post("/extract-names-from-excel")
def extract_drama_names_from_excel(file: bytes = Body(...)):
    """
    从Excel文件中提取剧集名称列
    用于江苏新媒体批量搜索功能
    """
    try:
        # 使用pandas读取Excel
        excel_data = BytesIO(file)
        df = pd.read_excel(excel_data, dtype=str).fillna('')
        
        if df.empty:
            raise HTTPException(status_code=400, detail="Excel文件为空")
        
        # 查找剧集名称列
        possible_names = ['剧集名称', '名称', '剧名', '片名', '内容名称', 'seriesName', '剧头名称']
        name_column = None
        
        for col in df.columns:
            col_str = str(col).strip()
            if any(name in col_str for name in possible_names):
                name_column = col
                break
        
        if name_column is None:
            # 如果没找到，尝试第一列
            name_column = df.columns[0]
        
        # 提取剧集名称（去除空值）
        drama_names = []
        for value in df[name_column]:
            name = str(value).strip()
            if name and name != '' and name.lower() != 'nan':
                drama_names.append(name)
        
        if not drama_names:
            raise HTTPException(status_code=400, detail="Excel文件中没有找到有效的剧集名称")
        
        return {
            "code": 200,
            "message": "提取成功",
            "data": {
                "drama_names": drama_names,
                "count": len(drama_names),
                "column_name": str(name_column)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析Excel失败: {str(e)}")


@router.post("/import-and-query-excel")
def import_and_query_excel(
    file: bytes = Body(...),
    customer_code: str = Query(...)
):
    """
    从Excel导入并直接查询剧集信息
    一步到位：解析Excel → 提取剧集名称 → 批量查询 → 返回结果
    """
    try:
        # 1. 解析Excel，提取剧集名称
        excel_data = BytesIO(file)
        df = pd.read_excel(excel_data, dtype=str).fillna('')
        
        if df.empty:
            raise HTTPException(status_code=400, detail="Excel文件为空")
        
        # 查找剧集名称列
        possible_names = ['剧集名称', '名称', '剧名', '片名', '内容名称', 'seriesName', '剧头名称']
        name_column = None
        
        for col in df.columns:
            col_str = str(col).strip()
            if any(name in col_str for name in possible_names):
                name_column = col
                break
        
        if name_column is None:
            name_column = df.columns[0]
        
        # 提取剧集名称
        drama_names = []
        for value in df[name_column]:
            name = str(value).strip()
            if name and name != '' and name.lower() != 'nan':
                drama_names.append(name)
        
        if not drama_names:
            raise HTTPException(status_code=400, detail="Excel文件中没有找到有效的剧集名称")
        
        # 2. 批量查询剧集信息
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 批量查询剧头信息
            placeholders = ','.join(['%s'] * len(drama_names))
            query = f"""
                SELECT drama_id, drama_name, dynamic_properties
                FROM drama_main
                WHERE customer_code = %s AND drama_name IN ({placeholders})
            """
            cursor.execute(query, [customer_code] + drama_names)
            dramas = cursor.fetchall()
            
            # 构建剧集名称到数据的映射
            drama_map = {}
            drama_ids = []
            for drama in dramas:
                drama_name = drama['drama_name']
                drama_map[drama_name] = {
                    'drama_id': drama['drama_id'],
                    'drama_name': drama_name,
                    'properties': parse_json(drama)
                }
                drama_ids.append(drama['drama_id'])
            
            # 批量查询子集数量
            episode_counts = {}
            if drama_ids:
                placeholders = ','.join(['%s'] * len(drama_ids))
                cursor.execute(
                    f"SELECT drama_id, COUNT(*) as episode_count FROM drama_episode WHERE drama_id IN ({placeholders}) GROUP BY drama_id",
                    drama_ids
                )
                episode_counts = {row['drama_id']: row['episode_count'] for row in cursor.fetchall()}
            
            # 3. 构建返回结果
            results = []
            for name in drama_names:
                if name in drama_map:
                    drama_info = drama_map[name]
                    drama_id = drama_info['drama_id']
                    props = drama_info['properties']
                    
                    # 获取关键信息
                    description = props.get('description', '') or props.get('简介', '')
                    
                    results.append({
                        'name': name,
                        'found': True,
                        'drama_id': drama_id,
                        'episode_count': episode_counts.get(drama_id, 0),
                        'description': description
                    })
                else:
                    results.append({
                        'name': name,
                        'found': False
                    })
        
        return {
            "code": 200,
            "message": "导入并查询成功",
            "data": {
                "results": results,
                "total": len(drama_names),
                "found": len([r for r in results if r['found']]),
                "not_found": len([r for r in results if not r['found']]),
                "column_name": str(name_column)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入并查询失败: {str(e)}")



@router.post("/batch-query")
def batch_query_dramas(
    drama_names: List[str] = Body(..., embed=True),
    customer_code: str = Body(...)
):
    """
    批量查询剧集信息
    用于优化江苏新媒体批量搜索性能
    """
    try:
        if not drama_names:
            raise HTTPException(status_code=400, detail="剧集名称列表不能为空")
        
        if not customer_code:
            raise HTTPException(status_code=400, detail="客户代码不能为空")
        
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 批量查询剧头信息（使用IN查询）
            placeholders = ','.join(['%s'] * len(drama_names))
            query = f"""
                SELECT drama_id, drama_name, dynamic_properties
                FROM drama_main
                WHERE customer_code = %s AND drama_name IN ({placeholders})
            """
            cursor.execute(query, [customer_code] + drama_names)
            dramas = cursor.fetchall()
            
            # 构建剧集名称到数据的映射
            drama_map = {}
            drama_ids = []
            for drama in dramas:
                drama_name = drama['drama_name']
                drama_map[drama_name] = {
                    'drama_id': drama['drama_id'],
                    'drama_name': drama_name,
                    'properties': parse_json(drama)
                }
                drama_ids.append(drama['drama_id'])
            
            # 批量查询子集数量
            if drama_ids:
                placeholders = ','.join(['%s'] * len(drama_ids))
                cursor.execute(
                    f"SELECT drama_id, COUNT(*) as episode_count FROM drama_episode WHERE drama_id IN ({placeholders}) GROUP BY drama_id",
                    drama_ids
                )
                episode_counts = {row['drama_id']: row['episode_count'] for row in cursor.fetchall()}
            else:
                episode_counts = {}
            
            # 构建返回结果
            results = []
            for name in drama_names:
                if name in drama_map:
                    drama_info = drama_map[name]
                    drama_id = drama_info['drama_id']
                    props = drama_info['properties']
                    
                    # 获取关键信息
                    description = props.get('description', '') or props.get('简介', '')
                    
                    results.append({
                        'name': name,
                        'found': True,
                        'drama_id': drama_id,
                        'episode_count': episode_counts.get(drama_id, 0),
                        'description': description
                    })
                else:
                    results.append({
                        'name': name,
                        'found': False
                    })
        
        return {
            "code": 200,
            "message": "查询成功",
            "data": {
                "results": results,
                "total": len(drama_names),
                "found": len([r for r in results if r['found']]),
                "not_found": len([r for r in results if not r['found']])
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量查询失败: {str(e)}")
