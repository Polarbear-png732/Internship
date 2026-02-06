"""
版权数据服务层
提供版权内容的业务逻辑处理、剧头/子集生成等核心功能
"""
import os
import json
from decimal import Decimal
from typing import Optional, Dict, Any, List
import pymysql

from database import get_db
from utils import (
    get_pinyin_abbr, get_content_dir, get_product_category,
    get_image_url, get_media_url, format_duration, format_datetime, get_genre,
    extract_episode_number, find_scan_match
)
from config import CUSTOMER_CONFIGS, get_enabled_customers


# 导出 Excel 的列名映射
COPYRIGHT_EXPORT_COLUMNS = {
    'id': '序号',
    'upstream_copyright': '上游版权方',
    'media_name': '介质名称',
    'category_level1': '一级分类',
    'category_level2': '二级分类',
    'category_level1_henan': '一级分类-河南标准',
    'category_level2_henan': '二级分类-河南标准',
    'episode_count': '集数',
    'single_episode_duration': '单集时长（分）',
    'total_duration': '总时长（分）',
    'production_year': '出品年代',
    'premiere_date': '首播日期',
    'authorization_region': '授权区域（全国/单独沟通）',
    'authorization_platform': '授权平台（IPTV、OTT、小屏、待沟通）',
    'cooperation_mode': '合作方式（采买/分成）',
    'production_region': '制作地区',
    'language': '语言',
    'language_henan': '语言-河南标准',
    'country': '国别',
    'director': '导演',
    'screenwriter': '编剧',
    'cast_members': '主演\\嘉宾\\主持人',
    'author': '作者',
    'recommendation': '推荐语/一句话介绍',
    'synopsis': '简介',
    'keywords': '关键字',
    'video_quality': '标清\\高清\\4K\\3D\\杜比',
    'license_number': '发行许可编号\\备案号等',
    'rating': '行业内相关网站的评级、评分（骨朵\\艺恩\\猫眼\\豆瓣\\时光网\\百度\\其他主流视频网站等评分',
    'exclusive_status': '独家\\非独',
    'copyright_start_date': '版权开始时间',
    'copyright_end_date': '版权结束时间',
    'category_level2_shandong': '二级分类-山东',
}


def convert_decimal(obj):
    """将 Decimal 转换为 float，用于 JSON 序列化"""
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def convert_row(row):
    """转换数据库行中的 Decimal 类型"""
    if not row:
        return row
    return {k: convert_decimal(v) for k, v in row.items()}


class CopyrightDramaService:
    """版权-剧集生成服务，负责从版权数据生成各客户的剧头和子集"""
    
    @staticmethod
    def build_drama_props_for_customer(data: dict, media_name: str, customer_code: str) -> dict:
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
                value = convert_decimal(data.get(col_config['source']))
                if value is None or value == '':
                    value = col_config.get('default', '')
                # 处理后缀
                if value and col_config.get('suffix'):
                    value = str(value) + col_config['suffix']
                # 处理日期格式
                if col_config.get('format') == 'datetime':
                    value = format_datetime(value, 'datetime')
                elif col_config.get('format') == 'datetime_full':
                    value = format_datetime(value, 'datetime_full')
                elif col_config.get('format') == 'datetime_compact':
                    value = format_datetime(value, 'datetime_compact')
                elif col_config.get('format') == 'date_compact':
                    value = format_datetime(value, 'date_compact')
                # 数值格式化：整数
                elif col_config.get('format') == 'int':
                    try:
                        value = int(float(value)) if value else ''
                    except (ValueError, TypeError):
                        value = ''
                # 字符串长度限制
                if value and col_config.get('max_length'):
                    value = str(value)[:col_config['max_length']]
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
                props[col_name] = int(convert_decimal(data.get('total_duration')) or 0)
            elif col_config.get('type') == 'pinyin_abbr':
                props[col_name] = abbr
            elif col_config.get('type') == 'genre':
                content_type = data.get('category_level1') or ''
                props[col_name] = get_genre(content_type, customer_code)
            elif col_config.get('type') == 'sequence':
                props[col_name] = None  # 序号在导出时生成
        
        return props
    
    @staticmethod
    def create_episodes_for_customer(cursor, drama_id: int, media_name: str, 
                                      total_episodes: int, data: dict, customer_code: str) -> int:
        """根据客户配置创建子集数据（使用批量插入）"""
        if total_episodes <= 0:
            return 0
        return CopyrightDramaService.batch_create_episodes(
            cursor, drama_id, media_name, 1, total_episodes, data, customer_code
        )
    
    @staticmethod
    def create_drama_for_customer(cursor, data: dict, media_name: str, customer_code: str) -> int:
        """为指定客户创建剧头和子集，返回 drama_id"""
        dynamic_props = CopyrightDramaService.build_drama_props_for_customer(data, media_name, customer_code)
        cursor.execute(
            "INSERT INTO drama_main (customer_code, drama_name, dynamic_properties) VALUES (%s, %s, %s)",
            (customer_code, media_name, json.dumps(dynamic_props, ensure_ascii=False))
        )
        drama_id = cursor.lastrowid
        
        total_episodes = int(data.get('episode_count') or 0)
        CopyrightDramaService.create_episodes_for_customer(cursor, drama_id, media_name, total_episodes, data, customer_code)
        
        return drama_id
    
    @staticmethod
    def update_drama_for_customer(
        cursor, 
        drama_id: int, 
        data: dict, 
        media_name: str, 
        customer_code: str,
        old_episode_count: int = None,
        old_media_name: str = None
    ) -> dict:
        """更新指定客户的剧头和子集（增量更新）"""
        stats = {'added': 0, 'deleted': 0, 'updated': 0}
        
        # 更新剧头
        dynamic_props = CopyrightDramaService.build_drama_props_for_customer(data, media_name, customer_code)
        cursor.execute(
            "UPDATE drama_main SET drama_name = %s, dynamic_properties = %s WHERE drama_id = %s",
            (media_name, json.dumps(dynamic_props, ensure_ascii=False), drama_id)
        )
        
        # 获取原集数
        if old_episode_count is None:
            old_episode_count = CopyrightDramaService.get_current_episode_count(cursor, drama_id)
        
        new_episode_count = int(data.get('episode_count') or 0)
        
        # 检测介质名称变化
        if old_media_name and old_media_name != media_name:
            updated = CopyrightDramaService.update_episode_properties(
                cursor, drama_id, old_media_name, media_name, data, customer_code
            )
            stats['updated'] = updated
        
        # 增量更新子集
        episode_stats = CopyrightDramaService.update_episodes_incremental(
            cursor, drama_id, old_episode_count, new_episode_count,
            media_name, data, customer_code
        )
        stats['added'] = episode_stats['added']
        stats['deleted'] = episode_stats['deleted']
        
        return stats
    
    @staticmethod
    def delete_drama_and_episodes(cursor, drama_id: int):
        """删除剧头及其子集"""
        cursor.execute("DELETE FROM drama_episode WHERE drama_id = %s", (drama_id,))
        cursor.execute("DELETE FROM drama_main WHERE drama_id = %s", (drama_id,))
    
    @staticmethod
    def get_current_episode_count(cursor, drama_id: int) -> int:
        """获取指定剧头的当前子集数量"""
        cursor.execute("SELECT COUNT(*) as count FROM drama_episode WHERE drama_id = %s", (drama_id,))
        result = cursor.fetchone()
        return result['count'] if result else 0
    
    @staticmethod
    def update_episodes_incremental(
        cursor, 
        drama_id: int, 
        old_count: int, 
        new_count: int, 
        media_name: str, 
        data: dict, 
        customer_code: str
    ) -> dict:
        """增量更新子集数据"""
        stats = {'added': 0, 'deleted': 0, 'updated': 0}
        
        if old_count == new_count:
            return stats
        elif old_count < new_count:
            added = CopyrightDramaService.batch_create_episodes(
                cursor, drama_id, media_name, 
                old_count + 1, new_count, 
                data, customer_code
            )
            stats['added'] = added
        else:
            cursor.execute(
                """DELETE FROM drama_episode 
                   WHERE drama_id = %s 
                   AND JSON_EXTRACT(dynamic_properties, '$.集数') > %s""",
                (drama_id, new_count)
            )
            stats['deleted'] = old_count - new_count
        
        return stats
    
    @staticmethod
    def batch_create_episodes(
        cursor,
        drama_id: int,
        media_name: str,
        start_episode: int,
        end_episode: int,
        data: dict,
        customer_code: str
    ) -> int:
        """批量创建子集数据"""
        if start_episode > end_episode:
            return 0
        
        config = CUSTOMER_CONFIGS.get(customer_code, {})
        abbr = get_pinyin_abbr(media_name)
        content_type = data.get('category_level1_henan') or data.get('category_level1') or ''
        content_dir = get_content_dir(content_type, customer_code)
        
        # 批量查询扫描结果（使用 file_name 模糊匹配）
        episode_names = [f"{media_name}第{ep:02d}集" for ep in range(start_episode, end_episode + 1)]
        like_conditions = ' OR '.join(['file_name LIKE %s'] * len(episode_names))
        like_values = [f"{name}%" for name in episode_names]
        where_parts = [f"({like_conditions})"] if like_conditions else []
        where_values = list(like_values)
        # 兼容文件夹按剧集名或拼音缩写命名
        folder_values = [media_name]
        if abbr:
            folder_values.append(abbr)
        if folder_values:
            in_folders = ','.join(['%s'] * len(folder_values))
            where_parts.append(f"source_file IN ({in_folders})")
            where_values.extend(folder_values)
        where_sql = ' OR '.join(where_parts) if where_parts else '1=0'
        cursor.execute(
            f"SELECT file_name, source_file, pinyin_abbr, duration_formatted, size_bytes, md5 FROM video_scan_result WHERE {where_sql}",
            where_values
        )
        # 构建多索引映射
        scan_results = {}
        folder_index = {}
        for row in cursor.fetchall():
            key = os.path.splitext(row['file_name'])[0] if row.get('file_name') else ''
            if not key:
                continue
            scan_data = {
                'duration_formatted': row.get('duration_formatted') or '00000000',
                'size_bytes': int(row.get('size_bytes') or 0),
                'md5': row.get('md5') or ''
            }
            scan_results[key] = scan_data
            if row.get('pinyin_abbr'):
                scan_results[row['pinyin_abbr']] = scan_data
            source_file = row.get('source_file') or ''
            if source_file:
                ep_num = extract_episode_number(key)
                if ep_num:
                    folder_index.setdefault(source_file, {})[ep_num] = scan_data
        if folder_index:
            scan_results['_folder_index'] = folder_index
        
        # 构建批量插入数据
        insert_data = []
        for episode_num in range(start_episode, end_episode + 1):
            episode_name = f"{media_name}第{episode_num:02d}集"
            
            match = find_scan_match(scan_results, media_name, abbr, episode_num)
            duration = match['duration_formatted'] if match and match.get('duration_formatted') else 0
            file_size = int(match['size_bytes']) if match and match.get('size_bytes') else 0
            md5_value = match['md5'] if match and match.get('md5') else ''
            
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
                elif col_config.get('type') == 'duration_seconds':
                    episode_props[col_name] = int(duration) if duration else 0
                elif col_config.get('type') == 'duration_hhmmss':
                    episode_props[col_name] = format_duration(duration, 'HH:MM:SS') if duration else '00:00:00'
                elif col_config.get('type') == 'file_size':
                    episode_props[col_name] = file_size
                elif col_config.get('type') == 'md5':
                    episode_props[col_name] = md5_value
                elif col_config.get('type') == 'episode_name_format':
                    fmt = col_config.get('format', '{drama_name}第{ep}集')
                    episode_props[col_name] = fmt.format(drama_name=media_name, ep=episode_num)
            
            insert_data.append((drama_id, episode_name, json.dumps(episode_props, ensure_ascii=False)))
        
        if insert_data:
            cursor.executemany(
                "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
                insert_data
            )
        
        return len(insert_data)
    
    @staticmethod
    def update_episode_properties(
        cursor,
        drama_id: int,
        old_media_name: str,
        new_media_name: str,
        data: dict,
        customer_code: str
    ) -> int:
        """更新所有子集的动态属性（当介质名称变化时）"""
        config = CUSTOMER_CONFIGS.get(customer_code, {})
        new_abbr = get_pinyin_abbr(new_media_name)
        content_type = data.get('category_level1_henan') or data.get('category_level1') or ''
        content_dir = get_content_dir(content_type, customer_code)
        
        cursor.execute(
            "SELECT episode_id, episode_name, dynamic_properties FROM drama_episode WHERE drama_id = %s",
            (drama_id,)
        )
        episodes = cursor.fetchall()
        
        if not episodes:
            return 0
        
        update_data = []
        for ep in episodes:
            old_ep_name = ep['episode_name']
            episode_num = 1
            if old_ep_name and '第' in old_ep_name and '集' in old_ep_name:
                try:
                    num_str = old_ep_name.split('第')[-1].split('集')[0]
                    episode_num = int(num_str)
                except (ValueError, IndexError):
                    pass
            
            new_ep_name = f"{new_media_name}第{episode_num:02d}集"
            props = json.loads(ep['dynamic_properties']) if ep['dynamic_properties'] else {}
            
            for col_config in config.get('episode_columns', []):
                col_name = col_config['col']
                if col_config.get('type') == 'media_url':
                    props[col_name] = get_media_url(new_abbr, episode_num, content_dir, customer_code)
                elif col_config.get('type') == 'episode_name_format':
                    fmt = col_config.get('format', '{drama_name}第{ep}集')
                    props[col_name] = fmt.format(drama_name=new_media_name, ep=episode_num)
            
            update_data.append((new_ep_name, json.dumps(props, ensure_ascii=False), ep['episode_id']))
        
        if update_data:
            cursor.executemany(
                "UPDATE drama_episode SET episode_name = %s, dynamic_properties = %s WHERE episode_id = %s",
                update_data
            )
        
        return len(update_data)


class CopyrightQueryService:
    """版权数据查询服务"""
    
    @staticmethod
    def get_copyright_list(keyword: Optional[str] = None, page: int = 1, page_size: int = 10) -> dict:
        """获取版权方数据列表"""
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            where_clause, params = "", []
            if keyword:
                where_clause = "WHERE media_name LIKE %s"
                params.append(f"%{keyword}%")
            
            cursor.execute(f"SELECT COUNT(*) as total FROM copyright_content {where_clause}", params)
            total = cursor.fetchone()['total']
            
            offset = (page - 1) * page_size
            cursor.execute(
                f"SELECT * FROM copyright_content {where_clause} ORDER BY id DESC LIMIT %s OFFSET %s",
                params + [page_size, offset]
            )
            items = cursor.fetchall()
            
            return {
                "list": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
    
    @staticmethod
    def get_copyright_by_id(item_id: int) -> Optional[dict]:
        """根据ID获取版权数据"""
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM copyright_content WHERE id = %s", (item_id,))
            return convert_row(cursor.fetchone())
    
    @staticmethod
    def get_copyright_by_media_name(media_name: str) -> Optional[dict]:
        """根据介质名称获取版权数据"""
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM copyright_content WHERE media_name = %s", (media_name,))
            return convert_row(cursor.fetchone())
    
    @staticmethod
    def get_all_copyrights() -> List[dict]:
        """获取所有版权数据"""
        with get_db() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM copyright_content ORDER BY id")
            return cursor.fetchall()
