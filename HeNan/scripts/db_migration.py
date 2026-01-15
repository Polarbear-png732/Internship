"""数据库迁移脚本 - 多客户支持"""
import pymysql

def run_migration():
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='polarbear',
        database='operation_management',
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    
    # 1. drama_main 表增加 customer_code 字段
    try:
        cursor.execute('''
            ALTER TABLE drama_main 
            ADD COLUMN customer_code VARCHAR(50) DEFAULT 'henan_mobile' COMMENT '客户代码'
        ''')
        print('✓ drama_main 添加 customer_code 字段成功')
    except Exception as e:
        if 'Duplicate column' in str(e):
            print('○ drama_main.customer_code 字段已存在')
        else:
            print(f'✗ 错误: {e}')
    
    # 2. 添加索引
    try:
        cursor.execute('ALTER TABLE drama_main ADD INDEX idx_customer_code (customer_code)')
        print('✓ 添加 idx_customer_code 索引成功')
    except Exception as e:
        if 'Duplicate key' in str(e):
            print('○ idx_customer_code 索引已存在')
        else:
            print(f'○ 索引: {e}')
    
    # 3. 检查 copyright_content 表结构
    cursor.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'operation_management' 
        AND TABLE_NAME = 'copyright_content' 
        AND COLUMN_NAME IN ('drama_id', 'drama_ids')
    """)
    columns = [row[0] for row in cursor.fetchall()]
    
    import json
    
    if 'drama_ids' in columns:
        print('○ copyright_content.drama_ids 字段已存在')
    elif 'drama_id' in columns:
        # 需要迁移：先备份数据
        cursor.execute("SELECT id, drama_id FROM copyright_content WHERE drama_id IS NOT NULL")
        old_data = cursor.fetchall()
        
        # 先删除外键约束
        try:
            cursor.execute('ALTER TABLE copyright_content DROP FOREIGN KEY fk_copyright_drama')
            print('✓ 删除外键约束 fk_copyright_drama')
        except Exception as e:
            print(f'○ 外键: {e}')
        
        # 删除旧字段，添加新字段
        cursor.execute('ALTER TABLE copyright_content DROP COLUMN drama_id')
        cursor.execute('''
            ALTER TABLE copyright_content 
            ADD COLUMN drama_ids JSON COMMENT '各客户的剧头ID'
        ''')
        print('✓ copyright_content.drama_id 改为 drama_ids (JSON) 成功')
        
        # 迁移旧数据
        for row_id, drama_id in old_data:
            if drama_id:
                new_value = json.dumps({'henan_mobile': drama_id})
                cursor.execute(
                    "UPDATE copyright_content SET drama_ids = %s WHERE id = %s",
                    (new_value, row_id)
                )
        print(f'✓ 迁移了 {len(old_data)} 条旧数据')
    else:
        print('○ copyright_content 表无 drama_id/drama_ids 字段')
    
    conn.commit()
    conn.close()
    print('\n数据库迁移完成')

if __name__ == '__main__':
    run_migration()
