"""
剧集服务层
提供剧集相关的业务逻辑，封装数据访问和数据转换
"""
import json
import pymysql
from typing import Optional, Dict, Any, List, Tuple
from database import get_db, get_db_cursor
from utils import parse_json, get_pinyin_abbr, get_image_url
from config import CUSTOMER_CONFIGS


# ============================================================
# 江苏新媒体表头配置
# ============================================================

JIANGSU_HEADERS = {
    '剧头': {
        'row1': ['vod_no', 'sId', 'appId', 'seriesName', 'volumnCount', 'description', 'seriesFlag', 'sortName', 'programType', 'releaseYear', 'language', 'rating', 'originalCountry', 'pgmCategory', 'pgmSedClass', 'director', 'actorDisplay'],
        'row2': ['序号', 'ID', '应用Id', '剧头名称', '集数', '介绍', '剧头类型', '搜索关键字', '栏目类型', '上映日期', '语言', '评分', '来源国家', '分类', '二级分类', '导演', '演员'],
    },
    '子集': {
        'row1': ['vod_info_no', 'vod_no', 'sId', 'pId', 'programName', 'volumnCount', 'type', 'fileURL', 'duration', 'bitRateType', 'mediaSpec'],
        'row2': ['序号', '剧头序号', '剧头Id', 'ID', '子集名称', '集数', '类型', '文件地址', '节目时长', '比特率', '视音频参数'],
    },
    '图片': {
        'row1': ['picture_no', 'vod_no', 'sId', 'picId', 'type', 'sequence', 'fileURL'],
        'row2': ['序号', '剧头序号', '剧头Id', '图片Id', '类型', '排序', '文件地址'],
    },
}

JIANGSU_COL_WIDTHS = {
    'vod_no': 8, 'sId': 10, 'appId': 10, 'seriesName': 30, 'volumnCount': 10,
    'description': 50, 'seriesFlag': 12, 'sortName': 20, 'programType': 15,
    'releaseYear': 12, 'language': 10, 'rating': 8, 'originalCountry': 12,
    'pgmCategory': 10, 'pgmSedClass': 20, 'director': 15, 'actorDisplay': 20,
    'vod_info_no': 10, 'pId': 10, 'programName': 35, 'type': 8,
    'fileURL': 60, 'duration': 12, 'bitRateType': 12, 'mediaSpec': 40,
    'picture_no': 10, 'picId': 10, 'sequence': 8,
}


# ============================================================
# 数据构建函数
# ============================================================

def build_drama_display_dict(drama: dict, customer_code: str) -> dict:
    """根据客户配置构建剧头显示数据"""
    config = CUSTOMER_CONFIGS.get(customer_code, CUSTOMER_CONFIGS.get('henan_mobile', {}))
    col_configs = config.get('drama_columns', [])
    return build_drama_display_dict_fast(drama, customer_code, col_configs)


def build_drama_display_dict_fast(drama: dict, customer_code: str, col_configs: list) -> dict:
    """根据客户配置构建剧头显示数据（快速版本，避免重复获取配置）"""
    props = drama.get('_parsed_props') if '_parsed_props' in drama else parse_json(drama)
    
    result = {}
    for col_config in col_configs:
        col_name = col_config['col']
        
        if col_config.get('field') == 'drama_id':
            result[col_name] = drama.get('drama_id', '')
        elif col_config.get('field') == 'drama_name':
            result[col_name] = drama.get('drama_name', '')
        elif 'value' in col_config:
            result[col_name] = col_config['value']
        elif col_config.get('type') == 'image':
            abbr = drama.get('_pinyin_abbr') if '_pinyin_abbr' in drama else get_pinyin_abbr(drama.get('drama_name', ''))
            image_type = col_config.get('image_type', 'vertical')
            result[col_name] = get_image_url(abbr, image_type, customer_code)
        else:
            value = props.get(col_name)
            if (value is None or value == '') and 'default' in col_config:
                value = col_config['default']
            result[col_name] = value if value is not None else ''
    
    return result


def build_episode_display_dict(episode: dict, customer_code: str, drama_name: str = '') -> dict:
    """根据客户配置构建子集显示数据"""
    config = CUSTOMER_CONFIGS.get(customer_code, CUSTOMER_CONFIGS.get('henan_mobile', {}))
    col_configs = config.get('episode_columns', [])
    return build_episode_display_dict_fast(episode, customer_code, col_configs)


def build_episode_display_dict_fast(episode: dict, customer_code: str, col_configs: list) -> dict:
    """根据客户配置构建子集显示数据（快速版本）"""
    props = episode.get('_parsed_props') if '_parsed_props' in episode else parse_json(episode)
    
    result = {}
    for col_config in col_configs:
        col_name = col_config['col']
        
        if col_config.get('field') == 'episode_id':
            result[col_name] = episode.get('episode_id', '')
        elif col_config.get('field') == 'episode_name':
            result[col_name] = episode.get('episode_name', '')
        elif 'value' in col_config:
            result[col_name] = col_config['value']
        else:
            value = props.get(col_name)
            if (value is None or value == '') and 'default' in col_config:
                value = col_config['default']
            result[col_name] = value if value is not None else ''
    
    return result


def get_column_names(customer_code: str, table_type: str = 'drama') -> list:
    """获取客户配置的列名列表"""
    config = CUSTOMER_CONFIGS.get(customer_code, CUSTOMER_CONFIGS.get('henan_mobile', {}))
    columns_key = 'drama_columns' if table_type == 'drama' else 'episode_columns'
    return [col['col'] for col in config.get(columns_key, [])]


def build_picture_data(drama: dict, customer_code: str) -> list:
    """构建江苏新媒体的图片数据 - 每个剧头4张图片(type: 0,1,2,99)"""
    abbr = drama.get('_pinyin_abbr') if '_pinyin_abbr' in drama else get_pinyin_abbr(drama['drama_name'])
    return build_picture_data_fast(abbr)


def build_picture_data_fast(abbr: str) -> list:
    """快速构建江苏新媒体的图片数据（直接使用拼音缩写）"""
    return [
        {'picture_no': '', 'vod_no': '', 'sId': None, 'picId': None, 'type': 0, 'sequence': 1, 'fileURL': f"/img/{abbr}/0.jpg"},
        {'picture_no': '', 'vod_no': '', 'sId': None, 'picId': None, 'type': 1, 'sequence': 2, 'fileURL': f"/img/{abbr}/1.jpg"},
        {'picture_no': '', 'vod_no': '', 'sId': None, 'picId': None, 'type': 2, 'sequence': 3, 'fileURL': f"/img/{abbr}/2.jpg"},
        {'picture_no': '', 'vod_no': '', 'sId': None, 'picId': None, 'type': 99, 'sequence': 4, 'fileURL': f"/img/{abbr}/99.jpg"},
    ]


# ============================================================
# 数据库查询服务
# ============================================================

class DramaQueryService:
    """剧集查询服务"""
    
    @staticmethod
    def get_dramas_paginated(
        customer_code: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[list, int]:
        """获取分页剧集列表"""
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
            
            return dramas, total
    
    @staticmethod
    def get_drama_by_id(drama_id: int) -> Optional[dict]:
        """根据ID获取剧集"""
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM drama_main WHERE drama_id = %s", (drama_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_drama_by_name(name: str, customer_code: str) -> Optional[dict]:
        """根据名称和客户代码获取剧集"""
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT * FROM drama_main WHERE drama_name = %s AND customer_code = %s",
                (name, customer_code)
            )
            return cursor.fetchone()
    
    @staticmethod
    def get_dramas_by_names(names: list, customer_code: str) -> list:
        """批量根据名称获取剧集"""
        if not names:
            return []
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            placeholders = ','.join(['%s'] * len(names))
            cursor.execute(
                f"SELECT * FROM drama_main WHERE customer_code = %s AND drama_name IN ({placeholders}) ORDER BY drama_id",
                (customer_code, *names)
            )
            return cursor.fetchall()
    
    @staticmethod
    def get_dramas_by_customer(customer_code: str) -> list:
        """获取指定客户的所有剧集"""
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT * FROM drama_main WHERE customer_code = %s ORDER BY drama_id",
                (customer_code,)
            )
            return cursor.fetchall()
    
    @staticmethod
    def get_episodes_by_drama_id(drama_id: int) -> list:
        """获取指定剧集的所有子集"""
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id",
                (drama_id,)
            )
            return cursor.fetchall()
    
    @staticmethod
    def get_episodes_by_drama_ids(drama_ids: list) -> list:
        """批量获取多个剧集的子集"""
        if not drama_ids:
            return []
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            placeholders = ','.join(['%s'] * len(drama_ids))
            cursor.execute(
                f"SELECT * FROM drama_episode WHERE drama_id IN ({placeholders}) ORDER BY drama_id, episode_id",
                drama_ids
            )
            return cursor.fetchall()
    
    @staticmethod
    def delete_drama(drama_id: int) -> bool:
        """删除剧集"""
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT drama_id FROM drama_main WHERE drama_id = %s", (drama_id,))
            if not cursor.fetchone():
                return False
            cursor.execute("DELETE FROM drama_main WHERE drama_id = %s", (drama_id,))
            conn.commit()
            return True


# ============================================================
# 数据预处理辅助函数
# ============================================================

def preprocess_dramas(dramas: list) -> list:
    """预处理剧集数据：解析JSON，计算拼音"""
    for drama in dramas:
        drama['_parsed_props'] = parse_json(drama)
        drama['_pinyin_abbr'] = get_pinyin_abbr(drama.get('drama_name', ''))
    return dramas


def preprocess_episodes(episodes: list) -> list:
    """预处理子集数据：解析JSON"""
    for episode in episodes:
        episode['_parsed_props'] = parse_json(episode)
    return episodes


def group_episodes_by_drama(episodes: list) -> dict:
    """按 drama_id 分组子集"""
    episodes_by_drama = {}
    for episode in episodes:
        drama_id = episode['drama_id']
        if drama_id not in episodes_by_drama:
            episodes_by_drama[drama_id] = []
        episodes_by_drama[drama_id].append(episode)
    return episodes_by_drama
