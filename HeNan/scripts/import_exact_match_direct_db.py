"""
直接通过数据库批量导入精确匹配的版权方数据
功能：
1. 读取 tables/匹配结果_精确匹配.xlsx
2. 连接本地 MySQL 数据库
3. 检查数据库中已存在的介质名称，自动跳过
4. 执行插入操作（同时创建 copyright_content, drama_main, drama_episode）
5. 修复了速度慢的问题，直接操作数据库
"""

import pandas as pd
import pymysql
import json
import os
import sys
from pypinyin import pinyin, Style
from datetime import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'polarbear',
    'database': 'operation_management',
    'charset': 'utf8mb4'
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def clean_value(val):
    """清理值，处理NaN和特殊类型"""
    if pd.isna(val) or val == 'nan':
        return None
    if isinstance(val, pd.Timestamp):
        return val.strftime('%Y-%m-%d')
    return val

def get_pinyin_abbr(name):
    """生成拼音首字母缩写"""
    if not name:
        return ""
    result = []
    for char in name:
        if '\u4e00' <= char <= '\u9fff':  # 中文字符
            py = pinyin(char, style=Style.FIRST_LETTER)
            if py and py[0]:
                result.append(py[0][0])
        elif char.isalnum():  # 数字和字母保留
            result.append(char.lower())
    return ''.join(result)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # 文件路径
    exact_match_path = os.path.join(base_dir, '../tables/匹配结果_精确匹配.xlsx')
    copyright_data_path = os.path.join(base_dir, '../tables/河南移动版权方数据表.xlsx')
    
    if not os.path.exists(exact_match_path) or not os.path.exists(copyright_data_path):
        print("Error: Excel files not found.")
        return

    print('读取精确匹配结果...')
    exact_match_df = pd.read_excel(exact_match_path)
    exact_names = set(exact_match_df['版权方介质名称'].astype(str).tolist())
    print(f'  精确匹配数量: {len(exact_names)} 个')

    print('读取版权方数据表...')
    copyright_df = pd.read_excel(copyright_data_path)
    
    # 筛选
    matched_df = copyright_df[copyright_df['介质名称'].isin(exact_names)].copy()
    print(f'  筛选出待处理数据: {len(matched_df)} 条')

    # 列名映射
    column_mapping = {
        '序号': 'serial_number',
        '上游版权方': 'upstream_copyright',
        '介质名称': 'media_name',
        '一级分类': 'category_level1',
        '一级分类-河南标准': 'category_level1_henan',
        '二级分类-河南标准': 'category_level2_henan',
        '集数': 'episode_count',
        '单集时长': 'single_episode_duration',
        '总时长': 'total_duration',
        '出品年代': 'production_year',
        '授权区域（全国/单独沟通）': 'authorization_region',
        '授权平台（IPTV、OTT、小屏、待沟通）': 'authorization_platform',
        '合作方式（采买/分成）': 'cooperation_mode',
        '制作地区': 'production_region',
        '语言': 'language',
        '语言-河南标准': 'language_henan',
        '国别': 'country',
        '导演': 'director',
        '编剧': 'screenwriter',
        '主演\\嘉宾\\主持人': 'cast_members',
        '推荐语/一句话介绍': 'recommendation',
        '简介': 'synopsis',
        '关键字': 'keywords',
        '标清\\高清\\4K\\3D\\杜比': 'video_quality',
        '发行许可编号\\备案号等': 'license_number',
        '行业内相关网站的评级、评分（骨朵\\艺恩\\猫眼\\豆瓣\\时光网\\百度\\其他主流视频网站等评分': 'rating',
        '独家\\非独': 'exclusive_status',
        '版权开始时间': 'copyright_start_date',
        '版权结束时间': 'copyright_end_date'
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 0. 预加载视频扫描结果到内存 (极大提升速度)
        print("预加载视频扫描结果到内存...")
        cursor.execute("SELECT standard_episode_name, duration_formatted, size_bytes FROM video_scan_result WHERE standard_episode_name IS NOT NULL")
        scan_results = cursor.fetchall()
        scan_map = {}
        for r in scan_results:
            # 建立映射: 标准化名称 -> (时长, 大小)
            scan_map[r['standard_episode_name']] = {
                'duration': r['duration_formatted'],
                'size': r['size_bytes']
            }
        print(f"  已加载 {len(scan_map)} 条扫描结果到内存")
        
        # 1. 检查已存在的数据
        print("检查数据库中已存在的数据...")
        cursor.execute("SELECT media_name FROM copyright_content")
        existing_names = set(row['media_name'] for row in cursor.fetchall())
        print(f"  数据库中已存在 {len(existing_names)} 条版权数据")
        
        # 过滤
        to_process = []
        for _, row in matched_df.iterrows():
            media_name = clean_value(row['介质名称'])
            if media_name and media_name not in existing_names:
                to_process.append(row)
            # 简单去重，防止Excel里自身有重复
            existing_names.add(media_name)
            
        print(f"  剩余需插入数据: {len(to_process)} 条")
        
        if not to_process:
            print("没有新数据需要插入。")
            return

        print("开始插入数据...")
        success_count = 0
        error_count = 0
        
        # 批量处理
        for i, row in enumerate(to_process):
            try:
                # 准备数据字典
                data = {}
                for cn_key, en_key in column_mapping.items():
                    if cn_key in row:
                        data[en_key] = clean_value(row[cn_key])
                
                media_name = data.get('media_name')
                if not media_name:
                    continue
                    
                # === 逻辑复刻 create_copyright ===
                
                # 1. 创建剧头
                author_list = data.get('director') or "暂无"
                language = data.get('language_henan') or data.get('language') or "简体中文"
                actors = data.get('cast_members') or ""
                content_type = data.get('category_level1_henan') or "电视剧"
                
                release_year = None
                if data.get('production_year'):
                    try:
                        release_year = int(data['production_year']) 
                    except: 
                        pass
                
                keywords = data.get('keywords') or ""
                
                rating = None
                if data.get('rating'):
                    try:
                        rating = float(data['rating'])
                    except:
                        pass
                
                recommendation = data.get('recommendation') or ""
                
                total_episodes = 0
                if data.get('episode_count'):
                    try:
                        total_episodes = int(data['episode_count'])
                    except:
                        pass
                        
                description = data.get('synopsis') or ""
                secondary_category = data.get('category_level2_henan') or ""
                
                # 产品分类
                product_category = 3
                if content_type:
                    ctype_str = str(content_type)
                    if "教育" in ctype_str:
                        product_category = 1
                    elif "电竞" in ctype_str:
                        product_category = 2

                abbr = get_pinyin_abbr(media_name)
                vertical_image = f"http://36.133.168.235:18181/img/{abbr}_st.jpg"
                horizontal_image = f"http://36.133.168.235:18181/img/{abbr}_ht.jpg"
                
                dynamic_props = {
                    '作者列表': author_list,
                    '清晰度': 1,
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
                    '版权': 1,
                    '二级分类': secondary_category
                }
                
                # 插入 drama_main
                drama_insert = "INSERT INTO drama_main (customer_id, drama_name, dynamic_properties) VALUES (NULL, %s, %s)"
                cursor.execute(drama_insert, (media_name, json.dumps(dynamic_props, ensure_ascii=False)))
                new_drama_id = cursor.lastrowid
                
                # 2. 创建子集
                if total_episodes > 0:
                    ctype_str = str(content_type) if content_type else ""
                    if "儿童" in ctype_str:
                        content_dir = "shaoer"
                    elif "教育" in ctype_str:
                        content_dir = "mqxt"
                    elif "电竞" in ctype_str:
                        content_dir = "rywg"
                    else:
                        content_dir = "shaoer"
                    
                    episode_values = []
                    
                    for episode_num in range(1, total_episodes + 1):
                        episode_name = f"{media_name}第{episode_num:02d}集"
                        media_url = f"ftp://ftpmediazjyd:rD2q0y1M5eI@36.133.168.235:2121/media/hnyd/{content_dir}/{abbr}/{abbr}{episode_num:03d}.ts"
                        
                        # 匹配时长和大小 (使用内存字典快速匹配)
                        duration = 0
                        file_size = 0
                        
                        match_result = scan_map.get(episode_name)
                        
                        if match_result:
                            duration = match_result['duration'] if match_result['duration'] else 0
                            file_size = int(match_result['size']) if match_result['size'] else 0
                        
                        episode_props = {
                            '媒体拉取地址': media_url,
                            '媒体类型': 1,
                            '编码格式': 1,
                            '集数': episode_num,
                            '时长': duration,
                            '文件大小': file_size
                        }
                        
                        episode_values.append((new_drama_id, episode_name, json.dumps(episode_props, ensure_ascii=False)))
                    
                    if episode_values:
                        ep_insert_sql = "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)"
                        cursor.executemany(ep_insert_sql, episode_values)

                # 3. 插入 copyright_content
                copyright_fields = [
                    'drama_id', 'media_name', 'upstream_copyright', 'category_level1', 'category_level1_henan',
                    'category_level2_henan', 'episode_count', 'single_episode_duration', 'total_duration',
                    'production_year', 'production_region', 'language', 'language_henan', 'country',
                    'director', 'screenwriter', 'cast_members', 'recommendation', 'synopsis',
                    'keywords', 'video_quality', 'license_number', 'rating', 'exclusive_status',
                    'copyright_start_date', 'copyright_end_date', 'authorization_region',
                    'authorization_platform', 'cooperation_mode'
                ]
                
                c_fields = ['drama_id']
                c_values = [new_drama_id]
                
                for field in copyright_fields[1:]:
                    val = data.get(field)
                    if val is not None:
                        c_fields.append(field)
                        c_values.append(val)
                
                cols = ', '.join(c_fields)
                placeholders = ', '.join(['%s'] * len(c_fields))
                c_insert_sql = f"INSERT INTO copyright_content ({cols}) VALUES ({placeholders})"
                
                cursor.execute(c_insert_sql, c_values)
                
                # 提交本条事务
                conn.commit()
                success_count += 1
                
                if success_count % 10 == 0:
                    print(f"  已处理: {success_count}/{len(to_process)}")
                    
            except Exception as e:
                conn.rollback()
                error_count += 1
                print(f"  插入失败: {media_name}, 错误: {e}")
                
        print(f"\n任务完成。成功: {success_count}, 失败: {error_count}")
        
    except Exception as e:
        print(f"System Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
