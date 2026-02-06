"""
Excel导入服务模块 - 高性能版本
实现版权方数据的Excel批量导入功能，同时生成剧头和子集
支持异步子集生成，提升用户体验
"""
import os
import uuid
import json
import pymysql
import pandas as pd
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from config import CUSTOMER_CONFIGS, get_enabled_customers
from utils import (
    get_pinyin_abbr, get_image_url, get_product_category, format_datetime,
    clean_numeric, clean_string, build_drama_props, build_episodes,
    extract_episode_number, find_scan_match,
    COLUMN_MAPPING, NUMERIC_FIELDS, INSERT_FIELDS
)


class ImportStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    GENERATING_EPISODES = "generating_episodes"  # 新增：正在生成子集


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
    # 新增：子集生成进度
    episode_generation_status: str = ""  # "", "pending", "running", "completed", "failed"
    episode_generation_progress: int = 0  # 百分比 0-100
    drama_ids_for_episodes: List[Dict] = field(default_factory=list)  # 待生成子集的剧头信息


class ExcelImportService:
    """Excel导入服务"""
    
    BATCH_SIZE = 2000  # 增大批次大小，减少commit次数
    MAX_FILE_SIZE = 50 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}
    
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
    
    def parse_excel(self, task: ImportTask) -> Dict[str, Any]:
        try:
            df = pd.read_excel(task.file_path, dtype=str).fillna('')
            rename_map = {col: COLUMN_MAPPING[col.strip()] for col in df.columns if col.strip() in COLUMN_MAPPING}
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

    def _preload_scans(self, cursor, media_names: List[str] = None) -> Dict:
        """按需加载扫描结果，只查询本次导入涉及的媒体名称"""
        if not media_names:
            # 如果没有指定媒体名称，返回空字典（兼容旧调用）
            return {}
        
        # 构建查询条件，匹配文件名与文件夹命名
        result = {}
        folder_index = {}
        # 分批查询，每批100个媒体名称，避免SQL过长
        for i in range(0, len(media_names), 100):
            batch_names = media_names[i:i+100]
            batch_abbrs = [get_pinyin_abbr(name) for name in batch_names]
            batch_abbrs = [abbr for abbr in batch_abbrs if abbr]

            conditions = []
            values = []
            # 使用LIKE匹配 file_name，每个媒体名称可能有多集
            if batch_names:
                like_conditions = ' OR '.join(['file_name LIKE %s'] * len(batch_names))
                conditions.append(f"({like_conditions})")
                values.extend([f"{name}%" for name in batch_names])
                # folder 直接命名为剧集名称
                in_names = ','.join(['%s'] * len(batch_names))
                conditions.append(f"source_file IN ({in_names})")
                values.extend(batch_names)
            # folder 命名为拼音缩写
            if batch_abbrs:
                in_abbrs = ','.join(['%s'] * len(batch_abbrs))
                conditions.append(f"source_file IN ({in_abbrs})")
                values.extend(batch_abbrs)

            where_sql = ' OR '.join(conditions) if conditions else '1=0'
            
            cursor.execute(
                f"SELECT file_name, pinyin_abbr, source_file, duration_seconds, duration_formatted, size_bytes, md5 FROM video_scan_result WHERE {where_sql}",
                values
            )
            
            for r in cursor.fetchall():
                if r['file_name']:
                    # 从 file_name 中去掉扩展名，得到标准集名用于匹配
                    key = os.path.splitext(r['file_name'])[0]
                    scan_data = {
                        'duration': int(r['duration_seconds'] or 0),
                        'duration_formatted': r['duration_formatted'] or '00000000',
                        'size': int(r['size_bytes'] or 0),
                        'md5': r['md5'] or ''
                    }
                    result[key] = scan_data
                    
                    # 同时用 pinyin_abbr 建立索引（如 "xzpq01"）
                    if r['pinyin_abbr']:
                        result[r['pinyin_abbr']] = scan_data

                    # 按文件夹建立索引（文件夹名可能是剧集名或拼音缩写）
                    source_file = r.get('source_file') or ''
                    if source_file:
                        ep_num = extract_episode_number(key)
                        if ep_num:
                            folder_index.setdefault(source_file, {})[ep_num] = scan_data

        if folder_index:
            result['_folder_index'] = folder_index
        
        return result

    def execute_import_sync(self, task: ImportTask, conn) -> Dict[str, Any]:
        """
        批量导入 - 优化版本
        1. 使用LAST_INSERT_ID()优化ID查询
        2. 分离子集生成到后台任务
        """
        task.status = ImportStatus.RUNNING
        task.processed_rows = task.success_count = task.failed_count = task.skipped_count = 0
        task.errors = []
        task.drama_ids_for_episodes = []

        if task.valid_data is None or len(task.valid_data) == 0:
            task.status = ImportStatus.FAILED
            task.errors.append({"message": "没有有效数据可导入"})
            return {"success": False, "error": "没有有效数据可导入"}

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        try:
            media_names_list = task.valid_data['media_name'].tolist()
            existing_names = self._get_existing_names(cursor, media_names_list)
            
            enabled_customers = get_enabled_customers()

            # 批量预计算拼音缩写
            unique_media_names = list(task.valid_data['media_name'].unique())
            pinyin_cache = {name: get_pinyin_abbr(name) for name in unique_media_names}
            
            total_rows = len(task.valid_data)
            task.total_rows = total_rows
            
            # 收集所有需要生成子集的剧头信息（用于后台异步生成）
            all_drama_episode_info = []
            
            for batch_start in range(0, total_rows, self.BATCH_SIZE):
                batch_end = min(batch_start + self.BATCH_SIZE, total_rows)
                batch_df = task.valid_data.iloc[batch_start:batch_end]
                
                copyright_values = []
                drama_batch = []  # [(customer_code, media_name, props_json, cleaned_data, episode_count)]
                columns = batch_df.columns.tolist()

                for row in batch_df.itertuples(index=False):
                    row_dict = dict(zip(columns, row))
                    media_name = str(row_dict.get('media_name', '')).strip()
                    if media_name in existing_names:
                        task.skipped_count += 1
                        continue

                    # 清洗数据
                    cleaned = {f: (clean_numeric(row_dict.get(f), NUMERIC_FIELDS[f]) if f in NUMERIC_FIELDS else clean_string(row_dict.get(f))) for f in INSERT_FIELDS if f != 'drama_ids'}
                    cleaned['media_name'] = media_name
                    episode_count = int(cleaned.get('episode_count') or 0)

                    # 为每个客户准备剧头数据（不加载scan_results，加速导入）
                    for cust in enabled_customers:
                        props = build_drama_props(cleaned, media_name, cust, {}, pinyin_cache)
                        drama_batch.append((cust, media_name, json.dumps(props, ensure_ascii=False), cleaned.copy(), episode_count))

                    copyright_values.append(cleaned)
                    existing_names.add(media_name)
                
                if not copyright_values:
                    task.processed_rows = batch_end
                    continue
                
                # 批量插入剧头，使用 LAST_INSERT_ID 获取实际的第一个ID
                if drama_batch:
                    # 按插入顺序排序，确保ID计算正确
                    insert_data = [(d[0], d[1], d[2]) for d in drama_batch]
                    cursor.executemany(
                        "INSERT INTO drama_main (customer_code, drama_name, dynamic_properties) VALUES (%s, %s, %s)",
                        insert_data
                    )
                    
                    # 使用 LAST_INSERT_ID 获取批量插入的第一个ID（MySQL特性）
                    cursor.execute("SELECT LAST_INSERT_ID() as first_id")
                    first_id = cursor.fetchone()['first_id']
                    
                    # 根据插入顺序计算每条记录的ID
                    drama_id_map = {}  # {media_name: {customer_code: drama_id}}
                    for idx, (cust, media_name, _, cleaned, ep_count) in enumerate(drama_batch):
                        drama_id = first_id + idx
                        if media_name not in drama_id_map:
                            drama_id_map[media_name] = {}
                        drama_id_map[media_name][cust] = drama_id
                        
                        # 收集子集生成信息（稍后异步生成）
                        if ep_count > 0:
                            all_drama_episode_info.append({
                                'drama_id': drama_id,
                                'media_name': media_name,
                                'episode_count': ep_count,
                                'customer_code': cust,
                                'cleaned_data': cleaned
                            })
                
                # 批量插入版权数据（不等待子集生成）
                copyright_insert_values = []
                for cleaned in copyright_values:
                    drama_ids = drama_id_map.get(cleaned['media_name'], {})
                    values = tuple(cleaned.get(f) if f != 'drama_ids' else json.dumps(drama_ids) for f in INSERT_FIELDS)
                    copyright_insert_values.append(values)
                
                placeholders = ','.join(['%s'] * len(INSERT_FIELDS))
                cursor.executemany(
                    f"INSERT INTO copyright_content ({','.join(INSERT_FIELDS)}) VALUES ({placeholders})",
                    copyright_insert_values
                )
                
                task.success_count += len(copyright_values)
                task.processed_rows = batch_end
                conn.commit()
            
            # 保存子集生成任务信息
            task.drama_ids_for_episodes = all_drama_episode_info
            task.episode_generation_status = "pending"
            
            task.status = ImportStatus.COMPLETED
            task.completed_at = datetime.now()
            
            # 启动后台线程生成子集
            if all_drama_episode_info:
                self._start_episode_generation_async(task)
            
            return {
                "success": True, 
                "inserted": task.success_count, 
                "skipped": task.skipped_count, 
                "failed": task.failed_count, 
                "errors": task.errors[:50],
                "episode_generation": "pending" if all_drama_episode_info else "none"
            }
            
        except Exception as e:
            task.status = ImportStatus.FAILED
            task.errors.append({"message": f"导入失败: {str(e)}"})
            conn.rollback()
            return {"success": False, "error": str(e)}

    def _start_episode_generation_async(self, task: ImportTask):
        """启动后台线程生成子集"""
        thread = threading.Thread(
            target=self._generate_episodes_background,
            args=(task,),
            daemon=True
        )
        thread.start()
    
    def _generate_episodes_background(self, task: ImportTask):
        """后台生成子集"""
        import traceback
        from database import get_db
        
        task.episode_generation_status = "running"
        task.episode_generation_progress = 0
        
        try:
            with get_db() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
                # 先验证哪些 drama_id 实际存在（防止删除后重新导入时的外键约束错误）
                all_drama_ids = [info['drama_id'] for info in task.drama_ids_for_episodes]
                if not all_drama_ids:
                    task.episode_generation_status = "completed"
                    task.episode_generation_progress = 100
                    return
                
                # 批量查询存在的 drama_id
                placeholders = ','.join(['%s'] * len(all_drama_ids))
                cursor.execute(f"SELECT drama_id FROM drama_main WHERE drama_id IN ({placeholders})", all_drama_ids)
                existing_drama_ids = {row['drama_id'] for row in cursor.fetchall()}
                
                # 过滤出有效的任务
                valid_tasks = [info for info in task.drama_ids_for_episodes if info['drama_id'] in existing_drama_ids]
                skipped_count = len(task.drama_ids_for_episodes) - len(valid_tasks)
                
                if skipped_count > 0:
                    print(f"[WARN] 子集生成：跳过 {skipped_count} 个已删除的剧头")
                
                if not valid_tasks:
                    task.episode_generation_status = "completed"
                    task.episode_generation_progress = 100
                    return
                
                # 收集所有需要的媒体名称，按需加载扫描结果
                media_names = list(set(info['media_name'] for info in valid_tasks))
                scan_results = self._preload_scans(cursor, media_names)
                
                # 批量预计算拼音缩写
                pinyin_cache = {name: get_pinyin_abbr(name) for name in media_names}
                
                total_dramas = len(valid_tasks)
                episode_batch = []
                EPISODE_BATCH_SIZE = 5000  # 子集批量插入大小
                
                for idx, info in enumerate(valid_tasks):
                    drama_id = info['drama_id']
                    media_name = info['media_name']
                    episode_count = info['episode_count']
                    customer_code = info['customer_code']
                    cleaned = info['cleaned_data']
                    
                    # 生成子集数据
                    eps = build_episodes(drama_id, media_name, episode_count, cleaned, customer_code, scan_results, pinyin_cache)
                    episode_batch.extend(eps)
                    
                    # 批量插入
                    if len(episode_batch) >= EPISODE_BATCH_SIZE:
                        cursor.executemany(
                            "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
                            episode_batch
                        )
                        conn.commit()
                        episode_batch = []
                    
                    # 更新进度
                    task.episode_generation_progress = int((idx + 1) / total_dramas * 100)
                
                # 插入剩余的子集
                if episode_batch:
                    cursor.executemany(
                        "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
                        episode_batch
                    )
                    conn.commit()
                
                # 更新剧头的时长相关字段（需要依赖 scan_results）
                self._update_drama_duration_fields(cursor, valid_tasks, scan_results, pinyin_cache)
                conn.commit()
                
                task.episode_generation_status = "completed"
                task.episode_generation_progress = 100
                
        except Exception as e:
            task.episode_generation_status = "failed"
            error_detail = f"子集生成失败: {str(e)}\n{traceback.format_exc()}"
            task.errors.append({"message": error_detail})
            print(f"[ERROR] 子集生成失败: {error_detail}")
    
    def _update_drama_duration_fields(self, cursor, valid_tasks, scan_results, pinyin_cache):
        """更新剧头的时长相关字段（子集生成后调用）"""
        # 按 drama_id 分组，收集每个剧头需要更新的信息
        drama_updates = {}  # {drama_id: {'media_name': ..., 'episode_count': ..., 'customer_code': ...}}
        
        for info in valid_tasks:
            drama_id = info['drama_id']
            if drama_id not in drama_updates:
                drama_updates[drama_id] = {
                    'media_name': info['media_name'],
                    'episode_count': info['episode_count'],
                    'customer_code': info['customer_code']
                }
        
        if not drama_updates:
            return
        
        # 批量获取剧头的 dynamic_properties
        drama_ids = list(drama_updates.keys())
        placeholders = ','.join(['%s'] * len(drama_ids))
        cursor.execute(
            f"SELECT drama_id, dynamic_properties FROM drama_main WHERE drama_id IN ({placeholders})",
            drama_ids
        )
        
        update_batch = []
        for row in cursor.fetchall():
            drama_id = row['drama_id']
            info = drama_updates.get(drama_id)
            if not info:
                continue
            
            try:
                props = json.loads(row['dynamic_properties'] or '{}')
            except:
                props = {}
            
            media_name = info['media_name']
            episode_count = info['episode_count']
            customer_code = info['customer_code']
            
            # 根据客户配置，更新需要 scan_results 的字段
            config = CUSTOMER_CONFIGS.get(customer_code, {})
            updated = False
            
            for c in config.get('drama_columns', []):
                col = c['col']
                col_type = c.get('type')
                
                if col_type == 'total_episodes_duration_seconds':
                    # 计算所有子集时长之和（秒），返回四舍五入的分钟数
                    total_dur = 0
                    abbr = pinyin_cache.get(media_name) if pinyin_cache else get_pinyin_abbr(media_name)
                    if episode_count > 0:
                        for ep in range(1, episode_count + 1):
                            match = find_scan_match(scan_results, media_name, abbr, ep)
                            total_dur += match.get('duration', 0)
                    # 使用四舍五入，299秒 -> 5分钟
                    props[col] = round(total_dur / 60) if total_dur else 0
                    updated = True
            
            if updated:
                update_batch.append((json.dumps(props, ensure_ascii=False), drama_id))
        
        # 批量更新
        if update_batch:
            cursor.executemany(
                "UPDATE drama_main SET dynamic_properties = %s WHERE drama_id = %s",
                update_batch
            )
            print(f"[INFO] 更新了 {len(update_batch)} 个剧头的时长字段")

