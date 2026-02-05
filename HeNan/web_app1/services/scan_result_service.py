"""
视频扫描结果导入服务
实现多种表格格式解析（CSV/Excel）、批量插入数据库、增量导入等功能
"""
import csv
import os
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
    
    def import_data(self, task: ScanImportTask, records: List[Dict], mode: str = "incremental") -> Dict[str, Any]:
        """
        导入数据到数据库（仅支持增量模式，跳过重复记录）
        """
        task.status = ScanImportStatus.RUNNING
        
        try:
            with get_db() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
                # 增量模式：获取已存在的记录
                existing_keys = self.get_existing_keys(cursor)
                logger.info(f"增量模式：数据库已有 {len(existing_keys)} 条记录")
                
                # 过滤新记录
                new_records = []
                for record in records:
                    key = f"{record.get('file_name', '')}|{record.get('source_folder', '')}"
                    if key not in existing_keys:
                        new_records.append(record)
                    else:
                        task.skipped_count += 1
                
                logger.info(f"待插入: {len(new_records)} 条，跳过重复: {task.skipped_count} 条")
                
                if not new_records:
                    task.status = ScanImportStatus.COMPLETED
                    task.completed_at = datetime.now()
                    return {
                        "success": True,
                        "message": "所有记录已存在，无需导入",
                        "total": task.total_rows,
                        "success_count": 0,
                        "skipped_count": task.skipped_count,
                        "failed_count": 0
                    }
                
                # 构建批量插入SQL
                insert_sql = f"""
                    INSERT INTO video_scan_result 
                    ({', '.join(self.INSERT_FIELDS)})
                    VALUES ({', '.join(['%s'] * len(self.INSERT_FIELDS))})
                """
                
                # 分批插入
                batch_values = []
                for i, record in enumerate(new_records):
                    values = tuple(
                        self._convert_value(record.get(field, ''), field)
                        for field in self.INSERT_FIELDS
                    )
                    batch_values.append(values)
                    
                    # 达到批次大小或最后一批
                    if len(batch_values) >= self.BATCH_SIZE or i == len(new_records) - 1:
                        try:
                            cursor.executemany(insert_sql, batch_values)
                            conn.commit()
                            task.success_count += len(batch_values)
                            task.processed_rows += len(batch_values)
                            logger.info(f"已插入 {task.processed_rows}/{len(new_records)} 条")
                        except Exception as e:
                            task.failed_count += len(batch_values)
                            task.errors.append({
                                "batch": i // self.BATCH_SIZE + 1,
                                "error": str(e)
                            })
                            logger.error(f"批次插入失败: {e}")
                        batch_values = []
                
                task.status = ScanImportStatus.COMPLETED
                task.completed_at = datetime.now()
                
                return {
                    "success": True,
                    "message": "导入完成",
                    "total": task.total_rows,
                    "success_count": task.success_count,
                    "skipped_count": task.skipped_count,
                    "failed_count": task.failed_count,
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
    
    def clear_all(self) -> Dict[str, Any]:
        """清空所有扫描结果"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM video_scan_result")
                count = cursor.fetchone()[0]
                
                cursor.execute("TRUNCATE TABLE video_scan_result")
                conn.commit()
                
                logger.info(f"已清空 video_scan_result 表，删除 {count} 条记录")
                return {
                    "success": True,
                    "message": f"已清空 {count} 条记录"
                }
        except Exception as e:
            logger.exception(f"清空表失败: {e}")
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
