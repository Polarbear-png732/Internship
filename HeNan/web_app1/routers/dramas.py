"""
剧集管理路由模块
提供剧头（剧集主信息）的查询、导出、编辑和删除功能
支持多客户配置驱动的字段映射和Excel导出格式定制
"""
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from typing import Optional, List
import pandas as pd
from io import BytesIO
from urllib.parse import quote

from config import CUSTOMER_CONFIGS
from logging_config import logger

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
    preprocess_dramas, preprocess_episodes, group_episodes_by_drama,
    DramaQueryService, DramaDetailService, BatchQueryService
)
from services.export_service import ExcelExportService

router = APIRouter(prefix="/api/dramas", tags=["剧集管理"])


# ============================================================
# 查询接口
# ============================================================

@router.get("")
def get_dramas(
    customer_code: Optional[str] = Query(None, description="客户代码"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取剧集列表"""
    dramas, total = DramaQueryService.get_dramas_paginated(customer_code, keyword, page, page_size)
    
    return {
        "code": 200, "message": "success",
        "data": {
            "list": dramas, "total": total, "page": page,
            "page_size": page_size, "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/by-name")
def get_drama_by_name(
    name: str = Query(..., description="剧集名称"),
    customer_code: str = Query('henan_mobile', description="客户代码")
):
    """根据剧集名称获取剧集详情（包含子集），按客户格式返回"""
    result = DramaDetailService.get_drama_with_episodes(name, customer_code)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"未找到该剧集（客户: {customer_code}）")
    
    return {"code": 200, "message": "success", "data": result}


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
    result = DramaDetailService.get_drama_detail_by_id(drama_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="剧集不存在")
    
    return {"code": 200, "message": "success", "data": result}


# ============================================================
# 导出接口
# ============================================================

@router.get("/{drama_id}/export")
def export_drama_to_excel(drama_id: int):
    """导出单个剧集数据为Excel文件（按该剧集所属客户的格式）"""
    from utils import parse_json, get_pinyin_abbr
    
    drama = DramaQueryService.get_drama_by_id(drama_id)
    if not drama:
        raise HTTPException(status_code=404, detail="剧集不存在")
    
    customer_code = drama.get('customer_code', 'henan_mobile')
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    drama_name = drama['drama_name']
    
    # 预处理
    drama['_parsed_props'] = parse_json(drama)
    drama['_pinyin_abbr'] = get_pinyin_abbr(drama_name)
    
    # 获取子集
    episodes = DramaQueryService.get_episodes_by_drama_id(drama_id)
    preprocess_episodes(episodes)
    
    # 导出
    output = ExcelExportService.export_single_drama(drama, episodes, customer_code)
    
    customer_name = config.get('name', '')
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'{drama_name}_{customer_name}.xlsx')}"}
    )


@router.get("/export/customer/{customer_code}")
def export_customer_dramas(customer_code: str):
    """导出指定客户的所有剧集数据为Excel文件"""
    if customer_code not in CUSTOMER_CONFIGS:
        raise HTTPException(status_code=404, detail=f"未知的客户代码: {customer_code}")
    
    # 获取剧集
    dramas = DramaQueryService.get_dramas_by_customer(customer_code)
    if not dramas:
        raise HTTPException(status_code=404, detail="该客户暂无剧集数据")
    
    # 批量获取子集
    drama_ids = [d['drama_id'] for d in dramas]
    episodes = DramaQueryService.get_episodes_by_drama_ids(drama_ids)
    
    # 预处理
    preprocess_dramas(dramas)
    preprocess_episodes(episodes)
    
    # 导出
    output = ExcelExportService.export_customer_dramas(dramas, episodes, customer_code)
    
    config = CUSTOMER_CONFIGS[customer_code]
    customer_name = config.get('name', '')
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'{customer_name}_注入表.xlsx')}"}
    )


@router.post("/export/batch/jiangsu_newmedia")
def export_jiangsu_batch(drama_names: list = Body(..., embed=True)):
    """批量导出江苏新媒体剧集"""
    customer_code = 'jiangsu_newmedia'
    
    if not drama_names:
        raise HTTPException(status_code=400, detail="请提供至少一个剧集名称")
    
    # 查询剧集
    dramas = DramaQueryService.get_dramas_by_names(drama_names, customer_code)
    if not dramas:
        raise HTTPException(status_code=404, detail="未找到匹配的江苏新媒体剧集")
    
    # 记录未找到的剧集
    found_names = {d['drama_name'] for d in dramas}
    missing_names = set(drama_names) - found_names
    if missing_names:
        logger.warning(f"批量导出：以下剧集未找到: {', '.join(missing_names)}")
    
    # 批量获取子集
    drama_ids = [d['drama_id'] for d in dramas]
    episodes = DramaQueryService.get_episodes_by_drama_ids(drama_ids)
    
    # 预处理
    preprocess_dramas(dramas)
    preprocess_episodes(episodes)
    
    # 构建数据
    config = CUSTOMER_CONFIGS[customer_code]
    drama_columns = _get_column_names(customer_code, 'drama')
    episode_columns = _get_column_names(customer_code, 'episode')
    drama_col_configs = config.get('drama_columns', [])
    episode_col_configs = config.get('episode_columns', [])
    
    episodes_by_drama = group_episodes_by_drama(episodes)
    
    drama_list, all_episodes, all_pictures = [], [], []
    drama_sequence = episode_sequence = picture_sequence = 0
    
    for drama in dramas:
        drama_sequence += 1
        header_dict = _build_drama_display_dict_fast(drama, customer_code, drama_col_configs)
        header_dict['vod_no'] = drama_sequence
        header_dict['sId'] = None
        drama_list.append(header_dict)
        
        drama_name = drama.get('drama_name', '')
        for episode in episodes_by_drama.get(drama['drama_id'], []):
            episode_sequence += 1
            ep_data = _build_episode_display_dict_fast(episode, customer_code, episode_col_configs, drama_name)
            ep_data['vod_info_no'] = episode_sequence
            ep_data['vod_no'] = drama_sequence
            ep_data['sId'] = None
            ep_data['pId'] = None
            all_episodes.append(ep_data)
        
        abbr = drama['_pinyin_abbr']
        for pic in _build_picture_data_fast(abbr):
            picture_sequence += 1
            pic['picture_no'] = picture_sequence
            pic['vod_no'] = drama_sequence
            all_pictures.append(pic)
    
    # 创建DataFrame并导出
    drama_df = pd.DataFrame(drama_list, columns=drama_columns)
    episode_df = pd.DataFrame(all_episodes, columns=episode_columns)
    picture_columns = [col['col'] for col in config.get('picture_columns', [])]
    picture_df = pd.DataFrame(all_pictures, columns=picture_columns)
    
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


@router.post("/export/batch/xinjiang_telecom")
def export_xinjiang_batch(drama_names: list = Body(..., embed=True)):
    """批量导出新疆电信剧集"""
    customer_code = 'xinjiang_telecom'
    
    if not drama_names:
        raise HTTPException(status_code=400, detail="请提供至少一个剧集名称")
    
    # 查询剧集
    dramas = DramaQueryService.get_dramas_by_names(drama_names, customer_code)
    if not dramas:
        raise HTTPException(status_code=404, detail="未找到匹配的新疆电信剧集")
    
    # 记录未找到的剧集
    found_names = {d['drama_name'] for d in dramas}
    missing_names = set(drama_names) - found_names
    if missing_names:
        logger.warning(f"批量导出：以下剧集未找到: {', '.join(missing_names)}")
    
    # 批量获取子集
    drama_ids = [d['drama_id'] for d in dramas]
    episodes = DramaQueryService.get_episodes_by_drama_ids(drama_ids)
    
    # 预处理
    preprocess_dramas(dramas)
    preprocess_episodes(episodes)
    
    # 导出
    output = ExcelExportService.export_customer_dramas(dramas, episodes, customer_code)
    
    config = CUSTOMER_CONFIGS[customer_code]
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


# ============================================================
# 删除接口
# ============================================================

@router.delete("/{drama_id}")
def delete_drama(drama_id: int):
    """删除剧头"""
    success = DramaQueryService.delete_drama(drama_id)
    if not success:
        raise HTTPException(status_code=404, detail="剧集不存在")
    
    logger.info(f"剧集已删除: drama_id={drama_id}")
    return {"code": 200, "message": "删除成功", "data": {"drama_id": drama_id}}


# ============================================================
# Excel解析与批量查询接口
# ============================================================

@router.post("/extract-names-from-excel")
def extract_drama_names_from_excel(file: bytes = Body(...)):
    """从Excel文件中提取剧集名称列"""
    try:
        result = BatchQueryService.extract_drama_names_from_excel(file)
        return {"code": 200, "message": "提取成功", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import-and-query-excel")
def import_and_query_excel(
    file: bytes = Body(...),
    customer_code: str = Query(...)
):
    """从Excel导入并直接查询剧集信息"""
    try:
        # 提取剧集名称
        extract_result = BatchQueryService.extract_drama_names_from_excel(file)
        drama_names = extract_result['drama_names']
        
        # 批量查询
        query_result = BatchQueryService.batch_query_dramas(drama_names, customer_code)
        query_result['column_name'] = extract_result['column_name']
        
        return {"code": 200, "message": "导入并查询成功", "data": query_result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch-query")
def batch_query_dramas(
    drama_names: List[str] = Body(..., embed=True),
    customer_code: str = Body(...)
):
    """批量查询剧集信息"""
    if not drama_names:
        raise HTTPException(status_code=400, detail="剧集名称列表不能为空")
    if not customer_code:
        raise HTTPException(status_code=400, detail="客户代码不能为空")
    
    result = BatchQueryService.batch_query_dramas(drama_names, customer_code)
    return {"code": 200, "message": "查询成功", "data": result}
