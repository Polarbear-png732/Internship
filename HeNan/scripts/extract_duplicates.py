"""
提取Excel中的重复数据

重复数据的判定逻辑（与导入功能一致）：
1. Excel内部重复：同一个"介质名称"出现多次，保留第一次，后续的都是重复
2. 数据库已存在：介质名称在 copyright_content 表中已存在

用法:
    python extract_duplicates.py <Excel文件路径>
    
示例:
    python extract_duplicates.py ../tables/版权方数据表.xlsx
"""
import sys
import os
import pandas as pd
import pymysql

# 添加父目录到路径，以便导入 web_app1 的配置
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_app1'))

from config import DB_CONFIG


def get_existing_names_from_db():
    """从数据库获取已存在的介质名称"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT media_name FROM copyright_content")
        existing = {row[0] for row in cursor.fetchall()}
        conn.close()
        return existing
    except Exception as e:
        print(f"⚠️ 无法连接数据库: {e}")
        print("将只检测Excel内部重复，不检测数据库已存在的数据")
        return set()


def extract_duplicates(excel_path: str):
    """提取重复数据并输出到新Excel"""
    
    if not os.path.exists(excel_path):
        print(f"❌ 文件不存在: {excel_path}")
        return
    
    print(f"📂 正在读取: {excel_path}")
    df = pd.read_excel(excel_path)
    
    # 查找介质名称列
    media_col = None
    for col in df.columns:
        if '介质名称' in str(col):
            media_col = col
            break
    
    if media_col is None:
        print("❌ 未找到'介质名称'列")
        return
    
    print(f"✅ 找到介质名称列: {media_col}")
    print(f"📊 总行数: {len(df)}")
    
    # 获取数据库已存在的名称
    existing_in_db = get_existing_names_from_db()
    print(f"📦 数据库中已存在: {len(existing_in_db)} 个介质名称")
    
    # 分类数据
    name_occurrences = {}  # {介质名称: [行索引列表]}
    empty_name_rows = []   # 介质名称为空
    
    for idx, row in df.iterrows():
        media_name = str(row[media_col]).strip() if pd.notna(row[media_col]) else ''
        
        if not media_name or media_name == 'nan':
            empty_name_rows.append(row)
        else:
            if media_name not in name_occurrences:
                name_occurrences[media_name] = []
            name_occurrences[media_name].append(idx)
    
    # 分离唯一数据和重复数据
    unique_rows = []           # 唯一数据（只出现一次且不在数据库中）
    duplicate_groups = []      # 重复数据（出现多次的，包含所有重复项）
    db_duplicates = []         # 数据库已存在
    
    for media_name, indices in name_occurrences.items():
        if media_name in existing_in_db:
            # 数据库已存在
            for idx in indices:
                db_duplicates.append(df.loc[idx])
        elif len(indices) > 1:
            # Excel内部重复 - 把所有重复的都加入
            for idx in indices:
                row = df.loc[idx].copy()
                row['重复次数'] = len(indices)
                duplicate_groups.append(row)
        else:
            # 唯一数据
            unique_rows.append(df.loc[indices[0]])
    
    # 统计重复的介质名称数量
    duplicate_media_count = sum(1 for indices in name_occurrences.values() if len(indices) > 1)
    duplicate_row_count = sum(len(indices) for indices in name_occurrences.values() if len(indices) > 1)
    
    # 输出统计
    print("\n" + "="*50)
    print("📊 数据分析结果:")
    print("="*50)
    print(f"  ✅ 唯一有效数据:     {len(unique_rows)} 行")
    print(f"  🔄 Excel内部重复:   {duplicate_row_count} 行 ({duplicate_media_count} 个介质名称有重复)")
    print(f"  📦 数据库已存在:     {len(db_duplicates)} 行")
    print(f"  ⚠️ 介质名称为空:     {len(empty_name_rows)} 行")
    print("="*50)
    
    # 生成输出文件
    base_name = os.path.splitext(excel_path)[0]
    output_dir = os.path.dirname(excel_path)
    
    # 使用 xlsxwriter 创建带多个sheet的Excel
    output_path = f"{base_name}_重复数据分析.xlsx"
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: 唯一有效数据
        if unique_rows:
            pd.DataFrame(unique_rows).to_excel(writer, sheet_name='唯一有效数据', index=False)
        
        # Sheet 2: Excel内部重复（包含所有重复项，按介质名称排序）
        if duplicate_groups:
            dup_df = pd.DataFrame(duplicate_groups)
            # 按介质名称排序，让相同名称的放在一起
            dup_df = dup_df.sort_values(by=[media_col])
            dup_df.to_excel(writer, sheet_name='Excel内部重复', index=False)
        
        # Sheet 3: 数据库已存在
        if db_duplicates:
            pd.DataFrame(db_duplicates).to_excel(writer, sheet_name='数据库已存在', index=False)
        
        # Sheet 4: 介质名称为空
        if empty_name_rows:
            pd.DataFrame(empty_name_rows).to_excel(writer, sheet_name='介质名称为空', index=False)
        
        # Sheet 5: 重复统计摘要
        summary_data = {
            '类别': ['唯一有效数据', 'Excel内部重复(行数)', 'Excel内部重复(介质数)', '数据库已存在', '介质名称为空', '原始总行数'],
            '数量': [len(unique_rows), duplicate_row_count, duplicate_media_count, len(db_duplicates), len(empty_name_rows), len(df)]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='统计摘要', index=False)
    
    print(f"\n📁 已生成分析文件: {output_path}")
    print("\n包含以下Sheet:")
    print("  1. 唯一有效数据 - 可以正常导入的数据")
    print("  2. Excel内部重复 - 同一介质名称在Excel中出现多次")
    print("  3. 数据库已存在 - 介质名称已在数据库中")
    print("  4. 介质名称为空 - 缺少介质名称的行")
    print("  5. 统计摘要 - 各类数据统计")


def main():
    if len(sys.argv) < 2:
        # 默认处理 tables/版权方数据表.xlsx
        default_path = os.path.join(os.path.dirname(__file__), '..', 'tables', '版权方数据表.xlsx')
        if os.path.exists(default_path):
            extract_duplicates(default_path)
        else:
            print("用法: python extract_duplicates.py <Excel文件路径>")
            print("示例: python extract_duplicates.py ../tables/版权方数据表.xlsx")
    else:
        extract_duplicates(sys.argv[1])


if __name__ == '__main__':
    main()
