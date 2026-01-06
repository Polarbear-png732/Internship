import pandas as pd

# 读取剧头数据.xlsx
print("=== 读取剧头数据.xlsx ===")
try:
    drama_header_df = pd.read_excel('剧头数据.xlsx')
    print(f"剧头数据行数：{len(drama_header_df)}")
    print(f"剧头数据列名：{drama_header_df.columns.tolist()}")
    print("\n剧头数据前2行：")
    print(drama_header_df.head(2))
except Exception as e:
    print(f"读取剧头数据.xlsx失败：{e}")

# 读取数据库子集数据_带id.xlsx
print("\n=== 读取数据库子集数据_带id.xlsx ===")
try:
    subset_df = pd.read_excel('数据库子集数据_带id.xlsx')
    print(f"子集数据行数：{len(subset_df)}")
    print(f"子集数据列名：{subset_df.columns.tolist()}")
    print("\n子集数据前2行：")
    print(subset_df.head(2))
except Exception as e:
    print(f"读取数据库子集数据_带id.xlsx失败：{e}")