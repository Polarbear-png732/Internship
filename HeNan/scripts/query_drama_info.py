"""
剧集信息查询工具
输入剧集名称，查询相关的剧集表、子集表、版权表信息
"""
import pymysql
import json

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'polarbear',
    'database': 'operation_management',
    'charset': 'utf8mb4'
}


def format_json(data):
    """格式化 JSON 字段"""
    if not data:
        return {}
    if isinstance(data, str):
        try:
            return json.loads(data)
        except:
            return data
    return data


def print_section(title, char='='):
    """打印分隔标题"""
    print(f"\n{char * 60}")
    print(f"  {title}")
    print(f"{char * 60}")


def print_dict(data, indent=2):
    """格式化打印字典"""
    prefix = ' ' * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_dict(value, indent + 2)
        else:
            # 截断过长的值
            str_val = str(value) if value is not None else 'NULL'
            if len(str_val) > 80:
                str_val = str_val[:80] + '...'
            print(f"{prefix}{key}: {str_val}")


def query_drama_info(drama_name):
    """查询剧集相关信息"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # 1. 查询剧集表 (精确匹配)
        cursor.execute(
            "SELECT * FROM drama_main WHERE drama_name = %s",
            (drama_name,)
        )
        dramas = cursor.fetchall()
        
        if not dramas:
            print(f"\n❌ 未找到包含 '{drama_name}' 的剧集")
            return
        
        print(f"\n✅ 找到 {len(dramas)} 个匹配的剧集")
        
        for drama in dramas:
            drama_id = drama['drama_id']
            
            # 剧集信息
            print_section(f"剧集: {drama['drama_name']} (ID: {drama_id})")
            
            print("\n【剧集表 drama_main】")
            print(f"  drama_id: {drama_id}")
            print(f"  drama_name: {drama['drama_name']}")
            print(f"  customer_id: {drama['customer_id']}")
            print(f"  created_at: {drama['created_at']}")
            print(f"  updated_at: {drama['updated_at']}")
            
            # 解析 dynamic_properties
            props = format_json(drama.get('dynamic_properties'))
            if props:
                print("\n  dynamic_properties:")
                for k, v in props.items():
                    str_v = str(v) if v is not None else 'NULL'
                    if len(str_v) > 60:
                        str_v = str_v[:60] + '...'
                    print(f"    {k}: {str_v}")
            
            # 2. 查询子集表
            cursor.execute(
                "SELECT * FROM drama_episode WHERE drama_id = %s ORDER BY episode_id",
                (drama_id,)
            )
            episodes = cursor.fetchall()
            
            print(f"\n【子集表 drama_episode】共 {len(episodes)} 条")
            if episodes:
                print(f"  {'序号':<5}{'episode_id':<10}{'episode_name':<28}{'时长':<12}{'文件大小':<12}{'扫描匹配路径'}")
                print(f"  {'-'*120}")
                for i, ep in enumerate(episodes, 1):
                    ep_props = format_json(ep.get('dynamic_properties'))
                    duration = ep_props.get('时长', '-')
                    file_size = ep_props.get('文件大小', '-')
                    if file_size and file_size != '-':
                        file_size = f"{int(file_size)/1024/1024:.1f}MB" if isinstance(file_size, (int, float)) and file_size > 0 else file_size
                    name = ep['episode_name'][:26] if len(ep['episode_name']) > 26 else ep['episode_name']
                    
                    # 查询扫描结果匹配
                    cursor.execute(
                        "SELECT source_folder, source_file FROM video_scan_result WHERE standard_episode_name = %s LIMIT 1",
                        (ep['episode_name'],)
                    )
                    scan_match = cursor.fetchone()
                    scan_path = f"{scan_match['source_folder']}/{scan_match['source_file']}" if scan_match else "未匹配"
                    
                    print(f"  {i:<5}{ep['episode_id']:<10}{name:<28}{str(duration):<12}{str(file_size):<12}{scan_path}")
            
            # 3. 查询版权表
            cursor.execute(
                "SELECT * FROM copyright_content WHERE drama_id = %s OR media_name = %s",
                (drama_id, drama['drama_name'])
            )
            copyrights = cursor.fetchall()
            
            print(f"\n【版权表 copyright_content】共 {len(copyrights)} 条")
            if copyrights:
                for cp in copyrights:
                    print(f"\n  --- 版权记录 ID: {cp['id']} ---")
                    important_fields = [
                        ('media_name', '介质名称'),
                        ('upstream_copyright', '上游版权方'),
                        ('category_level1_henan', '一级分类-河南'),
                        ('category_level2_henan', '二级分类-河南'),
                        ('episode_count', '集数'),
                        ('production_year', '出品年代'),
                        ('director', '导演'),
                        ('cast_members', '主演'),
                        ('copyright_start_date', '版权开始'),
                        ('copyright_end_date', '版权结束'),
                        ('authorization_region', '授权区域'),
                        ('authorization_platform', '授权平台'),
                    ]
                    for field, label in important_fields:
                        val = cp.get(field)
                        if val:
                            str_val = str(val)
                            if len(str_val) > 50:
                                str_val = str_val[:50] + '...'
                            print(f"  {label}: {str_val}")
            
            print("\n" + "-" * 60)
    
    finally:
        cursor.close()
        conn.close()


def main():
    print("=" * 60)
    print("  剧集信息查询工具")
    print("  输入剧集名称查询，输入 exit 退出")
    print("=" * 60)
    
    while True:
        print("\n请输入剧集名称:")
        drama_name = input("> ").strip()
        
        if drama_name.lower() == 'exit':
            print("再见!")
            break
        
        if not drama_name:
            print("请输入剧集名称")
            continue
        
        query_drama_info(drama_name)


if __name__ == "__main__":
    main()
