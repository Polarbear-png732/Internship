"""
Excel导入服务模块 - 超高性能版本
实现版权方数据的Excel批量导入功能，同时生成剧头和子集
使用批量插入策略，大幅提升性能
"""
import os
import uuid
import pandas as pd
import json
import time
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class ImportStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ImportTask:
    task_id: str
    file_path: str
    status: ImportStatus = ImportStatus.PENDING
    total_rows: int = 0
    processed_rows: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    errors: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    parsed_data: Optional[pd.DataFrame] = None
    valid_data: Optional[pd.DataFrame] = None
    invalid_details: List[Dict] = field(default_factory=list)
    duplicate_count: int = 0
    existing_in_db: int = 0


class ExcelImportService:
    """Excel导入服务 - 超高性能版本"""
    
    BATCH_SIZE = 500  # 大批次
    MAX_FILE_SIZE = 50 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}
    
    COLUMN_MAPPING = {
        '序号': 'serial_number', '上游版权方': 'upstream_copyright', '介质名称': 'media_name',
        '一级分类': 'category_level1', '二级分类': 'category_level2',
        '一级分类-河南标准': 'category_level1_henan', '一级分类-河南': 'category_level1_henan',
        '二级分类-河南标准': 'category_level2_henan', '二级分类-河南': 'category_level2_henan',
        '集数': 'episode_count', '单集时长': 'single_episode_duration', '总时长': 'total_duration',
        '出品年代': 'production_year', '制作地区': 'production_region', '出品地区': 'production_region',
        '语言': 'language', '语言-河南标准': 'language_henan', '语言-河南': 'language_henan',
        '国别': 'country', '国家': 'country', '导演': 'director', '编剧': 'screenwriter',
        '主演/嘉宾/主持人': 'cast_members', '主演\\嘉宾\\主持人': 'cast_members', '主演': 'cast_members',
        '推荐语': 'recommendation', '推荐语/一句话介绍': 'recommendation', '简介': 'synopsis',
        '关键字': 'keywords', '关键词': 'keywords', '清晰度': 'video_quality', '视频质量': 'video_quality',
        '标清\\高清\\4K\\3D\\杜比': 'video_quality', '许可编号': 'license_number', '许可证号': 'license_number',
        '发行许可编号\\备案号等': 'license_number', '评分': 'rating',
        '行业内相关网站的评级、评分（骨朵\\艺恩\\猫眼\\豆瓣\\时光网\\百度\\其他主流视频网站等评分': 'rating',
        '独家/非独': 'exclusive_status', '独家\\非独': 'exclusive_status', '独家状态': 'exclusive_status',
        '版权开始时间': 'copyright_start_date', '版权开始日期': 'copyright_start_date',
        '版权结束时间': 'copyright_end_date', '版权结束日期': 'copyright_end_date',
        '二级分类-山东': 'category_level2_shandong', '授权区域': 'authorization_region',
        '授权区域（全国/单独沟通）': 'authorization_region', '授权平台': 'authorization_platform',
        '授权平台（IPTV、OTT、小屏、待沟通）': 'authorization_platform',
        '合作方式': 'cooperation_mode', '合作方式（采买/分成）': 'cooperation_mode',
    }
    
    NUMERIC_FIELDS = {'episode_count': int, 'production_year': int, 'single_episode_duration': float, 'total_duration': float, 'rating': float}
    INSERT_FIELDS = ['media_name', 'upstream_copyright', 'category_level1', 'category_level2', 'category_level1_henan', 'category_level2_henan', 'episode_count', 'single_episode_duration', 'total_duration', 'production_year', 'production_region', 'language', 'language_henan', 'country', 'director', 'screenwriter', 'cast_members', 'recommendation', 'synopsis', 'keywords', 'video_quality', 'license_number', 'rating', 'exclusive_status', 'copyright_start_date', 'copyright_end_date', 'category_level2_shandong', 'authorization_region', 'authorization_platform', 'cooperation_mode', 'drama_ids']
    
    _tasks: Dict[str, ImportTask] = {}
    
    def __init__(self, upload_dir: str = "temp/uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    def validate_file(self, filename: str, file_size: int) -> tuple:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return False, f"不支持的文件格式，仅支持 {', '.join(self.ALLOWED_EXTENSIONS)}"
        if file_size > self.MAX_FILE_SIZE:
            return False, f"文件大小超过限制，最大允许 {self.MAX_FILE_SIZE // (1024*1024)}MB"
        return True, ""
    
    def create_task(self, file_path: str) -> ImportTask:
        task_id = str(uuid.uuid4())
        task = ImportTask(task_id=task_id, file_path=file_path)
        self._tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[ImportTask]:
        return self._tasks.get(task_id)
    
    def _clean_numeric(self, value, field_type):
        if value is None or value == '' or pd.isna(value):
            return None
        str_val = str(value).strip()
        if str_val in ['暂无', '制作中', '待定', '未知', '-', '/', 'N/A', 'NA', 'null', 'None']:
            return None
        try:
            cleaned = re.sub(r'[^\d.\-]', '', str_val)
            if not cleaned or cleaned in ['.', '-', '-.']:
                return None
            return int(float(cleaned)) if field_type == int else float(cleaned)
        except:
            return None
    
    def _clean_string(self, value, max_len=500):
        if value is None or pd.isna(value):
            return None
        s = str(value).strip()
        if not s or s.lower() in ['nan', 'none', 'null']:
            return None
        return s[:max_len] if len(s) > max_len else s
    
    def parse_excel(self, task: ImportTask) -> Dict[str, Any]:
        try:
            df = pd.read_excel(task.file_path, dtype=str).fillna('')
            rename_map = {col: self.COLUMN_MAPPING[col.strip()] for col in df.columns if col.strip() in self.COLUMN_MAPPING}
            if rename_map:
                df = df.rename(columns=rename_map)
            task.parsed_data = df
            task.total_rows = len(df)
            return {"success": True, "total_rows": len(df), "columns": list(df.columns)}
        except Exception as e:
            return {"success": False, "error": f"Excel解析失败: {str(e)}"}
    
    def validate_data(self, task: ImportTask, cursor=None) -> Dict[str, Any]:
        if task.parsed_data is None:
            return {"success": False, "error": "请先解析Excel文件"}
        
        df = task.parsed_data.copy()
        invalid_details, valid_indices, seen_names, final_indices = [], [], set(), []
        
        for idx, row in df.iterrows():
            media_name = str(row.get('media_name', '')).strip()
            if not media_name:
                invalid_details.append({"row": idx + 2, "reason": "介质名称为空"})
            else:
                valid_indices.append(idx)
        
        duplicate_count = 0
        for idx in valid_indices:
            media_name = str(df.loc[idx, 'media_name']).strip()
            if media_name in seen_names:
                duplicate_count += 1
            else:
                seen_names.add(media_name)
                final_indices.append(idx)
        
        valid_df = df.loc[final_indices].copy()
        existing_in_db = 0
        if cursor and len(valid_df) > 0:
            existing_names = self._get_existing_names(cursor, valid_df['media_name'].tolist())
            existing_in_db = len(existing_names)
        
        task.valid_data = valid_df
        task.invalid_details = invalid_details
        task.duplicate_count = duplicate_count
        task.existing_in_db = existing_in_db
        
        return {
            "success": True, "task_id": task.task_id, "total_rows": len(df),
            "valid_rows": len(valid_df), "invalid_rows": len([d for d in invalid_details if '为空' in d['reason']]),
            "duplicate_rows": duplicate_count, "existing_in_db": existing_in_db,
            "sample_data": [row.to_dict() for _, row in valid_df.head(10).iterrows()],
            "invalid_details": invalid_details[:50]
        }
    
    def _get_existing_names(self, cursor, names: List[str]) -> set:
        existing = set()
        for i in range(0, len(names), 1000):
            batch = names[i:i+1000]
            cursor.execute(f"SELECT media_name FROM copyright_content WHERE media_name IN ({','.join(['%s']*len(batch))})", batch)
            existing.update(row['media_name'] for row in cursor.fetchall())
        return existing

    def execute_import_sync(self, task: ImportTask, conn) -> Dict[str, Any]:
        """超高性能批量导入 - 使用批量插入策略"""
        import pymysql
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config import CUSTOMER_CONFIGS, get_enabled_customers
        from utils import get_pinyin_abbr, get_content_dir, get_product_category, get_image_url, get_media_url, format_duration, format_datetime
        
        task.status = ImportStatus.RUNNING
        task.processed_rows = task.success_count = task.failed_count = task.skipped_count = 0
        task.errors = []
        
        if task.valid_data is None or len(task.valid_data) == 0:
            task.status = ImportStatus.FAILED
            task.errors.append({"message": "没有有效数据可导入"})
            return {"success": False, "error": "没有有效数据可导入"}
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        try:
            # 预加载
            existing_names = self._get_existing_names(cursor, task.valid_data['media_name'].tolist())
            scan_results = self._preload_scans(cursor)
            enabled_customers = get_enabled_customers()
            
            total_rows = len(task.valid_data)
            task.total_rows = total_rows
            
            # 大批次处理
            for batch_start in range(0, total_rows, self.BATCH_SIZE):
                batch_end = min(batch_start + self.BATCH_SIZE, total_rows)
                batch_df = task.valid_data.iloc[batch_start:batch_end]
                
                # 收集批量数据
                copyright_values = []
                drama_batch = []  # [(customer_code, media_name, props_json, cleaned_data), ...]
                
                for _, row in batch_df.iterrows():
                    media_name = str(row.get('media_name', '')).strip()
                    if media_name in existing_names:
                        task.skipped_count += 1
                        continue
                    
                    # 清洗数据
                    cleaned = {f: (self._clean_numeric(row.get(f), self.NUMERIC_FIELDS[f]) if f in self.NUMERIC_FIELDS else self._clean_string(row.get(f))) for f in self.INSERT_FIELDS if f != 'drama_ids'}
                    cleaned['media_name'] = media_name
                    
                    # 为每个客户准备剧头数据
                    for cust in enabled_customers:
                        props = self._build_drama_props(cleaned, media_name, cust, CUSTOMER_CONFIGS, get_pinyin_abbr, get_image_url, get_product_category, format_datetime, scan_results)
                        drama_batch.append((cust, media_name, json.dumps(props, ensure_ascii=False), cleaned))
                    
                    copyright_values.append(cleaned)
                    existing_names.add(media_name)
                
                if not copyright_values:
                    task.processed_rows = batch_end
                    continue
                
                # 1. 批量插入剧头
                if drama_batch:
                    cursor.executemany(
                        "INSERT INTO drama_main (customer_code, drama_name, dynamic_properties) VALUES (%s, %s, %s)",
                        [(d[0], d[1], d[2]) for d in drama_batch]
                    )
                
                # 2. 批量查询刚插入的剧头ID
                media_names_in_batch = list(set(d[1] for d in drama_batch))
                placeholders = ','.join(['%s'] * len(media_names_in_batch))
                cursor.execute(
                    f"SELECT drama_id, customer_code, drama_name FROM drama_main WHERE drama_name IN ({placeholders}) ORDER BY drama_id DESC",
                    media_names_in_batch
                )
                
                # 构建 media_name -> {customer_code: drama_id} 映射
                drama_id_map = {}
                for row in cursor.fetchall():
                    key = row['drama_name']
                    if key not in drama_id_map:
                        drama_id_map[key] = {}
                    if row['customer_code'] not in drama_id_map[key]:
                        drama_id_map[key][row['customer_code']] = row['drama_id']
                
                # 3. 批量创建子集
                episode_values = []
                for cust, media_name, _, cleaned in drama_batch:
                    drama_id = drama_id_map.get(media_name, {}).get(cust)
                    if not drama_id:
                        continue
                    total_eps = int(cleaned.get('episode_count') or 0)
                    if total_eps > 0:
                        eps = self._build_episodes(drama_id, media_name, total_eps, cleaned, cust, scan_results, CUSTOMER_CONFIGS, get_pinyin_abbr, get_content_dir, get_media_url, format_duration)
                        episode_values.extend(eps)
                
                if episode_values:
                    cursor.executemany(
                        "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
                        episode_values
                    )
                
                # 4. 批量插入版权数据
                copyright_insert_values = []
                for cleaned in copyright_values:
                    drama_ids = drama_id_map.get(cleaned['media_name'], {})
                    values = tuple(cleaned.get(f) if f != 'drama_ids' else json.dumps(drama_ids) for f in self.INSERT_FIELDS)
                    copyright_insert_values.append(values)
                
                placeholders = ','.join(['%s'] * len(self.INSERT_FIELDS))
                cursor.executemany(
                    f"INSERT INTO copyright_content ({','.join(self.INSERT_FIELDS)}) VALUES ({placeholders})",
                    copyright_insert_values
                )
                
                task.success_count += len(copyright_values)
                task.processed_rows = batch_end
                conn.commit()
            
            task.status = ImportStatus.COMPLETED
            task.completed_at = datetime.now()
            return {"success": True, "inserted": task.success_count, "skipped": task.skipped_count, "failed": task.failed_count, "errors": task.errors[:50]}
            
        except Exception as e:
            task.status = ImportStatus.FAILED
            task.errors.append({"message": f"导入失败: {str(e)}"})
            conn.rollback()
            return {"success": False, "error": str(e)}
    
    def _preload_scans(self, cursor) -> Dict:
        cursor.execute("SELECT standard_episode_name, duration_seconds, duration_formatted, size_bytes FROM video_scan_result")
        return {r['standard_episode_name']: {
            'duration': int(r['duration_seconds'] or 0),  # 秒数，用于计算分钟
            'duration_formatted': r['duration_formatted'] or '00000000',  # 格式化时间，河南移动用
            'size': int(r['size_bytes'] or 0)
        } for r in cursor.fetchall() if r['standard_episode_name']}
    
    def _build_drama_props(self, data, media_name, cust, CONFIGS, get_abbr, get_img, get_cat, fmt_dt, scan_results=None):
        config = CONFIGS.get(cust, {})
        abbr = get_abbr(media_name)
        props = {}
        for c in config.get('drama_columns', []):
            col = c['col']
            if 'field' in c: continue
            if 'value' in c: props[col] = c['value']
            elif 'source' in c:
                v = data.get(c['source'])
                # 只有配置了 default 才使用默认值，否则保持空
                if (v is None or v == '') and 'default' in c:
                    v = c['default']
                # 分隔符转换：将逗号、顿号等转换为指定分隔符
                if v and c.get('separator'):
                    import re
                    v = re.sub(r'[,，、/／\\]', c['separator'], str(v))
                if v and c.get('suffix'): v = str(v) + c['suffix']
                if c.get('format') == 'datetime': v = fmt_dt(v) if v else ''
                props[col] = v if v is not None else ''
            elif c.get('type') == 'image': props[col] = get_img(abbr, c.get('image_type', 'vertical'), cust)
            elif c.get('type') == 'product_category':
                # 产品分类：如果一级分类为空，则产品分类也为空
                cat1 = data.get('category_level1_henan') or data.get('category_level1') or ''
                props[col] = get_cat(cat1, cust) if cat1 else ''
            elif c.get('type') == 'is_multi_episode': props[col] = 1 if int(data.get('episode_count') or 0) > 1 else 0
            elif c.get('type') == 'total_duration_seconds': props[col] = int(data.get('total_duration') or 0)
            elif c.get('type') == 'total_episodes_duration_seconds':
                # 计算所有子集时长之和（秒）
                total_dur = 0
                total_eps = int(data.get('episode_count') or 0)
                if scan_results and total_eps > 0:
                    for ep in range(1, total_eps + 1):
                        ep_name = f"{media_name}第{ep:02d}集"
                        match = scan_results.get(ep_name, {})
                        total_dur += match.get('duration', 0)
                props[col] = total_dur
            elif c.get('type') == 'pinyin_abbr': props[col] = abbr
            elif c.get('type') == 'sequence': props[col] = None
        return props
    
    def _build_episodes(self, drama_id, media_name, total, data, cust, scans, CONFIGS, get_abbr, get_dir, get_url, fmt_dur):
        config = CONFIGS.get(cust, {})
        abbr = get_abbr(media_name)
        # 获取一级分类，如果为空则 content_dir 也为空
        cat1 = data.get('category_level1_henan') or data.get('category_level1') or ''
        content_dir = get_dir(cat1, cust) if cat1 else ''
        result = []
        for ep in range(1, total + 1):
            ep_name = f"{media_name}第{ep:02d}集"
            match = scans.get(ep_name, {})
            dur = match.get('duration', 0)  # 秒数
            dur_formatted = match.get('duration_formatted', '00000000')  # 格式化时间
            size = match.get('size', 0)
            props = {}
            for c in config.get('episode_columns', []):
                col = c['col']
                if 'field' in c: continue
                if 'value' in c: props[col] = c['value']
                elif c.get('type') == 'media_url': props[col] = get_url(abbr, ep, content_dir, cust)
                elif c.get('type') == 'episode_num': props[col] = ep
                elif c.get('type') == 'duration': props[col] = dur_formatted  # 河南移动用格式化时间
                elif c.get('type') == 'duration_minutes': props[col] = fmt_dur(dur, 'minutes') if dur else 0
                elif c.get('type') == 'duration_hhmmss': props[col] = fmt_dur(dur, 'HH:MM:SS') if dur else '00:00:00'
                elif c.get('type') == 'file_size': props[col] = size
                elif c.get('type') == 'md5': props[col] = ''
                elif c.get('type') == 'episode_name_format': props[col] = c.get('format', '{drama_name}第{ep}集').format(drama_name=media_name, ep=ep)
            result.append((drama_id, ep_name, json.dumps(props, ensure_ascii=False)))
        return result
