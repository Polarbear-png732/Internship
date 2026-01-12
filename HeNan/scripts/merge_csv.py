"""
合并 scan_result 文件夹内所有 Excel 文件到一个 CSV 文件中
"""

import os
import pandas as pd
from pathlib import Path

# 源目录和输出文件
SOURCE_DIR = Path("scan_result")
OUTPUT_FILE = Path("scan_result_merged.csv")

def find_all_excel_files(root_dir: Path) -> list:
    """递归查找所有 Excel 文件"""
    excel_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.xlsx') and not filename.startswith('~$'):
                excel_files.append(Path(dirpath) / filename)
    return excel_files

def merge_to_csv():
    print("=" * 60)
    print("Excel 文件合并工具 (CSV 输出)")
    print("=" * 60)
    print()
    
    # 查找所有 Excel 文件
    print(f"正在扫描 {SOURCE_DIR} ...")
    excel_files = find_all_excel_files(SOURCE_DIR)
    print(f"找到 {len(excel_files)} 个 Excel 文件")
    print()
    
    if not excel_files:
        print("没有找到任何 Excel 文件")
        return
    
    # 合并所有数据
    all_data = []
    success_count = 0
    fail_count = 0
    
    for i, file_path in enumerate(excel_files, 1):
        try:
            relative_path = file_path.relative_to(SOURCE_DIR)
            folder_name = relative_path.parent
            file_name = file_path.stem
            
            df = pd.read_excel(file_path, engine='openpyxl')
            
            if df.empty:
                print(f"[{i}/{len(excel_files)}] 跳过空文件: {relative_path}")
                fail_count += 1
                continue
            
            df.insert(0, '来源文件夹', str(folder_name))
            df.insert(1, '来源文件', file_name)
            
            all_data.append(df)
            print(f"[{i}/{len(excel_files)}] 已读取: {relative_path} ({len(df)} 行)")
            success_count += 1
            
        except Exception as e:
            print(f"[{i}/{len(excel_files)}] 读取失败: {file_path} - {e}")
            fail_count += 1
    
    print()
    
    if not all_data:
        print("没有成功读取任何数据")
        return
    
    # 合并所有数据
    print("正在合并数据...")
    merged_df = pd.concat(all_data, ignore_index=True)
    print(f"合并完成，共 {len(merged_df)} 行数据")
    
    # 保存到 CSV 文件（UTF-8 with BOM，Excel 可正确显示中文）
    print(f"正在保存到 {OUTPUT_FILE} ...")
    merged_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    # 显示文件大小
    file_size = OUTPUT_FILE.stat().st_size
    if file_size > 1024 * 1024:
        size_str = f"{file_size / 1024 / 1024:.2f} MB"
    else:
        size_str = f"{file_size / 1024:.2f} KB"
    
    print()
    print("=" * 60)
    print(f"合并完成！")
    print(f"成功: {success_count}, 失败/跳过: {fail_count}")
    print(f"输出文件: {OUTPUT_FILE}")
    print(f"文件大小: {size_str}")
    print(f"总行数: {len(merged_df)}")
    print("=" * 60)


if __name__ == "__main__":
    merge_to_csv()
