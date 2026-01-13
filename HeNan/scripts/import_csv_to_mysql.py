"""
将 scan_result_merged.csv 导入 MySQL 数据库
"""

import pandas as pd
import pymysql
from pathlib import Path

# 数据库配置（与 web_app1 一致）
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'polarbear',
    'database': 'operation_management',
    'charset': 'utf8mb4'
}

# CSV 文件路径（相对于脚本所在目录的上级）
SCRIPT_DIR = Path(__file__).parent
CSV_FILE = SCRIPT_DIR.parent / "tables" / "scan_result_merged.csv"

# 建表 SQL
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS video_scan_result (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_folder VARCHAR(255) COMMENT '来源文件夹',
    source_file VARCHAR(255) COMMENT '来源文件（剧集名）',
    file_name VARCHAR(500) COMMENT '文件名称',
    duration_seconds DECIMAL(10,2) COMMENT '时长（秒）',
    duration_formatted VARCHAR(20) COMMENT '时长格式化',
    size_bytes BIGINT COMMENT '大小（字节）',
    size_kb DECIMAL(15,2) COMMENT '大小（KB）',
    size_mb DECIMAL(15,2) COMMENT '大小（MB）',
    INDEX idx_source_file (source_file),
    INDEX idx_file_name (file_name(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频扫描结果';
"""

def import_csv():
    print("=" * 60)
    print("CSV 导入 MySQL 工具")
    print("=" * 60)
    print()
    
    # 读取 CSV
    print(f"正在读取 {CSV_FILE} ...")
    df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    print(f"读取完成，共 {len(df)} 行数据")
    print()
    
    # 重命名列以匹配数据库字段
    df.columns = ['source_folder', 'source_file', 'file_name', 'duration_seconds', 
                  'duration_formatted', 'size_bytes', 'size_kb', 'size_mb']
    
    # 连接数据库
    print("正在连接数据库...")
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 创建表（如果不存在）
    print("正在创建表...")
    cursor.execute("DROP TABLE IF EXISTS video_scan_result")
    cursor.execute(CREATE_TABLE_SQL)
    conn.commit()
    print("表创建成功")
    print()
    
    # 批量插入数据
    print("正在导入数据...")
    insert_sql = """
        INSERT INTO video_scan_result 
        (source_folder, source_file, file_name, duration_seconds, duration_formatted, size_bytes, size_kb, size_mb)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    batch_size = 1000
    total = len(df)
    
    for i in range(0, total, batch_size):
        batch = df.iloc[i:i+batch_size]
        data = [tuple(row) for row in batch.values]
        cursor.executemany(insert_sql, data)
        conn.commit()
        print(f"已导入 {min(i + batch_size, total)}/{total} 行")
    
    conn.close()
    
    print()
    print("=" * 60)
    print(f"导入完成！共 {total} 条记录")
    print("表名: video_scan_result")
    print()
    print("查询示例:")
    print("  SELECT * FROM video_scan_result WHERE source_file = '某剧集名';")
    print("  SELECT * FROM video_scan_result WHERE file_name LIKE '%第1集%';")
    print("=" * 60)


if __name__ == "__main__":
    import_csv()
