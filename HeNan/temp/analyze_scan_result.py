from pathlib import Path
import pandas as pd

root = Path('scan_result')

# 统计文件
excel_files = list(root.rglob('*.xlsx'))
print(f'Excel文件总数: {len(excel_files)}')
print(f'\n按盘符分组:')

for drive in ['D', 'E', 'G', 'H', 'I']:
    drive_path = root / drive
    if drive_path.exists():
        files = list(drive_path.rglob('*.xlsx'))
        print(f'  {drive}盘: {len(files)} 个Excel文件')

# 读取几个示例文件看看结构
print('\n\n示例文件内容:')
sample_files = excel_files[:3]
for f in sample_files:
    print(f'\n文件: {f}')
    try:
        df = pd.read_excel(f)
        print(f'  行数: {len(df)}')
        print(f'  列名: {df.columns.tolist()}')
        if len(df) > 0:
            print(f'  第一行文件名: {df.iloc[0]["文件名称"]}')
    except Exception as e:
        print(f'  读取失败: {e}')

# 统计所有扫描过的视频文件
print('\n\n统计所有已扫描的视频文件...')
all_videos = []
for excel_file in excel_files:
    try:
        df = pd.read_excel(excel_file)
        for _, row in df.iterrows():
            all_videos.append({
                'excel_path': str(excel_file),
                'filename': row['文件名称'],
                'duration': row['时长（秒）'],
                'size_mb': row['大小（mb）']
            })
    except Exception as e:
        print(f'读取失败: {excel_file} - {e}')

print(f'\n总共已扫描视频文件数: {len(all_videos)}')
print(f'\n前5个视频:')
for v in all_videos[:5]:
    print(f'  {v["filename"]} ({v["size_mb"]} MB)')
