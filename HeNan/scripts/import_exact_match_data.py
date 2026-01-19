"""
导入精确匹配数据脚本
1. 清空数据库的子集表、剧头表、版权表
2. 从精确匹配版权方数据表导入数据
3. 同时生成剧头和子集
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
from config import DB_CONFIG, get_enabled_customers
from utils import (
    clean_numeric, clean_string, build_drama_props, build_episodes,
    COLUMN_MAPPING, NUMERIC_FIELDS, INSERT_FIELDS
)


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
            'duration': int(r['duration_seconds'] or 0),
            'duration_formatted': r['duration_formatted'] or '00000000',
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
            
            # 查询剧头ID
            media_names_in_batch = list(set(d[1] for d in drama_batch))
            placeholders = ','.join(['%s'] * len(media_names_in_batch))
            cursor.execute(
                f"SELECT drama_id, customer_code, drama_name FROM drama_main WHERE drama_name IN ({placeholders}) ORDER BY drama_id DESC",
                media_names_in_batch
            )
            
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
