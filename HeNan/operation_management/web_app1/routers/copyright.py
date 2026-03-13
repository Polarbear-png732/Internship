"""
版权方数据管理路由模块
提供版权内容的增删改查、Excel批量导入导出、剧头子集生成等核心功能
支持异步导入、实时进度推送（SSE）和多客户数据同步
"""
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, List
import pymysql
import pandas as pd
import json
import time
import re
from decimal import Decimal
from io import BytesIO
from urllib.parse import quote
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

from database import get_db
from utils import (
    get_pinyin_abbr, get_content_dir, get_product_category,
    get_image_url, get_media_url, format_duration, format_datetime, get_genre,
    get_customer_codes_by_operator, normalize_date_to_ymd, normalize_date_to_ymd_unpadded
)
from config import COPYRIGHT_FIELDS, CUSTOMER_CONFIGS
from models import CopyrightCreate, CopyrightUpdate, CopyrightResponse

# 从服务层导入
from services.copyright_service import (
    CopyrightDramaService, CopyrightQueryService,
    COPYRIGHT_EXPORT_COLUMNS, convert_decimal, convert_row
)
from services.cache_service import get_cache, CacheKeys
from logging_config import logger

router = APIRouter(prefix="/api/copyright", tags=["版权管理"])


def _to_text_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """将DataFrame统一转换为文本导出，空值保持为空字符串。"""
    if df is None:
        return pd.DataFrame()
    return df.fillna('').astype(str)


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


def _parse_drama_ids(raw_value: Any) -> Dict[str, int]:
    if isinstance(raw_value, str):
        return json.loads(raw_value) if raw_value else {}
    if isinstance(raw_value, dict):
        return raw_value
    return {}


def _resolve_target_customers_from_data(data: Dict[str, Any]) -> List[str]:
    return get_customer_codes_by_operator(data.get('operator_name'), enabled_only=True)


def _get_customer_operator_name(customer_code: str) -> str:
    """根据客户代码获取运营商名称（用于版权筛选）。"""
    cfg = CUSTOMER_CONFIGS.get(customer_code)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"未知客户代码: {customer_code}")
    name = str(cfg.get('name') or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail=f"客户未配置名称: {customer_code}")
    return name


def _parse_selected_ids_param(selected_ids: Optional[str]) -> List[int]:
    if not selected_ids:
        return []

    parsed_ids: List[int] = []
    for part in str(selected_ids).split(','):
        raw = part.strip()
        if not raw:
            continue
        if not raw.isdigit():
            raise HTTPException(status_code=400, detail=f"selected_ids 参数非法: {raw}")
        parsed_ids.append(int(raw))

    return parsed_ids


def _build_copyright_filters(
    keyword: Optional[str] = None,
    media_name: Optional[str] = None,
    upstream_copyright: Optional[str] = None,
    category_level1: Optional[str] = None,
    operator_name: Optional[str] = None,
) -> tuple[str, List[Any]]:
    """构建版权列表/导出的筛选 SQL。"""
    conditions: List[str] = []
    params: List[Any] = []

    def _split_multi_values(raw: Optional[str]) -> List[str]:
        if raw is None:
            return []
        values: List[str] = []
        seen = set()
        for part in re.split(r'[|｜,，;；、\n]+', str(raw)):
            value = part.strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            values.append(value)
        return values

    def _append_multi_like(column: str, raw: Optional[str]):
        values = _split_multi_values(raw)
        if not values:
            return
        if len(values) == 1:
            conditions.append(f"{column} LIKE %s")
            params.append(f"%{values[0]}%")
            return
        conditions.append("(" + " OR ".join([f"{column} LIKE %s"] * len(values)) + ")")
        params.extend([f"%{v}%" for v in values])

    if keyword:
        conditions.append("media_name LIKE %s")
        params.append(f"%{keyword.strip()}%")
    _append_multi_like("media_name", media_name)
    _append_multi_like("upstream_copyright", upstream_copyright)
    _append_multi_like("category_level1", category_level1)
    _append_multi_like("operator_name", operator_name)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_clause, params


@router.get("/filter-options")
def get_copyright_filter_options(
    limit: int = Query(200, ge=20, le=1000, description="每个字段最多返回条数")
):
    """获取版权筛选字段的候选值（用于前端下拉建议）。"""
    field_map = {
        'media_name': 'media_name',
        'upstream_copyright': 'upstream_copyright',
        'category_level1': 'category_level1',
        'operator_name': 'operator_name',
    }

    data: Dict[str, List[str]] = {
        'media_name': [],
        'upstream_copyright': [],
        'category_level1': [],
        'operator_name': [],
    }

    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        for key, column in field_map.items():
            cursor.execute(
                f"""
                SELECT DISTINCT {column} AS value
                FROM copyright_content
                WHERE {column} IS NOT NULL
                  AND TRIM({column}) <> ''
                ORDER BY {column} ASC
                LIMIT %s
                """,
                (limit,),
            )
            values = []
            for row in cursor.fetchall():
                value = str(row.get('value') or '').strip()
                if value:
                    values.append(value)
            data[key] = values

    return {
        'code': 200,
        'message': 'success',
        'data': data,
    }


def _normalize_copyright_item_dates(item: Dict[str, Any]) -> Dict[str, Any]:
    """统一版权列表日期输出格式。"""
    if not item:
        return item
    item['copyright_start_date'] = normalize_date_to_ymd(item.get('copyright_start_date'))
    item['copyright_end_date'] = normalize_date_to_ymd(item.get('copyright_end_date'))
    item['premiere_date'] = normalize_date_to_ymd_unpadded(item.get('premiere_date'))
    return item


# ============================================================
# API 路由
# ============================================================

@router.get("")
def get_copyright_list(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    media_name: Optional[str] = Query(None, description="按介质名称筛选"),
    upstream_copyright: Optional[str] = Query(None, description="按上游版权方筛选"),
    category_level1: Optional[str] = Query(None, description="按一级分类筛选"),
    operator_name: Optional[str] = Query(None, description="按运营商筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取版权方数据列表（带缓存）"""
    # 尝试从缓存获取
    cache_key = (
        f"{CacheKeys.COPYRIGHT_LIST}:"
        f"{keyword or ''}:{media_name or ''}:{upstream_copyright or ''}:{category_level1 or ''}:{operator_name or ''}:"
        f"{page}:{page_size}"
    )
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        where_clause, params = _build_copyright_filters(
            keyword=keyword,
            media_name=media_name,
            upstream_copyright=upstream_copyright,
            category_level1=category_level1,
            operator_name=operator_name,
        )
        
        cursor.execute(f"SELECT COUNT(*) as total FROM copyright_content {where_clause}", params)
        total = cursor.fetchone()['total']
        
        offset = (page - 1) * page_size
        cursor.execute(f"SELECT * FROM copyright_content {where_clause} ORDER BY id DESC LIMIT %s OFFSET %s",
                      params + [page_size, offset])
        items = cursor.fetchall()
        items = [_normalize_copyright_item_dates(item) for item in items]
        
        result = {
            "code": 200, "message": "success",
            "data": {"list": items, "total": total, "page": page, "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size}
        }
        
        # 缓存结果（仅缓存第一页和无关键词的查询）
        if page == 1 and not any([keyword, media_name, upstream_copyright, category_level1, operator_name]):
            cache.set(cache_key, result, ttl=60)  # 缓存1分钟
        
        return result


@router.get("/selection/by-customer")
def get_copyright_selection_by_customer(
    customer_code: str = Query(..., description="客户代码"),
    keyword: Optional[str] = Query(None, description="按介质名称关键词筛选"),
    limit: int = Query(500, ge=1, le=2000, description="最大返回条数")
):
    """按客户筛选版权数据（用于剧头管理页勾选导出）。"""
    customer_name = _get_customer_operator_name(customer_code)

    conditions: List[str] = ["operator_name LIKE %s"]
    params: List[Any] = [f"%{customer_name}%"]

    if keyword and keyword.strip():
        conditions.append("media_name LIKE %s")
        params.append(f"%{keyword.strip()}%")

    where_clause = f"WHERE {' AND '.join(conditions)}"

    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            f"""
            SELECT *
            FROM copyright_content
            {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            params + [limit]
        )
        items = cursor.fetchall()
        items = [_normalize_copyright_item_dates(item) for item in items]

    return {
        "code": 200,
        "message": "success",
        "data": {
            "customer_code": customer_code,
            "customer_name": customer_name,
            "list": items,
            "total": len(items),
        }
    }


@router.get("/template")
def download_import_template():
    """下载版权方数据导入模板（只有表头的Excel文件）"""
    # 使用导出的列名顺序创建空的DataFrame，只有表头
    columns = list(COPYRIGHT_EXPORT_COLUMNS.values())
    
    df = _to_text_dataframe(pd.DataFrame(columns=columns))
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='版权方数据模板', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['版权方数据模板']
        text_format = workbook.add_format({'num_format': '@'})
        
        # 设置列宽（与导出API保持一致）
        col_widths = {
            '序号': 8,
            '上游版权方': 15, 
            '介质名称': 25, 
            '运营商': 12,
            '一级分类': 10, 
            '二级分类': 10, 
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
        }
        
        # 应用列宽
        for i, col_name in enumerate(columns):
            width = col_widths.get(col_name, 12)
            worksheet.set_column(i, i, width, text_format)
        
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

        # 在日期相关列添加注释，提示统一填写格式
        date_hint = '请统一按此格式填写：2026-03-02'
        date_columns = ['首播日期', '版权开始时间', '版权结束时间']
        for date_col in date_columns:
            if date_col in columns:
                col_idx = columns.index(date_col)
                worksheet.write_comment(0, col_idx, date_hint)
                # 输入提示：选中单元格时自动显示，不需要鼠标悬停
                worksheet.data_validation(1, col_idx, 9999, col_idx, {
                    'validate': 'any',
                    'input_title': '日期填写格式',
                    'input_message': '请按 2026-03-02 填写（例如：2026-03-02）'
                })
        
        # 设置首行高度
        worksheet.set_row(0, 30)

        # 新增说明页：更明显的填写指引，不影响导入（导入仍读取模板第一页）
        guide_sheet = workbook.add_worksheet('填写说明')
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'font_color': '#1E40AF'
        })
        text_format = workbook.add_format({
            'font_size': 11,
            'text_wrap': True,
            'valign': 'top'
        })
        highlight_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'font_color': '#B91C1C',
            'bg_color': '#FEF2F2'
        })

        guide_sheet.set_column('A:A', 80)
        guide_sheet.write('A1', '版权导入模板填写说明', title_format)
        guide_sheet.write('A3', '1. 日期相关字段（首播日期、版权开始时间、版权结束时间）请统一填写为这个格式：2026-03-02', highlight_format)
        guide_sheet.write('A5', '2. 仅填写模板中的字段；模板外字段会被忽略。', text_format)
        guide_sheet.write('A6', '3. 运营商请填写单个省份名称（例如：河南移动 / 山东移动 / 甘肃移动 / 江西移动）。', text_format)
        guide_sheet.write('A7', '4. 导入时系统读取第一个工作表（版权方数据模板），本说明页不会影响导入。', text_format)
    
    output.seek(0)
    filename_encoded = quote('版权方数据导入模板.xlsx')
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename*=UTF-8\'\'{filename_encoded}'}
    )


@router.get("/export")
def export_copyright_to_excel(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    media_name: Optional[str] = Query(None, description="按介质名称筛选"),
    upstream_copyright: Optional[str] = Query(None, description="按上游版权方筛选"),
    category_level1: Optional[str] = Query(None, description="按一级分类筛选"),
    operator_name: Optional[str] = Query(None, description="按运营商筛选"),
    customer_code: Optional[str] = Query(None, description="按客户代码筛选运营商"),
    selected_ids: Optional[str] = Query(None, description="按逗号分隔的版权ID列表导出"),
):
    """导出所有版权方数据为Excel文件（高性能版本）"""
    selected_id_values = _parse_selected_ids_param(selected_ids)

    if selected_id_values and not customer_code:
        raise HTTPException(status_code=400, detail="按勾选导出时必须传 customer_code")

    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        where_clause, params = _build_copyright_filters(
            keyword=keyword,
            media_name=media_name,
            upstream_copyright=upstream_copyright,
            category_level1=category_level1,
            operator_name=operator_name,
        )

        conditions: List[str] = []
        if where_clause:
            conditions.append(where_clause.replace("WHERE ", "", 1))

        if customer_code:
            customer_name = _get_customer_operator_name(customer_code)
            conditions.append("operator_name LIKE %s")
            params.append(f"%{customer_name}%")

        if selected_id_values:
            placeholders = ','.join(['%s'] * len(selected_id_values))
            conditions.append(f"id IN ({placeholders})")
            params.extend(selected_id_values)

        final_where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor.execute(f"SELECT * FROM copyright_content {final_where_clause} ORDER BY created_at DESC, id DESC", params)
        items = cursor.fetchall()
    
    export_data = []
    for export_index, item in enumerate(items, start=1):
        row = {}
        for db_col, cn_col in COPYRIGHT_EXPORT_COLUMNS.items():
            # 序号列按导出顺序从 1 递增，不使用数据库内 id 字段
            if db_col == 'id':
                value = export_index
            else:
                value = item.get(db_col, '')

            # 集数统一导出为整数，避免出现 30.0 / 7.0
            if db_col == 'episode_count':
                if value is not None and value != '':
                    try:
                        value = int(float(value))
                    except (ValueError, TypeError):
                        value = ''
                else:
                    value = ''
            
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
    
    df = _to_text_dataframe(pd.DataFrame(export_data, columns=list(COPYRIGHT_EXPORT_COLUMNS.values())))

    output = BytesIO()
    # 使用 xlsxwriter 引擎，性能更好
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='版权数据', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['版权数据']
        text_format = workbook.add_format({'num_format': '@'})
        
        # 设置列宽（按照数据库表结构顺序，不包含序号(自定义)）
        col_widths = {
            '序号': 8, 
            '上游版权方': 15, 
            '介质名称': 25, 
            '运营商': 12,
            '一级分类': 10, 
            '二级分类': 10, 
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
        }
        
        for idx, col_name in enumerate(df.columns):
            width = col_widths.get(col_name, 15)
            worksheet.set_column(idx, idx, width, text_format)
        
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
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM copyright_content WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="数据不存在")
        item = _normalize_copyright_item_dates(item)
        return {"code": 200, "message": "success", "data": item}


@router.post("")
def create_copyright(data: Dict[str, Any] = Body(...)):
    """创建版权方数据，自动为所有启用的客户生成剧头和子集"""
    start_time = time.time()
    
    if 'media_name' not in data or not data['media_name']:
        raise HTTPException(status_code=400, detail="介质名称不能为空")

    episode_count = data.get('episode_count')
    try:
        episode_count = int(episode_count)
    except (TypeError, ValueError):
        episode_count = 0
    if episode_count <= 0:
        raise HTTPException(status_code=400, detail="集数为必填项，且必须大于0")
    data['episode_count'] = episode_count

    # 仅版权表写入做时间格式规范；剧头/子集仍使用原始输入值
    copyright_data = dict(data)
    if 'premiere_date' in copyright_data:
        copyright_data['premiere_date'] = normalize_date_to_ymd_unpadded(copyright_data.get('premiere_date'))
    if 'copyright_start_date' in copyright_data:
        copyright_data['copyright_start_date'] = normalize_date_to_ymd(copyright_data.get('copyright_start_date'))
    if 'copyright_end_date' in copyright_data:
        copyright_data['copyright_end_date'] = normalize_date_to_ymd(copyright_data.get('copyright_end_date'))
    
    media_name = data['media_name']
    
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        try:
            # 1. 按运营商精确定位客户并创建剧头/子集
            target_customers = _resolve_target_customers_from_data(data)
            if not target_customers:
                raise HTTPException(status_code=400, detail="运营商未匹配到启用客户，请检查运营商名称")
            drama_ids = {}
            
            for customer_code in target_customers:
                drama_id = _create_drama_for_customer(cursor, data, media_name, customer_code)
                drama_ids[customer_code] = drama_id
            
            # 2. 插入版权方数据
            insert_fields = ['drama_ids']
            insert_values = [json.dumps(drama_ids)]
            
            for field in COPYRIGHT_FIELDS:
                if field in copyright_data and copyright_data[field] is not None:
                    insert_fields.append(field)
                    insert_values.append(copyright_data[field])
            
            cursor.execute(
                f"INSERT INTO copyright_content ({', '.join(insert_fields)}) VALUES ({', '.join(['%s'] * len(insert_fields))})",
                insert_values
            )
            
            copyright_id = cursor.lastrowid
            conn.commit()
            
            # 清除版权列表缓存
            cache.invalidate_prefix(CacheKeys.COPYRIGHT_LIST)
            
            logger.info(f"版权数据创建成功: id={copyright_id}, name={media_name}")
            
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
            logger.error(f"版权数据创建失败: {media_name}, 错误: {e}")
            raise


@router.put("/{item_id}")
def update_copyright(item_id: int, data: Dict[str, Any] = Body(...)):
    """更新版权方数据，并同步更新所有关联的剧集和子集（增量更新，事务保护）"""
    start_time = time.time()
    
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 仅版权表写入做时间格式规范；剧头/子集仍使用原始输入值
        copyright_data = dict(data)
        if 'premiere_date' in copyright_data:
            copyright_data['premiere_date'] = normalize_date_to_ymd_unpadded(copyright_data.get('premiere_date'))
        if 'copyright_start_date' in copyright_data:
            copyright_data['copyright_start_date'] = normalize_date_to_ymd(copyright_data.get('copyright_start_date'))
        if 'copyright_end_date' in copyright_data:
            copyright_data['copyright_end_date'] = normalize_date_to_ymd(copyright_data.get('copyright_end_date'))
        
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
            for field in COPYRIGHT_FIELDS:
                if field in copyright_data:
                    update_parts.append(f"{field} = %s")
                    update_values.append(copyright_data[field])
            
            if update_parts:
                update_values.append(item_id)
                cursor.execute(f"UPDATE copyright_content SET {', '.join(update_parts)} WHERE id = %s", update_values)
            
            # 2. 合并数据
            merged_data = dict(item)
            merged_data.update(data)
            media_name = merged_data.get('media_name')
            
            # 3. 获取现有的 drama_ids
            drama_ids = _parse_drama_ids(item.get('drama_ids'))

            # 4. 按最新运营商字段计算目标客户
            target_customers = _resolve_target_customers_from_data(merged_data)
            if not target_customers:
                raise HTTPException(status_code=400, detail="运营商未匹配到启用客户，请检查运营商名称")
            target_set = set(target_customers)
            existing_set = {code for code, drama_id in drama_ids.items() if drama_id}
            
            # 5. 更新目标客户下已有剧头（增量更新）
            total_stats = {'dramas_updated': 0, 'episodes_added': 0, 'episodes_deleted': 0, 'episodes_updated': 0}
            
            for customer_code, drama_id in list(drama_ids.items()):
                if drama_id:
                    if customer_code in target_set:
                        stats = _update_drama_for_customer(
                            cursor, drama_id, merged_data, media_name, customer_code,
                            old_episode_count=old_episode_count,
                            old_media_name=old_media_name
                        )
                        total_stats['dramas_updated'] += 1
                        total_stats['episodes_added'] += stats.get('added', 0)
                        total_stats['episodes_deleted'] += stats.get('deleted', 0)
                        total_stats['episodes_updated'] += stats.get('updated', 0)
                    else:
                        # 运营商变更后，不再属于目标客户的剧头直接删除
                        _delete_drama_and_episodes(cursor, drama_id)
                        drama_ids.pop(customer_code, None)

            # 6. 为新增目标客户创建剧头
            for customer_code in target_customers:
                if customer_code not in existing_set:
                    new_drama_id = _create_drama_for_customer(cursor, merged_data, media_name, customer_code)
                    drama_ids[customer_code] = new_drama_id

            # 7. 更新 drama_ids
            cursor.execute(
                "UPDATE copyright_content SET drama_ids = %s WHERE id = %s",
                (json.dumps(drama_ids), item_id)
            )
            
            conn.commit()
            
            # 清除版权列表缓存
            cache.invalidate_prefix(CacheKeys.COPYRIGHT_LIST)
            
            logger.info(f"版权数据更新成功: id={item_id}, name={media_name}")
            
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
            conn.rollback()
            logger.error(f"版权数据更新失败: id={item_id}, 错误: {e}")
            raise


@router.delete("/{item_id}")
def delete_copyright(item_id: int):
    """删除版权方数据及所有关联的剧集和子集"""
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("SELECT id, media_name, drama_ids FROM copyright_content WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="数据不存在")
        
        media_name = item.get('media_name')
        
        # 获取所有关联的 drama_ids
        drama_ids = _parse_drama_ids(item.get('drama_ids'))
        
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
            
            # 清除版权列表缓存
            cache.invalidate_prefix(CacheKeys.COPYRIGHT_LIST)
            
            logger.info(f"版权数据删除成功: id={item_id}, name={media_name}")
            
            return {
                "code": 200, "message": "删除成功",
                "data": {"id": item_id, "deleted_dramas": deleted_dramas}
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"版权数据删除失败: id={item_id}, 错误: {e}")
            raise


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
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


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


async def _run_backfill_task(task_id: str):
    """后台执行子集扫描字段回填任务"""
    task = import_service.get_backfill_task(task_id)
    if not task:
        return

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_backfill_task, task_id)
    except Exception as e:
        task.status = 'failed'
        task.errors.append({"message": f"回填失败: {str(e)}"})


def _sync_import_task(task_id: str):
    """同步执行导入任务"""
    task = import_service.get_task(task_id)
    if not task:
        return
    
    try:
        with get_db() as conn:
            import_service.execute_import_sync(task, conn)
        
        # 导入完成后清除版权列表缓存
        cache.invalidate_prefix(CacheKeys.COPYRIGHT_LIST)
        logger.info(f"导入任务完成，已清除版权列表缓存: task_id={task_id}")
    except Exception as e:
        task.status = ImportStatus.FAILED
        task.errors.append({"message": f"导入失败: {str(e)}"})


def _sync_backfill_task(task_id: str):
    """同步执行子集扫描字段回填任务"""
    task = import_service.get_backfill_task(task_id)
    if not task:
        return

    try:
        with get_db() as conn:
            import_service.execute_backfill_sync(task, conn)
    except Exception as e:
        task.status = 'failed'
        task.errors.append({"message": f"回填失败: {str(e)}"})


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


@router.post('/backfill/scan-fields/start')
async def start_scan_field_backfill(
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any] = Body(...)
):
    """启动子集扫描字段回填任务（仅空值回填/单剧校正重算）。"""
    media_names = payload.get('media_names') or []
    fields = payload.get('fields') or ['md5', 'duration', 'size']
    mode = payload.get('mode') or 'only_empty'

    if not isinstance(media_names, list) or not media_names:
        raise HTTPException(status_code=400, detail='media_names 不能为空')
    if mode not in {'only_empty', 'recalculate_all'}:
        raise HTTPException(status_code=400, detail='mode 仅支持 only_empty 或 recalculate_all')
    if mode == 'recalculate_all' and len(media_names) != 1:
        raise HTTPException(status_code=400, detail='recalculate_all 模式仅支持单个剧名')

    task = import_service.create_backfill_task(media_names=media_names, fields=fields, mode=mode)
    if task.total_media <= 0:
        raise HTTPException(status_code=400, detail='未提供有效剧名')

    background_tasks.add_task(_run_backfill_task, task.task_id)

    return {
        'code': 200,
        'message': '回填任务已启动',
        'data': {
            'task_id': task.task_id,
            'total_media': task.total_media,
            'fields': task.fields,
            'mode': task.mode
        }
    }


@router.get('/backfill/scan-fields/status/{task_id}')
def get_scan_field_backfill_status(task_id: str):
    """获取子集扫描字段回填任务状态"""
    task = import_service.get_backfill_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail='任务不存在')

    total = task.total_media or 1
    percentage = int(task.processed_media / total * 100) if task.total_media > 0 else 0

    return {
        'code': 200,
        'data': {
            'task_id': task.task_id,
            'status': task.status,
            'total_media': task.total_media,
            'processed_media': task.processed_media,
            'percentage': percentage,
            'fields': task.fields,
            'mode': task.mode,
            'matched_episodes': task.matched_episodes,
            'updated_episodes': task.updated_episodes,
            'skipped_episodes': task.skipped_episodes,
            'missed_episodes': task.missed_episodes,
            'failed_count': task.failed_count,
            'errors': task.errors[:50] if task.status in ['completed', 'failed'] else []
        }
    }
