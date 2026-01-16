"""
导入精确匹配数据脚本
1. 清空数据库的子集表、剧头表、版权表
2. 从精确匹配结果中获取介质名称列表
3. 从版权方数据表中筛选这些介质名称的数据
4. 导入到版权表，同时生成剧头和子集
"""
import sys
import os

# 添加 web_app1 到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
webapp_dir = os.path.join(project_root, 'web_app1')
sys.path.insert(0, webapp_dir)

import pandas as pd
import pymysql
import json
from config import DB_CONFIG, CUSTOMER_CONFIGS, get_enabled_customers
from utils import get_pinyin_abbr, get_content_dir, get_product_category, get_image_url, get_media_url, format_duration, format_datetime


def clean_numeric(value, field_type):
    """清洗数值字段"""
    import re
    if value is None or value == '' or pd.isna(value):
        return None
    str_val = str(value).strip()
    if str_val in ['暂无', '制作中', '待定', '未知', '-', '/', 'N/A', 'NA', 'null', 'None']:
        return None
    try:
        cleaned = re.sub(r'[^\d.\-]', '', str_val)
        if not cleaned or cleaned in ['.', '-', '-.']:
            return None
        return int(float(cleaned)) if field_type == int else float(cleaned)
    except:
        return None


def clean_string(value, max_len=500):
    """清洗字符串字段"""
    if value is None or pd.isna(value):
        return None
    s = str(value).strip()
    if not s or s.lower() in ['nan', 'none', 'null']:
        return None
    return s[:max_len] if len(s) > max_len else s


def build_drama_props(data, media_name, cust, scan_results=None):
    """构建剧头属性"""
    import re
    config = CUSTOMER_CONFIGS.get(cust, {})
    abbr = get_pinyin_abbr(media_name)
    props = {}
    for c in config.get('drama_columns', []):
        col = c['col']
        if 'field' in c:
            continue
        if 'value' in c:
            props[col] = c['value']
        elif 'source' in c:
            v = data.get(c['source'])
            # 只有配置了 default 才使用默认值，否则保持空
            if (v is None or v == '') and 'default' in c:
                v = c['default']
            # 分隔符转换：将逗号、顿号等转换为指定分隔符
            if v and c.get('separator'):
                v = re.sub(r'[,，、/／\\]', c['separator'], str(v))
            if v and c.get('suffix'):
                v = str(v) + c['suffix']
            if c.get('format') == 'datetime':
                v = format_datetime(v) if v else ''
            props[col] = v if v is not None else ''
        elif c.get('type') == 'image':
            props[col] = get_image_url(abbr, c.get('image_type', 'vertical'), cust)
        elif c.get('type') == 'product_category':
            cat1 = data.get('category_level1_henan') or data.get('category_level1') or ''
            props[col] = get_product_category(cat1, cust) if cat1 else ''
        elif c.get('type') == 'is_multi_episode':
            props[col] = 1 if int(data.get('episode_count') or 0) > 1 else 0
        elif c.get('type') == 'total_duration_seconds':
            props[col] = int(data.get('total_duration') or 0)
        elif c.get('type') == 'total_episodes_duration_seconds':
            # 计算所有子集时长之和（秒）
            total_dur = 0
            total_eps = int(data.get('episode_count') or 0)
            if scan_results and total_eps > 0:
                for ep in range(1, total_eps + 1):
                    ep_name = f"{media_name}第{ep:02d}集"
                    match = scan_results.get(ep_name, {})
                    total_dur += match.get('duration', 0)
            props[col] = total_dur
        elif c.get('type') == 'pinyin_abbr':
            props[col] = abbr
        elif c.get('type') == 'sequence':
            props[col] = None
    return props


def build_episodes(drama_id, media_name, total, data, cust, scan_results):
    """构建子集数据"""
    config = CUSTOMER_CONFIGS.get(cust, {})
    abbr = get_pinyin_abbr(media_name)
    cat1 = data.get('category_level1_henan') or data.get('category_level1') or ''
    content_dir = get_content_dir(cat1, cust) if cat1 else ''
    result = []
    for ep in range(1, total + 1):
        ep_name = f"{media_name}第{ep:02d}集"
        match = scan_results.get(ep_name, {})
        dur = match.get('duration', 0)  # 秒数
        dur_formatted = match.get('duration_formatted', '00000000')  # 格式化时间
        size = match.get('size', 0)
        props = {}
        for c in config.get('episode_columns', []):
            col = c['col']
            if 'field' in c:
                continue
            if 'value' in c:
                props[col] = c['value']
            elif c.get('type') == 'media_url':
                props[col] = get_media_url(abbr, ep, content_dir, cust)
            elif c.get('type') == 'episode_num':
                props[col] = ep
            elif c.get('type') == 'duration':
                props[col] = dur_formatted  # 河南移动用格式化时间
            elif c.get('type') == 'duration_minutes':
                props[col] = format_duration(dur, 'minutes') if dur else 0
            elif c.get('type') == 'duration_hhmmss':
                props[col] = format_duration(dur, 'HH:MM:SS') if dur else '00:00:00'
            elif c.get('type') == 'file_size':
                props[col] = size
            elif c.get('type') == 'md5':
                props[col] = ''
            elif c.get('type') == 'episode_name_format':
                props[col] = c.get('format', '{drama_name}第{ep}集').format(drama_name=media_name, ep=ep)
        result.append((drama_id, ep_name, json.dumps(props, ensure_ascii=False)))
    return result


# 列名映射
COLUMN_MAPPING = {
    '序号': 'serial_number', '上游版权方': 'upstream_copyright', '介质名称': 'media_name',
    '一级分类': 'category_level1', '二级分类': 'category_level2',
    '一级分类-河南标准': 'category_level1_henan', '一级分类-河南': 'category_level1_henan',
    '二级分类-河南标准': 'category_level2_henan', '二级分类-河南': 'category_level2_henan',
    '集数': 'episode_count', '单集时长': 'single_episode_duration', '总时长': 'total_duration',
    '出品年代': 'production_year', '制作地区': 'production_region', '出品地区': 'production_region',
    '语言': 'language', '语言-河南标准': 'language_henan', '语言-河南': 'language_henan',
    '国别': 'country', '国家': 'country', '导演': 'director', '编剧': 'screenwriter',
    '主演/嘉宾/主持人': 'cast_members', '主演\\嘉宾\\主持人': 'cast_members', '主演': 'cast_members',
    '推荐语': 'recommendation', '推荐语/一句话介绍': 'recommendation', '简介': 'synopsis',
    '关键字': 'keywords', '关键词': 'keywords', '清晰度': 'video_quality', '视频质量': 'video_quality',
    '标清\\高清\\4K\\3D\\杜比': 'video_quality', '许可编号': 'license_number', '许可证号': 'license_number',
    '发行许可编号\\备案号等': 'license_number', '评分': 'rating',
    '行业内相关网站的评级、评分（骨朵\\艺恩\\猫眼\\豆瓣\\时光网\\百度\\其他主流视频网站等评分': 'rating',
    '独家/非独': 'exclusive_status', '独家\\非独': 'exclusive_status', '独家状态': 'exclusive_status',
    '版权开始时间': 'copyright_start_date', '版权开始日期': 'copyright_start_date',
    '版权结束时间': 'copyright_end_date', '版权结束日期': 'copyright_end_date',
    '二级分类-山东': 'category_level2_shandong', '授权区域': 'authorization_region',
    '授权区域（全国/单独沟通）': 'authorization_region', '授权平台': 'authorization_platform',
    '授权平台（IPTV、OTT、小屏、待沟通）': 'authorization_platform',
    '合作方式': 'cooperation_mode', '合作方式（采买/分成）': 'cooperation_mode',
}

NUMERIC_FIELDS = {'episode_count': int, 'production_year': int, 'single_episode_duration': float, 'total_duration': float, 'rating': float}

INSERT_FIELDS = ['media_name', 'upstream_copyright', 'category_level1', 'category_level2', 
                 'category_level1_henan', 'category_level2_henan', 'episode_count', 
                 'single_episode_duration', 'total_duration', 'production_year', 'production_region', 
                 'language', 'language_henan', 'country', 'director', 'screenwriter', 'cast_members', 
                 'recommendation', 'synopsis', 'keywords', 'video_quality', 'license_number', 
                 'rating', 'exclusive_status', 'copyright_start_date', 'copyright_end_date',
                 'category_level2_shandong', 'authorization_region', 'authorization_platform', 
                 'cooperation_mode', 'drama_ids']


def main():
    print("=" * 60)
    print("导入精确匹配数据")
    print("=" * 60)
    
    # 1. 直接读取精确匹配版权方数据表
    print("\n[1/5] 读取精确匹配版权方数据表...")
    copyright_df = pd.read_excel(os.path.join(project_root, 'tables/精确匹配版权方数据.xlsx'), dtype=str).fillna('')
    
    # 重命名列
    rename_map = {col: COLUMN_MAPPING[col.strip()] for col in copyright_df.columns if col.strip() in COLUMN_MAPPING}
    if rename_map:
        copyright_df = copyright_df.rename(columns=rename_map)
    
    # 去重，保留第一条
    filtered_df = copyright_df.drop_duplicates(subset=['media_name'], keep='first')
    print(f"  数据表总行数: {len(copyright_df)}")
    print(f"  去重后行数: {len(filtered_df)}")
    
    # 2. 连接数据库
    print("\n[2/5] 连接数据库...")
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # 3. 清空表
        print("\n[3/5] 清空数据库表...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE drama_episode")
        cursor.execute("TRUNCATE TABLE drama_main")
        cursor.execute("TRUNCATE TABLE copyright_content")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        print("  已清空: drama_episode, drama_main, copyright_content")
        
        # 4. 预加载扫描结果
        print("\n[4/5] 预加载扫描结果...")
        cursor.execute("SELECT standard_episode_name, duration_seconds, duration_formatted, size_bytes FROM video_scan_result")
        scan_results = {r['standard_episode_name']: {
            'duration': int(r['duration_seconds'] or 0),  # 秒数
            'duration_formatted': r['duration_formatted'] or '00000000',  # 格式化时间
            'size': int(r['size_bytes'] or 0)
        } for r in cursor.fetchall() if r['standard_episode_name']}
        print(f"  扫描结果数量: {len(scan_results)}")
        
        # 5. 导入数据
        print("\n[5/5] 导入数据...")
        enabled_customers = get_enabled_customers()
        print(f"  启用的客户: {enabled_customers}")
        
        success_count = 0
        batch_size = 100
        total_rows = len(filtered_df)
        
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch_df = filtered_df.iloc[batch_start:batch_end]
            
            copyright_values = []
            drama_batch = []
            
            for _, row in batch_df.iterrows():
                media_name = str(row.get('media_name', '')).strip()
                if not media_name:
                    continue
                
                # 清洗数据
                cleaned = {}
                for f in INSERT_FIELDS:
                    if f == 'drama_ids':
                        continue
                    if f in NUMERIC_FIELDS:
                        cleaned[f] = clean_numeric(row.get(f), NUMERIC_FIELDS[f])
                    else:
                        cleaned[f] = clean_string(row.get(f))
                cleaned['media_name'] = media_name
                
                # 为每个客户准备剧头数据
                for cust in enabled_customers:
                    props = build_drama_props(cleaned, media_name, cust, scan_results)
                    drama_batch.append((cust, media_name, json.dumps(props, ensure_ascii=False), cleaned))
                
                copyright_values.append(cleaned)
            
            if not copyright_values:
                continue
            
            # 批量插入剧头
            if drama_batch:
                cursor.executemany(
                    "INSERT INTO drama_main (customer_code, drama_name, dynamic_properties) VALUES (%s, %s, %s)",
                    [(d[0], d[1], d[2]) for d in drama_batch]
                )
            
            # 批量查询刚插入的剧头ID
            media_names_in_batch = list(set(d[1] for d in drama_batch))
            placeholders = ','.join(['%s'] * len(media_names_in_batch))
            cursor.execute(
                f"SELECT drama_id, customer_code, drama_name FROM drama_main WHERE drama_name IN ({placeholders}) ORDER BY drama_id DESC",
                media_names_in_batch
            )
            
            # 构建映射
            drama_id_map = {}
            for row in cursor.fetchall():
                key = row['drama_name']
                if key not in drama_id_map:
                    drama_id_map[key] = {}
                if row['customer_code'] not in drama_id_map[key]:
                    drama_id_map[key][row['customer_code']] = row['drama_id']
            
            # 批量创建子集
            episode_values = []
            for cust, media_name, _, cleaned in drama_batch:
                drama_id = drama_id_map.get(media_name, {}).get(cust)
                if not drama_id:
                    continue
                total_eps = int(cleaned.get('episode_count') or 0)
                if total_eps > 0:
                    eps = build_episodes(drama_id, media_name, total_eps, cleaned, cust, scan_results)
                    episode_values.extend(eps)
            
            if episode_values:
                cursor.executemany(
                    "INSERT INTO drama_episode (drama_id, episode_name, dynamic_properties) VALUES (%s, %s, %s)",
                    episode_values
                )
            
            # 批量插入版权数据
            copyright_insert_values = []
            for cleaned in copyright_values:
                drama_ids = drama_id_map.get(cleaned['media_name'], {})
                values = tuple(cleaned.get(f) if f != 'drama_ids' else json.dumps(drama_ids) for f in INSERT_FIELDS)
                copyright_insert_values.append(values)
            
            placeholders = ','.join(['%s'] * len(INSERT_FIELDS))
            cursor.executemany(
                f"INSERT INTO copyright_content ({','.join(INSERT_FIELDS)}) VALUES ({placeholders})",
                copyright_insert_values
            )
            
            success_count += len(copyright_values)
            conn.commit()
            
            print(f"  进度: {batch_end}/{total_rows} ({batch_end*100//total_rows}%)")
        
        print("\n" + "=" * 60)
        print(f"导入完成!")
        print(f"  成功导入版权数据: {success_count} 条")
        
        # 统计结果
        cursor.execute("SELECT COUNT(*) as cnt FROM copyright_content")
        copyright_cnt = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM drama_main")
        drama_cnt = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM drama_episode")
        episode_cnt = cursor.fetchone()['cnt']
        
        print(f"  版权表记录数: {copyright_cnt}")
        print(f"  剧头表记录数: {drama_cnt}")
        print(f"  子集表记录数: {episode_cnt}")
        print("=" * 60)
        
    except Exception as e:
        conn.rollback()
        print(f"\n错误: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    main()
