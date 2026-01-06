import pandas as pd
import os

# 读取Excel文件
file_path = '运营管理平台文档.xlsx'

# 读取版权数据库-版权方纬度表
try:
    copyright_df = pd.read_excel(file_path, sheet_name='版权数据库-版权方纬度')
    print("=== 版权数据库-版权方纬度表信息 ===")
    print(f"行数：{len(copyright_df)}")
    print(f"列名：{copyright_df.columns.tolist()}")
except Exception as e:
    print(f"读取版权数据库-版权方纬度表失败：{e}")
    exit(1)

# 定义剧头信息的字段顺序
field_order = [
    '作者列表', '清晰度', '语言', '主演', '内容类型', '上映年份',
    '关键字', '评分', '推荐语', '总集数', '产品分类', '竖图', '描述',
    '横图', '版权', '二级分类'
]

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

# 生成SQL脚本
print("\n=== 生成SQL脚本 ===")
sql_script = """-- 确保客户端使用正确的字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 使用数据库
USE operation_management;

-- 从版权数据库-版权方纬度表生成的插入语句
"""

# 遍历每条数据
for index, row in copyright_df.iterrows():
    # 跳过表头或无效数据
    if pd.isna(row['序号']) or row['序号'] == '序号':
        continue
    
    # 获取剧集名称
    drama_name = row['介质名称']
    if pd.isna(drama_name):
        continue
    
    # 1. 作者列表：匹配导演字段，若为空则使用"暂无"
    author_list = row['导演'] if pd.notna(row['导演']) else "暂无"
    
    # 3. 清晰度：默认为1（高清）
    clarity = 1
    
    # 4. 语言：匹配语言-河南标准，若无则使用语言字段
    language = row['语言-河南标准'] if pd.notna(row['语言-河南标准']) else row['语言'] if pd.notna(row['语言']) else "简体中文"
    
    # 5. 主演：匹配主演\嘉宾\主持人字段
    actors = row['主演\嘉宾\主持人'] if pd.notna(row['主演\嘉宾\主持人']) else ""
    
    # 6. 内容类型：匹配一级分类-河南标准，若无则默认
    content_type = row['一级分类-河南标准'] if pd.notna(row['一级分类-河南标准']) else "电视剧"
    
    # 7. 上映年份：匹配出品年代字段
    release_year = int(row['出品年代']) if pd.notna(row['出品年代']) else None
    
    # 8. 关键字：匹配关键字字段
    keywords = row['关键字'] if pd.notna(row['关键字']) else ""
    
    # 9. 评分：匹配行业内相关网站的评级、评分字段
    rating = row['行业内相关网站的评级、评分（骨朵\\艺恩\\猫眼\\豆瓣\\时光网\\百度\\其他主流视频网站等评分']
    if pd.notna(rating):
        try:
            rating = float(rating)
        except ValueError:
            rating = None
    else:
        rating = None
    
    # 10. 推荐语：匹配推荐语/一句话介绍字段
    recommendation = row['推荐语/一句话介绍'] if pd.notna(row['推荐语/一句话介绍']) else ""
    
    # 11. 总集数：匹配集数字段
    total_episodes = int(row['集数']) if pd.notna(row['集数']) else 0
    
    # 12. 产品分类：根据内容类型生成
    # 1.如果【内容类型】是【教育】则输出1；2.如果【内容类型】是【电竞】，则输出2；3.其他则输出3
    product_category = 3  # 默认值
    if pd.notna(content_type):
        content_type_lower = str(content_type).lower()
        if "教育" in content_type_lower:
            product_category = 1
        elif "电竞" in content_type_lower:
            product_category = 2
    
    # 13. 竖图：根据剧集名称生成URL
    # http://36.133.168.235:18181/img/剧集名称的首字母_st.jpg
    # 使用name_to_abbr映射获取正确的缩写
    abbr = name_to_abbr.get(drama_name, drama_name[0].lower() if drama_name else "")
    vertical_image = f"http://36.133.168.235:18181/img/{abbr}_st.jpg"
    
    # 14. 描述：匹配简介字段
    description = row['简介'] if pd.notna(row['简介']) else ""
    
    # 15. 横图：根据剧集名称生成URL
    # http://36.133.168.235:18181/img/剧集名称的首字母_ht.jpg
    horizontal_image = f"http://36.133.168.235:18181/img/{abbr}_ht.jpg"
    
    # 16. 版权：默认为1
    copyright = 1
    
    # 17. 二级分类：匹配二级分类-河南标准字段
    secondary_category = row['二级分类-河南标准'] if pd.notna(row['二级分类-河南标准']) else ""
    
    # 构建dynamic_properties字典，按照指定顺序
    dynamic_props = {
        '作者列表': author_list,
        '清晰度': clarity,
        '语言': language,
        '主演': actors,
        '内容类型': content_type,
        '上映年份': release_year,
        '关键字': keywords,
        '评分': rating,
        '推荐语': recommendation,
        '总集数': total_episodes,
        '产品分类': product_category,
        '竖图': vertical_image,
        '描述': description,
        '横图': horizontal_image,
        '版权': copyright,
        '二级分类': secondary_category
    }
    
    # 生成JSON字符串，格式化格式，每个属性一行，适合MySQL
    json_lines = ['{']
    for field in field_order:
        value = dynamic_props[field]
        if value is None:
            json_value = 'null'
        elif isinstance(value, str):
            # 转义字符串中的双引号
            json_value = f'"{value.replace("\"", "\\\"")}"'
        elif isinstance(value, (int, float)):
            json_value = str(value)
        else:
            json_value = str(value)
        json_lines.append(f'    "{field}": {json_value},')
    
    # 移除最后一个逗号
    if json_lines[-1].endswith(','):
        json_lines[-1] = json_lines[-1][:-1]
    json_lines.append('}')
    
    json_str = '\n'.join(json_lines)
    
    # 生成SQL语句，JSON字符串必须用单引号包裹
    sql_statement = f"INSERT INTO drama_main (drama_name, dynamic_properties) VALUES (\n    '{drama_name}',\n    '{json_str}'\n);\n"
    
    sql_script += sql_statement + "\n"

# 保存SQL脚本
output_file = 'sql/insert_copyright_data.sql'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(sql_script)

print(f"\n=== SQL脚本生成完成 ===")
print(f"SQL脚本已保存到 {output_file}")
print(f"共生成 {len(copyright_df)} 条插入语句")
print("\n=== 脚本执行完成 ===")