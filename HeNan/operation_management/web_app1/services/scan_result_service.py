"""
视频扫描结果导入服务
实现多种表格格式解析（CSV/Excel）、批量插入数据库、增量导入等功能
"""
import csv
import os
import re
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from io import StringIO
import pymysql

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from database import get_db
from logging_config import logger


class ScanImportStatus(Enum):
    """导入状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScanImportTask:
    """扫描结果导入任务"""
    task_id: str
    file_path: str
    status: ScanImportStatus = ScanImportStatus.PENDING
    total_rows: int = 0
    processed_rows: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0  # 跳过的重复记录
    errors: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class ScanResultImportService:
    """视频扫描结果导入服务"""
    
    BATCH_SIZE = 2000  # 批量插入大小
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 最大100MB
    
    # CSV 字段映射（CSV列名 -> 数据库字段名）
    FIELD_MAPPING = {
        'source_folder': 'source_folder',
        'source_file': 'source_file',
        'file_name': 'file_name',
        'pinyin_abbr': 'pinyin_abbr',
        'duration_seconds': 'duration_seconds',
        'duration_formatted': 'duration_formatted',
        'size_bytes': 'size_bytes',
        'md5': 'md5'
    }
    
    # 数据库插入字段顺序
    INSERT_FIELDS = [
        'source_folder', 'source_file', 'file_name', 'pinyin_abbr',
        'duration_seconds', 'duration_formatted', 'size_bytes', 'md5'
    ]
    VALID_IMPORT_MODES = {'incremental', 'overwrite', 'fill_missing'}
    
    _tasks: Dict[str, ScanImportTask] = {}
    
    def __init__(self, upload_dir: str = "temp/uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    # 支持的文件格式
    SUPPORTED_FORMATS = {'.csv', '.xlsx', '.xls'}
    
    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, str]:
        """验证文件"""
        ext = os.path.splitext(filename.lower())[1]
        if ext not in self.SUPPORTED_FORMATS:
            return False, f"不支持的文件格式，支持: {', '.join(self.SUPPORTED_FORMATS)}"
        if ext in {'.xlsx', '.xls'} and not HAS_PANDAS:
            return False, "Excel格式需要安装 pandas 和 openpyxl: pip install pandas openpyxl"
        if file_size > self.MAX_FILE_SIZE:
            return False, f"文件大小超过限制，最大允许 {self.MAX_FILE_SIZE // (1024*1024)}MB"
        return True, ""
    
    def create_task(self, file_path: str) -> ScanImportTask:
        """创建导入任务"""
        task_id = str(uuid.uuid4())
        task = ScanImportTask(task_id=task_id, file_path=file_path)
        self._tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[ScanImportTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def parse_csv(self, task: ScanImportTask) -> Dict[str, Any]:
        """解析文件（支持CSV/Excel）"""
        ext = os.path.splitext(task.file_path.lower())[1]
        
        if ext in {'.xlsx', '.xls'}:
            return self._parse_excel(task)
        else:
            return self._parse_csv(task)
    
    def _parse_excel(self, task: ScanImportTask) -> Dict[str, Any]:
        """解析Excel文件"""
        if not HAS_PANDAS:
            return {"success": False, "error": "需要安装 pandas 和 openpyxl: pip install pandas openpyxl"}
        
        try:
            # 读取Excel
            df = pd.read_excel(task.file_path, dtype=str)
            df = df.fillna('')  # 将NaN替换为空字符串
            
            # 验证必需字段
            headers = list(df.columns)
            missing_fields = set(self.FIELD_MAPPING.keys()) - set(headers)
            if missing_fields:
                return {
                    "success": False,
                    "error": f"Excel缺少必需字段: {', '.join(missing_fields)}"
                }
            
            records = []
            for _, row in df.iterrows():
                cleaned_row = {}
                for key in self.FIELD_MAPPING:
                    if key in row:
                        value = str(row[key]) if row[key] else ''
                        # 去除可能存在的制表符前缀
                        cleaned_row[self.FIELD_MAPPING[key]] = value.lstrip('\t')
                records.append(cleaned_row)
            
            task.total_rows = len(records)
            
            return {
                "success": True,
                "total_rows": len(records),
                "columns": list(self.FIELD_MAPPING.values()),
                "records": records
            }
        except Exception as e:
            return {"success": False, "error": f"Excel解析失败: {str(e)}"}
    
    def _parse_csv(self, task: ScanImportTask) -> Dict[str, Any]:
        """解析CSV文件"""
        try:
            records = []
            with open(task.file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # 验证必需字段
                headers = reader.fieldnames or []
                missing_fields = set(self.FIELD_MAPPING.keys()) - set(headers)
                if missing_fields:
                    return {
                        "success": False,
                        "error": f"CSV缺少必需字段: {', '.join(missing_fields)}"
                    }
                
                for row in reader:
                    # 清理数据：去除制表符前缀（Excel兼容性处理）
                    cleaned_row = {}
                    for key, value in row.items():
                        if key in self.FIELD_MAPPING:
                            # 去除可能存在的制表符前缀
                            cleaned_value = value.lstrip('\t') if value else ''
                            cleaned_row[self.FIELD_MAPPING[key]] = cleaned_value
                    records.append(cleaned_row)
            
            task.total_rows = len(records)
            
            return {
                "success": True,
                "total_rows": len(records),
                "columns": list(self.FIELD_MAPPING.values()),
                "records": records
            }
        except UnicodeDecodeError:
            # 尝试GBK编码
            try:
                records = []
                with open(task.file_path, 'r', encoding='gbk') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cleaned_row = {}
                        for key, value in row.items():
                            if key in self.FIELD_MAPPING:
                                cleaned_value = value.lstrip('\t') if value else ''
                                cleaned_row[self.FIELD_MAPPING[key]] = cleaned_value
                        records.append(cleaned_row)
                
                task.total_rows = len(records)
                return {
                    "success": True,
                    "total_rows": len(records),
                    "columns": list(self.FIELD_MAPPING.values()),
                    "records": records
                }
            except Exception as e:
                return {"success": False, "error": f"CSV解析失败: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"CSV解析失败: {str(e)}"}
    
    def get_existing_keys(self, cursor) -> set:
        """获取数据库中已存在的记录键（file_name + source_folder）"""
        cursor.execute("""
            SELECT CONCAT(IFNULL(file_name, ''), '|', IFNULL(source_folder, '')) as unique_key
            FROM video_scan_result
        """)
        return {row['unique_key'] for row in cursor.fetchall()}

    def get_existing_records(self, cursor) -> Dict[str, Dict[str, Any]]:
        """获取数据库中已存在记录映射（key -> row）"""
        cursor.execute("""
            SELECT
                id,
                source_folder,
                source_file,
                file_name,
                pinyin_abbr,
                duration_seconds,
                duration_formatted,
                size_bytes,
                md5,
                CONCAT(IFNULL(file_name, ''), '|', IFNULL(source_folder, '')) as unique_key
            FROM video_scan_result
        """)
        return {row['unique_key']: row for row in cursor.fetchall()}

    def _is_empty_field_value(self, field: str, value: Any) -> bool:
        if value is None:
            return True
        if field in {'duration_seconds', 'size_bytes'}:
            try:
                return float(value) == 0
            except (TypeError, ValueError):
                return True
        value_str = str(value).strip()
        if value_str == '':
            return True
        if field == 'duration_formatted' and value_str in {'0', '00000000', '00:00:00'}:
            return True
        return False
    
    def import_data(self, task: ScanImportTask, records: List[Dict], mode: str = "incremental") -> Dict[str, Any]:
        """
        导入数据到数据库

        mode:
        - incremental: 仅插入新记录，重复键跳过
        - overwrite: 重复键全字段覆盖更新
        - fill_missing: 重复键仅回填空值字段
        """
        import_mode = (mode or 'incremental').lower()
        if import_mode not in self.VALID_IMPORT_MODES:
            return {
                "success": False,
                "error": f"不支持的导入模式: {mode}"
            }

        task.status = ScanImportStatus.RUNNING
        
        try:
            with get_db() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)

                existing_records = self.get_existing_records(cursor)
                logger.info(f"导入模式: {import_mode}，数据库已有 {len(existing_records)} 条记录")

                insert_rows = []
                overwrite_rows = []
                fill_missing_rows = []

                overwrite_count = 0
                fill_count = 0

                for record in records:
                    key = f"{record.get('file_name', '')}|{record.get('source_folder', '')}"
                    existing = existing_records.get(key)

                    converted = {
                        field: self._convert_value(record.get(field, ''), field)
                        for field in self.INSERT_FIELDS
                    }

                    if not existing:
                        insert_rows.append(tuple(converted[field] for field in self.INSERT_FIELDS))
                        continue

                    if import_mode == 'incremental':
                        task.skipped_count += 1
                        continue

                    if import_mode == 'overwrite':
                        changed = any(existing.get(field) != converted[field] for field in self.INSERT_FIELDS)
                        if changed:
                            overwrite_rows.append(tuple(converted[field] for field in self.INSERT_FIELDS) + (existing['id'],))
                            overwrite_count += 1
                        else:
                            task.skipped_count += 1
                        continue

                    merged = {}
                    changed = False
                    for field in self.INSERT_FIELDS:
                        old_val = existing.get(field)
                        new_val = converted[field]
                        if self._is_empty_field_value(field, old_val) and not self._is_empty_field_value(field, new_val):
                            merged[field] = new_val
                            changed = True
                        else:
                            merged[field] = old_val

                    if changed:
                        fill_missing_rows.append(tuple(merged[field] for field in self.INSERT_FIELDS) + (existing['id'],))
                        fill_count += 1
                    else:
                        task.skipped_count += 1

                insert_sql = f"""
                    INSERT INTO video_scan_result
                    ({', '.join(self.INSERT_FIELDS)})
                    VALUES ({', '.join(['%s'] * len(self.INSERT_FIELDS))})
                """

                update_sql = f"""
                    UPDATE video_scan_result SET
                    {', '.join([f'{field} = %s' for field in self.INSERT_FIELDS])}
                    WHERE id = %s
                """

                def execute_batches(sql: str, rows: List[tuple], action_name: str):
                    if not rows:
                        return
                    for idx in range(0, len(rows), self.BATCH_SIZE):
                        batch = rows[idx: idx + self.BATCH_SIZE]
                        try:
                            cursor.executemany(sql, batch)
                            conn.commit()
                            task.success_count += len(batch)
                            task.processed_rows += len(batch)
                        except Exception as e:
                            task.failed_count += len(batch)
                            task.errors.append({
                                "batch": idx // self.BATCH_SIZE + 1,
                                "action": action_name,
                                "error": str(e)
                            })
                            logger.error(f"{action_name} 失败: {e}")

                execute_batches(insert_sql, insert_rows, 'insert')
                execute_batches(update_sql, overwrite_rows, 'overwrite')
                execute_batches(update_sql, fill_missing_rows, 'fill_missing')

                if not insert_rows and not overwrite_rows and not fill_missing_rows and task.skipped_count > 0:
                    message = "所有记录均已存在且无需更新"
                else:
                    message = "导入完成"
                
                task.status = ScanImportStatus.COMPLETED
                task.completed_at = datetime.now()
                
                return {
                    "success": True,
                    "message": message,
                    "total": task.total_rows,
                    "success_count": task.success_count,
                    "skipped_count": task.skipped_count,
                    "failed_count": task.failed_count,
                    "inserted_count": len(insert_rows),
                    "overwritten_count": overwrite_count,
                    "filled_count": fill_count,
                    "mode": import_mode,
                    "errors": task.errors[:10]  # 最多返回10个错误
                }
                
        except Exception as e:
            task.status = ScanImportStatus.FAILED
            task.completed_at = datetime.now()
            logger.exception(f"导入失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "total": task.total_rows,
                "success_count": task.success_count,
                "skipped_count": task.skipped_count,
                "failed_count": task.failed_count
            }
    
    def _convert_value(self, value: str, field: str) -> Any:
        """转换字段值为合适的数据库类型"""
        if not value or value.strip() == '':
            return None
        
        value = value.strip()
        
        if field == 'duration_seconds':
            try:
                return float(value)
            except:
                return None
        elif field == 'size_bytes':
            try:
                return int(value)
            except:
                return None
        else:
            return value

    def _normalize_md5_filename(self, filename: str) -> str:
        """标准化文件名：去扩展名、去空白、转小写"""
        if not filename:
            return ''
        name = os.path.basename(str(filename).strip())
        base = os.path.splitext(name)[0]
        return re.sub(r'\s+', '', base).lower()

    def _build_md5_match_key(self, filename: str) -> str:
        """构建宽松匹配key，兼容01/001与空格差异"""
        base = self._normalize_md5_filename(filename)
        if not base:
            return ''

        m = re.match(r'^(.*?)第(\d{1,4})集$', base)
        if m and m.group(1):
            return f"{m.group(1)}#{int(m.group(2))}"

        m = re.match(r'^(.*?)(\d{1,4})$', base)
        if m and m.group(1):
            return f"{m.group(1)}#{int(m.group(2))}"

        return base

    def _parse_shandong_md5_lines(self, content: str) -> Dict[str, str]:
        """解析山东切片结果文本，提取 文件名 -> md5"""
        records: Dict[str, str] = {}
        if not content:
            return records

        for line in content.splitlines():
            text = (line or '').strip()
            if not text:
                continue

            md5_match = re.search(r'(?i)\b([0-9a-f]{32})\b', text)
            if not md5_match:
                continue

            first_token = text.split()[0] if text.split() else ''
            file_name = os.path.basename(first_token)

            if not file_name or '.' not in file_name:
                fallback = re.search(r'([^\s/\\]+\.[A-Za-z0-9]{2,8})', text)
                file_name = fallback.group(1) if fallback else ''

            if not file_name:
                continue

            records[file_name] = md5_match.group(1).lower()

        return records

    def import_shandong_md5_file(self, file_path: str) -> Dict[str, Any]:
        """导入山东MD5文本并回填video_scan_result空md5字段"""
        content = None
        for encoding in ('utf-8-sig', 'utf-8', 'gbk'):
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except Exception:
                continue

        if content is None:
            return {"success": False, "error": "文件读取失败，无法识别编码"}

        parsed_map = self._parse_shandong_md5_lines(content)
        if not parsed_map:
            return {"success": False, "error": "未解析到有效的文件名与MD5记录"}

        try:
            with get_db() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("""
                    SELECT id, file_name, md5
                    FROM video_scan_result
                    WHERE file_name IS NOT NULL AND file_name <> ''
                """)
                rows = cursor.fetchall()

                all_keys = {}
                empty_md5_keys = {}

                for row in rows:
                    key = self._build_md5_match_key(row.get('file_name'))
                    if not key:
                        continue

                    all_keys[key] = all_keys.get(key, 0) + 1

                    md5_val = row.get('md5')
                    if md5_val is None or str(md5_val).strip() == '':
                        empty_md5_keys.setdefault(key, []).append(row['id'])

                update_rows = []
                not_found_count = 0
                skipped_existing_count = 0
                matched_count = 0

                for file_name, md5_val in parsed_map.items():
                    key = self._build_md5_match_key(file_name)
                    if not key:
                        not_found_count += 1
                        continue

                    target_ids = empty_md5_keys.get(key, [])
                    if target_ids:
                        matched_count += len(target_ids)
                        for row_id in target_ids:
                            update_rows.append((md5_val, row_id))
                    elif key in all_keys:
                        skipped_existing_count += 1
                    else:
                        not_found_count += 1

                updated_count = 0
                if update_rows:
                    cursor.executemany(
                        """
                        UPDATE video_scan_result
                        SET md5 = %s
                        WHERE id = %s AND (md5 IS NULL OR TRIM(md5) = '')
                        """,
                        update_rows
                    )
                    conn.commit()
                    updated_count = len(update_rows)

                return {
                    "success": True,
                    "data": {
                        "parsed_count": len(parsed_map),
                        "matched_count": matched_count,
                        "updated_count": updated_count,
                        "not_found_count": not_found_count,
                        "skipped_existing_count": skipped_existing_count
                    }
                }
        except Exception as e:
            logger.exception(f"山东MD5回填失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取扫描结果统计信息"""
        try:
            with get_db() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
                # 总记录数
                cursor.execute("SELECT COUNT(*) as total FROM video_scan_result")
                total = cursor.fetchone()['total']
                
                # 按来源文件夹分组统计
                cursor.execute("""
                    SELECT source_folder, COUNT(*) as count 
                    FROM video_scan_result 
                    GROUP BY source_folder 
                    ORDER BY count DESC 
                    LIMIT 20
                """)
                by_folder = cursor.fetchall()
                
                # 按剧集名分组统计（前20）
                cursor.execute("""
                    SELECT source_file, COUNT(*) as count 
                    FROM video_scan_result 
                    GROUP BY source_file 
                    ORDER BY count DESC 
                    LIMIT 20
                """)
                by_source_file = cursor.fetchall()
                
                return {
                    "success": True,
                    "data": {
                        "total": total,
                        "by_folder": by_folder,
                        "by_source_file": by_source_file
                    }
                }
        except Exception as e:
            logger.exception(f"获取统计信息失败: {e}")
            return {"success": False, "error": str(e)}
    
    def search(self, keyword: str = None, source_folder: str = None, 
               page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """查询扫描结果"""
        try:
            with get_db() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
                where_clauses = []
                params = []
                
                if keyword:
                    where_clauses.append("(file_name LIKE %s OR source_file LIKE %s)")
                    params.extend([f"%{keyword}%", f"%{keyword}%"])
                
                if source_folder:
                    where_clauses.append("source_folder = %s")
                    params.append(source_folder)
                
                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
                
                # 统计总数
                cursor.execute(f"SELECT COUNT(*) as total FROM video_scan_result {where_sql}", params)
                total = cursor.fetchone()['total']
                
                # 分页查询
                offset = (page - 1) * page_size
                cursor.execute(f"""
                    SELECT * FROM video_scan_result 
                    {where_sql}
                    ORDER BY id DESC 
                    LIMIT %s OFFSET %s
                """, params + [page_size, offset])
                items = cursor.fetchall()
                
                return {
                    "success": True,
                    "data": {
                        "list": items,
                        "total": total,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (total + page_size - 1) // page_size
                    }
                }
        except Exception as e:
            logger.exception(f"查询失败: {e}")
            return {"success": False, "error": str(e)}


# 全局服务实例
scan_result_service = ScanResultImportService()
