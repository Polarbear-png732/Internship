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
from utils import parse_json, build_drama_dict, build_episode_dict, get_pinyin_abbr, get_image_url
from config import CUSTOMER_CONFIGS

router = APIRouter(prefix="/api/dramas", tags=["剧集管理"])


def _build_drama_display_dict(drama, customer_code):
    """根据客户配置构建剧头显示数据"""
    config = CUSTOMER_CONFIGS.get(customer_code, CUSTOMER_CONFIGS.get('henan_mobile', {}))
    props = parse_json(drama)
    
    result = {}
    for col_config in config.get('drama_columns', []):
        col_name = col_config['col']
        
        if col_config.get('field') == 'drama_id':
            result[col_name] = drama.get('drama_id', '')
        elif col_config.get('field') == 'drama_name':
            result[col_name] = drama.get('drama_name', '')
        elif 'value' in col_config:
            result[col_name] = col_config['value']
        elif col_config.get('type') == 'image':
            # 图片URL
            abbr = get_pinyin_abbr(drama.get('drama_name', ''))
            image_type = col_config.get('image_type', 'vertical')
            result[col_name] = get_image_url(abbr, image_type, customer_code)
        else:
            # 从 dynamic_properties 中获取
            result[col_name] = props.get(col_name, col_config.get('default', ''))
    
    return result


def _build_episode_display_dict(episode, customer_code, drama_name=''):
    """根据客户配置构建子集显示数据"""
    config = CUSTOMER_CONFIGS.get(customer_code, CUSTOMER_CONFIGS.get('henan_mobile', {}))
    props = parse_json(episode)
    
    result = {}
    for col_config in config.get('episode_columns', []):
        col_name = col_config['col']
        
        if col_config.get('field') == 'episode_id':
            result[col_name] = episode.get('episode_id', '')
        elif col_config.get('field') == 'episode_name':
            result[col_name] = episode.get('episode_name', '')
        elif 'value' in col_config:
            result[col_name] = col_config['value']
        else:
            # 从 dynamic_properties 中获取
            result[col_name] = props.get(col_name, col_config.get('default', ''))
    
    return result


def _get_column_names(customer_code, table_type='drama'):
    """获取客户配置的列名列表"""
    config = CUSTOMER_CONFIGS.get(customer_code, CUSTOMER_CONFIGS.get('henan_mobile', {}))
    columns_key = 'drama_columns' if table_type == 'drama' else 'episode_columns'
    return [col['col'] for col in config.get(columns_key, [])]


@router.get("")
async def get_dramas(
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
async def get_drama_by_name(
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
async def get_customer_columns(customer_code: str):
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
async def get_drama_detail(drama_id: int):
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
async def export_drama_to_excel(drama_id: int):
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
                _format_jiangsu_excel(writer)
            else:
                _format_excel_sheets(writer, customer_code)
        
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


def _build_picture_data(drama, customer_code):
    """构建江苏新媒体的图片数据 - 每个剧头4张图片(type: 0,1,2,99)"""
    abbr = get_pinyin_abbr(drama['drama_name'])
    
    # 4种图片类型: 0, 1, 2, 99
    picture_types = [
        {'type': 0, 'sequence': 1},
        {'type': 1, 'sequence': 2},
        {'type': 2, 'sequence': 3},
        {'type': 99, 'sequence': 4},
    ]
    
    pictures = []
    for pt in picture_types:
        pictures.append({
            'picture_no': '',  # 序号，导出时会填充
            'vod_no': '',      # 剧头序号，导出时会填充
            'sId': None,       # 剧头Id，留空
            'picId': None,     # 图片Id，留空
            'type': pt['type'],
            'sequence': pt['sequence'],
            'fileURL': f"/img/{abbr}/{pt['type']}.jpg"
        })
    return pictures


def _format_excel_sheets(writer, customer_code):
    """格式化Excel表格"""
    from openpyxl.styles import Font, PatternFill
    
    workbook = writer.book
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        sheet.row_dimensions[1].height = 30
        
        for col_idx in range(1, sheet.max_column + 1):
            col_letter = get_column_letter(col_idx)
            max_width = 10
            
            for row_idx in range(1, sheet.max_row + 1):
                cell = sheet.cell(row=row_idx, column=col_idx)
                if cell.value is not None:
                    cell_width = sum(2 if ord(c) > 127 else 1 for c in str(cell.value))
                    max_width = max(max_width, min(cell_width, 50))
                cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
            
            sheet.column_dimensions[col_letter].width = max_width * 1.2 + 2


def _format_jiangsu_excel(writer):
    """为江苏新媒体格式化Excel，按照江苏新媒体注入表模版.xlsx的格式
    格式：第1行英文字段名，第2行中文说明，第3行开始是数据
    """
    from openpyxl.styles import Font, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    
    workbook = writer.book
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    header_fill = PatternFill(start_color='E0E0E0', end_color='E0E0E0', fill_type='solid')
    
    # 江苏剧头表头配置 - 2行表头
    # 第1行: 英文字段名 (vod_no, sId, appId, ...)
    # 第2行: 中文说明 (序号, ID, 应用Id, ...)
    jiangsu_drama_headers = {
        'row1': ['vod_no', 'sId', 'appId', 'seriesName', 'volumnCount', 'description', 'seriesFlag', 'sortName', 'programType', 'releaseYear', 'language', 'rating', 'originalCountry', 'pgmCategory', 'pgmSedClass', 'director', 'actorDisplay'],
        'row2': ['序号', 'ID', '应用Id', '剧头名称', '集数', '介绍', '剧头类型', '搜索关键字', '栏目类型', '上映日期', '语言', '评分', '来源国家', '分类', '二级分类', '导演', '演员'],
    }
    
    # 江苏子集表头配置 - 2行表头
    jiangsu_episode_headers = {
        'row1': ['vod_info_no', 'vod_no', 'sId', 'pId', 'programName', 'volumnCount', 'type', 'fileURL', 'duration', 'bitRateType', 'mediaSpec'],
        'row2': ['序号', '剧头序号', '剧头Id', 'ID', '子集名称', '集数', '类型', '文件地址', '节目时长', '比特率', '视音频参数'],
    }
    
    # 江苏图片表头配置 - 2行表头
    jiangsu_picture_headers = {
        'row1': ['picture_no', 'vod_no', 'sId', 'picId', 'type', 'sequence', 'fileURL'],
        'row2': ['序号', '剧头序号', '剧头Id', '图片Id', '类型', '排序', '文件地址'],
    }
    
    headers_config = {
        '剧头': jiangsu_drama_headers,
        '子集': jiangsu_episode_headers,
        '图片': jiangsu_picture_headers
    }
    
    for sheet_name in workbook.sheetnames:
        if sheet_name not in headers_config:
            continue
            
        sheet = workbook[sheet_name]
        config = headers_config[sheet_name]
        
        # 插入一行作为第二行（中文说明行）
        sheet.insert_rows(2)
        
        # 第1行已经是pandas写入的列名，覆盖为英文字段名
        for col_idx, value in enumerate(config['row1'], 1):
            cell = sheet.cell(row=1, column=col_idx)
            cell.value = value
            cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
            cell.fill = header_fill
            cell.border = thin_border
        
        # 写入第2行中文说明
        for col_idx, value in enumerate(config['row2'], 1):
            cell = sheet.cell(row=2, column=col_idx)
            cell.value = value
            cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
            cell.fill = header_fill
            cell.border = thin_border
        
        # 设置行高
        sheet.row_dimensions[1].height = 20
        sheet.row_dimensions[2].height = 20
        
        # 调整列宽
        for col_idx in range(1, sheet.max_column + 1):
            col_letter = get_column_letter(col_idx)
            max_width = 10
            
            for row_idx in range(1, min(sheet.max_row + 1, 100)):
                cell = sheet.cell(row=row_idx, column=col_idx)
                if cell.value is not None:
                    cell_width = sum(2 if ord(c) > 127 else 1 for c in str(cell.value))
                    max_width = max(max_width, min(cell_width, 50))
            
            sheet.column_dimensions[col_letter].width = max_width * 1.2 + 2


@router.get("/export/customer/{customer_code}")
async def export_customer_dramas(customer_code: str):
    """导出指定客户的所有剧集数据为Excel文件"""
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
            
            # 构建剧头数据
            drama_list = []
            all_episodes = []
            all_pictures = []
            
            drama_sequence = 0
            episode_sequence = 0
            picture_sequence = 0
            
            for drama in dramas:
                drama_sequence += 1
                header_dict = _build_drama_display_dict(drama, customer_code)
                
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
                
                # 获取子集
                cursor.execute(
                    "SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id",
                    (drama['drama_id'],)
                )
                episodes = cursor.fetchall()
                
                for episode in episodes:
                    episode_sequence += 1
                    ep_data = _build_episode_display_dict(episode, customer_code)
                    
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
                    for pic in _build_picture_data(drama, customer_code):
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
                _format_jiangsu_excel(writer)
            else:
                _format_excel_sheets(writer, customer_code)
        
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
