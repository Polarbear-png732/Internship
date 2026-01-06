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

# 剧头数据列名顺序（与剧头数据.xlsx保持一致）
DRAMA_HEADER_COLUMNS = [
    '剧头id', '剧集名称', '作者列表', '清晰度', '语言', '主演', '内容类型', '上映年份',
    '关键字', '评分', '推荐语', '总集数', '产品分类', '竖图', '描述', '横图', '版权', '二级分类'
]

# 子集数据列名顺序（与数据库子集数据_带id.xlsx保持一致）
SUBSET_COLUMNS = [
    '子集id', '节目名称', '媒体拉取地址', '媒体类型', '编码格式', '集数', '时长', '文件大小'
]

def main():
    # 1. 获取用户输入的剧集名称
    drama_name = input("请输入要查询的剧集名称：").strip()
    if not drama_name:
        print("剧集名称不能为空！")
        return
    
    print(f"\n=== 查询剧集：{drama_name} ===")
    
    # 2. 建立数据库连接
    print("\n=== 连接数据库 ===")
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("数据库连接成功")
    except Exception as e:
        print(f"数据库连接失败：{e}")
        return
    
    try:
        # 3. 查询剧头数据
        print("\n=== 查询剧头数据 ===")
        query_header = "SELECT * FROM drama_main WHERE drama_name = %s"
        cursor.execute(query_header, (drama_name,))
        header_result = cursor.fetchone()
        
        if not header_result:
            print(f"未找到剧集 '{drama_name}' 的剧头数据")
            conn.close()
            return
        
        # 获取剧头表的列名
        header_columns = [desc[0] for desc in cursor.description]
        header_data = dict(zip(header_columns, header_result))
        
        # 解析dynamic_properties JSON
        dynamic_props = json.loads(header_data['dynamic_properties']) if header_data['dynamic_properties'] else {}
        
        # 构建剧头数据字典，按照指定顺序
        header_dict = {
            '剧头id': header_data['drama_id'],
            '剧集名称': header_data['drama_name'],
            '作者列表': dynamic_props.get('作者列表', ''),
            '清晰度': dynamic_props.get('清晰度', 0),
            '语言': dynamic_props.get('语言', ''),
            '主演': dynamic_props.get('主演', ''),
            '内容类型': dynamic_props.get('内容类型', ''),
            '上映年份': dynamic_props.get('上映年份', 0),
            '关键字': dynamic_props.get('关键字', ''),
            '评分': dynamic_props.get('评分', 0.0),
            '推荐语': dynamic_props.get('推荐语', ''),
            '总集数': dynamic_props.get('总集数', 0),
            '产品分类': dynamic_props.get('产品分类', 0),
            '竖图': dynamic_props.get('竖图', ''),
            '描述': dynamic_props.get('描述', ''),
            '横图': dynamic_props.get('横图', ''),
            '版权': dynamic_props.get('版权', 0),
            '二级分类': dynamic_props.get('二级分类', '')
        }
        
        # 转换为DataFrame
        header_df = pd.DataFrame([header_dict], columns=DRAMA_HEADER_COLUMNS)
        print(f"找到剧头数据：\n{header_df}")
        
        # 4. 查询子集数据
        print("\n=== 查询子集数据 ===")
        query_subset = "SELECT * FROM drama_episode WHERE drama_id = %s"
        cursor.execute(query_subset, (header_data['drama_id'],))
        subset_results = cursor.fetchall()
        
        if not subset_results:
            print(f"未找到剧集 '{drama_name}' 的子集数据")
            conn.close()
            return
        
        # 获取子集表的列名
        subset_columns_db = [desc[0] for desc in cursor.description]
        
        subset_data_list = []
        for i, subset_result in enumerate(subset_results, 1):
            subset_dict = dict(zip(subset_columns_db, subset_result))
            
            # 解析dynamic_properties JSON
            subset_dynamic_props = json.loads(subset_dict['dynamic_properties']) if subset_dict['dynamic_properties'] else {}
            
            # 构建子集数据字典，按照指定顺序
            subset_data = {
                '子集id': i,  # 使用自增id
                '节目名称': subset_dict['episode_name'],
                '媒体拉取地址': subset_dynamic_props.get('媒体拉取地址', ''),
                '媒体类型': subset_dynamic_props.get('媒体类型', 0),
                '编码格式': subset_dynamic_props.get('编码格式', 0),
                '集数': subset_dynamic_props.get('集数', 0),
                '时长': subset_dynamic_props.get('时长', 0),
                '文件大小': subset_dynamic_props.get('文件大小', 0)
            }
            subset_data_list.append(subset_data)
        
        # 转换为DataFrame
        subset_df = pd.DataFrame(subset_data_list, columns=SUBSET_COLUMNS)
        print(f"找到 {len(subset_df)} 条子集数据")
        print(f"子集数据示例：\n{subset_df.head(2)}")
        
        # 5. 生成Excel文件
        print("\n=== 生成Excel文件 ===")
        output_file = f"excel/{drama_name}_数据.xlsx"
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # 写入剧头数据工作表
            header_df.to_excel(writer, sheet_name=f'{drama_name}-剧头', index=False)
            
            # 写入子集数据工作表
            subset_df.to_excel(writer, sheet_name=f'{drama_name}-子集', index=False)
        
        print(f"Excel文件已生成：{output_file}")
        print(f"包含工作表：")
        print(f"  - {drama_name}-剧头：{len(header_df)} 条数据")
        print(f"  - {drama_name}-子集：{len(subset_df)} 条数据")
        
    except Exception as e:
        print(f"处理数据时出错：{e}")
    finally:
        # 关闭数据库连接
        conn.close()
        print("\n数据库连接已关闭")

if __name__ == "__main__":
    main()