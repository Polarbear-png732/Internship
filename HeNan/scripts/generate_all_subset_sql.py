import pandas as pd
import pymysql
import json

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'polarbear',
    'database': 'operation_management',
    'charset': 'utf8mb4'
}

# 读取Excel文件
file_path = '运营管理平台文档.xlsx'

# 1. 建立数据库连接
print("=== 连接数据库 ===")
try:
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("数据库连接成功")
except Exception as e:
    print(f"数据库连接失败：{e}")
    exit(1)

# 2. 读取版权数据库-版权方纬度表，获取所有剧集信息
print("\n=== 读取版权数据库-版权方纬度表 ===")
try:
    copyright_df = pd.read_excel(file_path, sheet_name='版权数据库-版权方纬度')
    print(f"版权方纬度表行数：{len(copyright_df)}")
except Exception as e:
    print(f"读取版权数据库-版权方纬度表失败：{e}")
    conn.close()
    exit(1)

# 定义剧集名称到首字母缩写的映射
name_to_abbr = {
    '紧急追捕': 'jjzb',
    '悠悠寸草心Ⅱ': 'yyccx2',
    '暗夜心慌慌': 'ayxhh',
    '如果还有明天': 'rghymt',
    '走过路过莫错过': 'zglgmcg',
    '人间烟火': 'rjyh',
    '好汉一箩筐': 'hhylk',
    '今生今世': 'jsjs'
}

# 3. 生成SQL脚本
print("\n=== 生成SQL脚本 ===")
sql_script = """-- 确保客户端使用正确的字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 使用数据库
USE operation_management;

-- 所有剧集的子集表插入语句
-- drama_id从drama_main表中查询得到
"""

# 4. 查询所有剧集的drama_id，构建映射关系
print("\n=== 查询所有剧集的drama_id ===")
drama_name_to_id = {}

# 查询drama_main表中的所有数据
query = "SELECT drama_id, drama_name FROM drama_main"
try:
    cursor.execute(query)
    results = cursor.fetchall()
    print(f"查询到 {len(results)} 条剧头数据")
    
    for row in results:
        drama_id = row[0]
        drama_name = row[1]
        drama_name_to_id[drama_name] = drama_id
        print(f"  {drama_name} -> drama_id={drama_id}")
        
except Exception as e:
    print(f"查询剧头数据失败：{e}")
    conn.close()
    exit(1)

# 5. 遍历版权方纬度表中的每个剧集，生成插入语句
print("\n=== 生成子集插入语句 ===")
for index, row in copyright_df.iterrows():
    # 跳过表头或无效数据
    if pd.isna(row['序号']) or row['序号'] == '序号':
        continue
    
    try:
        # 获取剧集基本信息
        drama_name = row['介质名称']
        content_type = row['一级分类-河南标准'] if pd.notna(row['一级分类-河南标准']) else "电视剧"
        total_episodes = int(row['集数']) if pd.notna(row['集数']) else 0
        
        # 查询该剧集的实际drama_id
        if drama_name in drama_name_to_id:
            drama_id = drama_name_to_id[drama_name]
            print(f"\n处理剧集 '{drama_name}'，实际drama_id={drama_id}")
        else:
            print(f"\n警告：未找到剧集 '{drama_name}' 的drama_id，跳过处理")
            continue
        
        # 根据内容类型确定媒体路径中的目录
        if "儿童" in str(content_type):
            content_dir = "shaoer"
        elif "教育" in str(content_type):
            content_dir = "mqxt"
        elif "电竞" in str(content_type):
            content_dir = "rywg"
        else:
            content_dir = "shaoer"  # 默认使用shaoer
        
        # 获取剧集名称的首字母缩写
        if drama_name in name_to_abbr:
            abbr = name_to_abbr[drama_name]
        else:
            abbr = drama_name[:4].lower()
        
        # 生成该剧集的所有子集数据
        for episode_num in range(1, total_episodes + 1):
            # 生成节目名称
            episode_name = f"{drama_name}第{episode_num:02d}集"
            
            # 生成媒体拉取地址
            media_url = f"ftp://ftpmediazjyd:rD2q0y1M5eI@36.133.168.235:2121/media/hnyd/{content_dir}/{abbr}/{abbr}{episode_num:03d}.ts"
            
            # 构建dynamic_properties JSON
            dynamic_props = {
                '子集id': None,
                '媒体拉取地址': media_url,
                '媒体类型': 1,  # 正片
                '编码格式': 1,  # H.264
                '集数': episode_num,
                '时长': 18000,  # 默认时长，实际需要根据视频确定
                '文件大小': 120000000  # 默认文件大小，实际需要根据视频确定
            }
            
            # 生成JSON字符串，每个属性一行
            json_lines = ['{']
            for key, value in dynamic_props.items():
                if value is None:
                    json_value = 'null'
                elif isinstance(value, str):
                    json_value = f'"{value}"'
                elif isinstance(value, (int, float)):
                    json_value = str(value)
                else:
                    json_value = str(value)
                json_lines.append(f'    "{key}": {json_value},')
            
            # 移除最后一个逗号
            if json_lines[-1].endswith(','):
                json_lines[-1] = json_lines[-1][:-1]
            json_lines.append('}')
            
            json_str = '\n'.join(json_lines)
            
            # 生成SQL语句
            sql_statement = f"INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (\n    {drama_id},\n    '{episode_name}',\n    '{json_str}'\n);\n"
            
            sql_script += sql_statement + "\n"
        
        print(f"  已为剧集 '{drama_name}' 生成 {total_episodes} 条子集插入语句，使用缩写 '{abbr}'")
        
    except Exception as e:
        print(f"  处理剧集 '{drama_name}' 时出错：{e}")
        continue

# 6. 保存SQL脚本
output_file = 'sql/insert_all_subset_data.sql'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(sql_script)

# 7. 关闭数据库连接
conn.close()
print(f"\n=== SQL脚本生成完成 ===")
print(f"SQL脚本已保存到 {output_file}")
print("数据库连接已关闭")
print("\n=== 脚本执行完成 ===")