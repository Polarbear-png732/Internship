"""
Excel导入服务模块 - 高性能版本
实现版权方数据的Excel批量导入功能，同时生成剧头和子集
"""
import os
import uuid
import json
import pymysql
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from config import CUSTOMER_CONFIGS, get_enabled_customers
from utils import (
    get_pinyin_abbr, get_image_url, get_product_category, format_datetime,
    clean_numeric, clean_string, build_drama_props, build_episodes,
    COLUMN_MAPPING, NUMERIC_FIELDS, INSERT_FIELDS
)


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
    """Excel导入服务"""
    
    BATCH_SIZE = 500
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

    def _preload_scans(self, cursor) -> Dict:
        cursor.execute("SELECT standard_episode_name, duration_seconds, duration_formatted, size_bytes FROM video_scan_result")
        return {r['standard_episode_name']: {
            'duration': int(r['duration_seconds'] or 0),
            'duration_formatted': r['duration_formatted'] or '00000000',
            'size': int(r['size_bytes'] or 0)
        } for r in cursor.fetchall() if r['standard_episode_name']}

    def execute_import_sync(self, task: ImportTask, conn) -> Dict[str, Any]:
        """批量导入"""
        task.status = ImportStatus.RUNNING
        task.processed_rows = task.success_count = task.failed_count = task.skipped_count = 0
        task.errors = []
        
        if task.valid_data is None or len(task.valid_data) == 0:
            task.status = ImportStatus.FAILED
            task.errors.append({"message": "没有有效数据可导入"})
            return {"success": False, "error": "没有有效数据可导入"}
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        try:
            existing_names = self._get_existing_names(cursor, task.valid_data['media_name'].tolist())
            scan_results = self._preload_scans(cursor)
            enabled_customers = get_enabled_customers()
            
            total_rows = len(task.valid_data)
            task.total_rows = total_rows
            
            for batch_start in range(0, total_rows, self.BATCH_SIZE):
                batch_end = min(batch_start + self.BATCH_SIZE, total_rows)
                batch_df = task.valid_data.iloc[batch_start:batch_end]
                
                copyright_values = []
                drama_batch = []
                
                for _, row in batch_df.iterrows():
                    media_name = str(row.get('media_name', '')).strip()
                    if media_name in existing_names:
                        task.skipped_count += 1
                        continue
                    
                    # 清洗数据
                    cleaned = {f: (clean_numeric(row.get(f), NUMERIC_FIELDS[f]) if f in NUMERIC_FIELDS else clean_string(row.get(f))) for f in INSERT_FIELDS if f != 'drama_ids'}
                    cleaned['media_name'] = media_name
                    
                    # 为每个客户准备剧头数据
                    for cust in enabled_customers:
                        props = build_drama_props(cleaned, media_name, cust, scan_results)
                        drama_batch.append((cust, media_name, json.dumps(props, ensure_ascii=False), cleaned))
                    
                    copyright_values.append(cleaned)
                    existing_names.add(media_name)
                
                if not copyright_values:
                    task.processed_rows = batch_end
                    continue
                
                # 批量插入剧头
                if drama_batch:
                    cursor.executemany(
                        "INSERT INTO drama_main (customer_code, drama_name, dynamic_properties) VALUES (%s, %s, %s)",
                        [(d[0], d[1], d[2]) for d in drama_batch]
                    )
                
                # 查询剧头ID
                media_names_in_batch = list(set(d[1] for d in drama_batch))
                placeholders = ','.join(['%s'] * len(media_names_in_batch))
                cursor.execute(
                    f"SELECT drama_id, customer_code, drama_name FROM drama_main WHERE drama_name IN ({placeholders}) ORDER BY drama_id DESC",
                    media_names_in_batch
                )
                
                drama_id_map = {}
                for row in cursor.fetchall():
                    key = row['drama_name']
                    if key not in drama_id_map:
                        drama_id_map[key] = {}
                    if row['customer_code'] not in drama_id_map[key]:
                        drama_id_map[key][row['customer_code']] = row['drama_id']
                
                # 批量创建子集
                episode_values = []
                for cust, media_name, _, cleaned in drama_batch:
                    drama_id = drama_id_map.get(media_name, {}).get(cust)
                    if not drama_id:
                        continue
                    total_eps = int(cleaned.get('episode_count') or 0)
                    if total_eps > 0:
                        eps = build_episodes(drama_id, media_name, total_eps, cleaned, cust, scan_results)
                        episode_values.extend(eps)
                
                if episode_values:
                    cursor.executemany(
                        "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
                        episode_values
                    )
                
                # 批量插入版权数据
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
            
            task.status = ImportStatus.COMPLETED
            task.completed_at = datetime.now()
            return {"success": True, "inserted": task.success_count, "skipped": task.skipped_count, "failed": task.failed_count, "errors": task.errors[:50]}
            
        except Exception as e:
            task.status = ImportStatus.FAILED
            task.errors.append({"message": f"导入失败: {str(e)}"})
            conn.rollback()
            return {"success": False, "error": str(e)}
