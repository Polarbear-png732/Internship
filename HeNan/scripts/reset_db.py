"""
一键清空数据库（保留视频扫描表）
用于测试时快速重置数据

清空的表：
- drama_episode (子集)
- drama_main (剧头)  
- copyright_content (版权)

保留的表：
- video_scan_result (视频扫描结果)
"""
import pymysql
import sys
sys.path.insert(0, 'd:/ioeyu/Internship/HeNan/web_app1')
from database import get_db


def clear_database(confirm=False):
    """清空数据库（保留视频扫描表）"""
    
    with get_db() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 统计当前数据
        cursor.execute('SELECT COUNT(*) as cnt FROM drama_episode')
        ep_count = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) as cnt FROM drama_main')
        drama_count = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) as cnt FROM copyright_content')
        copyright_count = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) as cnt FROM video_scan_result')
        scan_count = cursor.fetchone()['cnt']
        
        print("当前数据:")
        print("  子集 (drama_episode):      %d" % ep_count)
        print("  剧头 (drama_main):         %d" % drama_count)
        print("  版权 (copyright_content):  %d" % copyright_count)
        print("  扫描 (video_scan_result):  %d (保留)" % scan_count)
        print()
        
        if not confirm:
            user_input = input("确认清空以上数据？(yes/no): ").strip().lower()
            if user_input != 'yes':
                print("已取消")
                return False
        
        print("正在清空...")
        
        # 按顺序清空（先子表后主表，避免外键约束问题）
        # 1. 清空子集（外键关联 drama_main）
        cursor.execute('DELETE FROM drama_episode')
        print("  已清空 drama_episode: %d 条" % cursor.rowcount)
        
        # 2. 清空剧头
        cursor.execute('DELETE FROM drama_main')
        print("  已清空 drama_main: %d 条" % cursor.rowcount)
        
        # 3. 清空版权
        cursor.execute('DELETE FROM copyright_content')
        print("  已清空 copyright_content: %d 条" % cursor.rowcount)
        
        # 重置自增ID
        cursor.execute('ALTER TABLE drama_episode AUTO_INCREMENT = 1')
        cursor.execute('ALTER TABLE drama_main AUTO_INCREMENT = 1')
        cursor.execute('ALTER TABLE copyright_content AUTO_INCREMENT = 1')
        print("  已重置自增ID")
        
        conn.commit()
        
        print()
        print("✅ 清空完成！")
        return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='清空数据库（保留视频扫描表）')
    parser.add_argument('-y', '--yes', action='store_true', help='跳过确认直接执行')
    args = parser.parse_args()
    
    print("=" * 50)
    print("   数据库清空工具（保留视频扫描表）")
    print("=" * 50)
    print()
    
    clear_database(confirm=args.yes)
