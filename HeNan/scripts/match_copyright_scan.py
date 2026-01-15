"""
匹配版权方数据表和视频扫描结果表
"""
import pandas as pd
import pymysql
import re

# 读取版权方数据表
copyright_df = pd.read_excel('tables/河南移动版权方数据表.xlsx')
media_names = copyright_df['介质名称'].dropna().unique().tolist()

# 连接数据库
conn = pymysql.connect(host='localhost', user='root', password='polarbear', database='operation_management', charset='utf8mb4')
cursor = conn.cursor()
# 查询source_file和source_folder
cursor.execute('SELECT DISTINCT source_file, source_folder FROM video_scan_result WHERE source_file IS NOT NULL')
scan_results = cursor.fetchall()
# 构建 source_file -> source_folder 的映射
scan_files = [row[0] for row in scan_results]
scan_folder_map = {row[0]: row[1] for row in scan_results}

def normalize(name):
    """标准化名称"""
    s = str(name).strip()
    # 中文数字转阿拉伯数字
    cn_map = {'一':'1','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9'}
    for cn, ar in cn_map.items():
        s = s.replace(f'第{cn}季', f' 第{ar}季')
        s = s.replace(f'第{cn}部', f' 第{ar}部')
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()

def get_base_name(name):
    """提取剧集基础名称"""
    s = normalize(name)
    s = re.sub(r'\s*第\d+季.*', '', s)
    s = re.sub(r'\s*第\d+部.*', '', s)
    s = re.sub(r'\s*全集.*', '', s)
    s = re.sub(r'\s*（.*）', '', s)
    s = re.sub(r'\s*\(.*\)', '', s)
    return s.strip()

# 构建扫描文件映射
scan_norm_map = {normalize(f): f for f in scan_files}
scan_base_map = {}
for f in scan_files:
    base = get_base_name(f)
    if base and len(base) >= 2:
        if base not in scan_base_map:
            scan_base_map[base] = []
        scan_base_map[base].append(f)

found_exact = []
found_base = []
not_found = []

for name in media_names:
    name_str = str(name).strip()
    name_norm = normalize(name_str)
    name_base = get_base_name(name_str)
    
    # 精确匹配
    if name_norm in scan_norm_map:
        matched_file = scan_norm_map[name_norm]
        matched_folder = scan_folder_map.get(matched_file, '')
        found_exact.append((name_str, matched_file, matched_folder))
        continue
    
    # 基础名称匹配
    if name_base in scan_base_map and len(name_base) >= 3:
        matched_file = scan_base_map[name_base][0]
        matched_folder = scan_folder_map.get(matched_file, '')
        found_base.append((name_str, matched_file, matched_folder, name_base))
        continue
    
    # 基础名称包含匹配
    matched = False
    for base, files in scan_base_map.items():
        if len(name_base) >= 4 and len(base) >= 4:
            if name_base in base or base in name_base:
                matched_file = files[0]
                matched_folder = scan_folder_map.get(matched_file, '')
                found_base.append((name_str, matched_file, matched_folder, f'{name_base}~{base}'))
                matched = True
                break
    
    if not matched:
        not_found.append(name_str)

total_matched = len(found_exact) + len(found_base)
print(f'匹配结果统计:')
print(f'  精确匹配: {len(found_exact)} 个')
print(f'  基础名称匹配: {len(found_base)} 个')
print(f'  总匹配: {total_matched} 个')
print(f'  未匹配: {len(not_found)} 个')
print(f'  匹配率: {total_matched / len(media_names) * 100:.1f}%')

# 导出到Excel
print('\n正在导出匹配结果到Excel...')

# 精确匹配表
exact_df = pd.DataFrame(found_exact, columns=['版权方介质名称', '扫描结果文件名', '来源文件夹'])
exact_df.to_excel('tables/匹配结果_精确匹配.xlsx', index=False)
print(f'  精确匹配结果已保存到: tables/匹配结果_精确匹配.xlsx ({len(found_exact)} 条)')

# 基础名称匹配表
base_df = pd.DataFrame(found_base, columns=['版权方介质名称', '扫描结果文件名', '来源文件夹', '匹配基础名称'])
base_df.to_excel('tables/匹配结果_基础名称匹配.xlsx', index=False)
print(f'  基础名称匹配结果已保存到: tables/匹配结果_基础名称匹配.xlsx ({len(found_base)} 条)')

# 未匹配表
not_found_df = pd.DataFrame(not_found, columns=['版权方介质名称'])
not_found_df.to_excel('tables/匹配结果_未匹配.xlsx', index=False)
print(f'  未匹配结果已保存到: tables/匹配结果_未匹配.xlsx ({len(not_found)} 条)')

print('\n导出完成!')

cursor.close()
conn.close()
