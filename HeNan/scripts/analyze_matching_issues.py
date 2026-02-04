"""
分析版权数据与扫描数据匹配问题的脚本
"""
import pandas as pd
import re
from pathlib import Path

# 文件路径
scan_file = Path(__file__).parent.parent / 'tables' / 'scan_result_with_standard_name.csv'
copyright_file = Path(__file__).parent.parent / 'tables' / '版权方数据表.xlsx'

# 读取数据
print("读取数据文件...")
scan_df = pd.read_csv(scan_file)
copyright_df = pd.read_excel(copyright_file)

def normalize(s):
    """标准化字符串：去除空格"""
    if pd.isna(s):
        return ''
    return str(s).replace(' ', '').replace('　', '').strip()

def parse_episode_count(val):
    """解析集数"""
    if pd.isna(val):
        return 0
    match = re.search(r'(\d+)', str(val))
    return int(match.group(1)) if match else 0

# 构建索引
print("\n构建索引...")
scan_media = {normalize(n): n for n in scan_df['来源文件'].dropna().unique()}
scan_std_names = set(normalize(n) for n in scan_df['标准化子集名称'].dropna().unique())

print(f"扫描表介质数量: {len(scan_media)}")
print(f"扫描表子集数量: {len(scan_std_names)}")
print(f"版权表记录数量: {len(copyright_df)}")

# 分析三种情况
print("\n" + "="*80)
print("匹配情况分析")
print("="*80)

# 1. 介质名称完全匹配
# 2. 介质名称匹配但子集不匹配
# 3. 介质名称完全不匹配

media_matched = []
media_partial = []
media_unmatched = []

for _, row in copyright_df.iterrows():
    media_name = row['介质名称']
    ep_count = parse_episode_count(row['集数'])
    if pd.isna(media_name):
        continue
    
    norm_name = normalize(media_name)
    
    if norm_name in scan_media:
        # 介质匹配，检查子集
        generated = [f'{norm_name}第{ep:02d}集' for ep in range(1, ep_count + 1)]
        matched = sum(1 for g in generated if g in scan_std_names)
        actual_eps = [n for n in scan_std_names if n.startswith(norm_name + '第') and '集' in n]
        
        if matched > 0:
            media_matched.append({
                'copyright_name': media_name,
                'scan_name': scan_media[norm_name],
                'copyright_ep': ep_count,
                'matched_ep': matched,
                'scan_actual_ep': len(actual_eps)
            })
        else:
            media_partial.append({
                'copyright_name': media_name,
                'scan_name': scan_media[norm_name],
                'copyright_ep': ep_count,
                'scan_actual_ep': len(actual_eps),
                'sample_actual': actual_eps[:3] if actual_eps else []
            })
    else:
        media_unmatched.append({
            'copyright_name': media_name,
            'norm_name': norm_name,
            'ep_count': ep_count
        })

print(f"\n1. 介质匹配且子集有匹配: {len(media_matched)} 条")
print(f"2. 介质匹配但子集无匹配: {len(media_partial)} 条")
print(f"3. 介质完全不匹配: {len(media_unmatched)} 条")

# 详细分析
print("\n" + "="*80)
print("1. 介质匹配且子集匹配的情况（前20个）")
print("="*80)
for ex in media_matched[:20]:
    print(f"  {ex['copyright_name']}: 版权{ex['copyright_ep']}集, 匹配{ex['matched_ep']}集, 扫描实际{ex['scan_actual_ep']}集")

print("\n" + "="*80)
print("2. 介质匹配但子集不匹配的情况（全部）- 需要检查命名格式")
print("="*80)
for ex in media_partial[:30]:
    print(f"  版权: {ex['copyright_name']} ({ex['copyright_ep']}集)")
    print(f"  扫描: {ex['scan_name']}")
    if ex['sample_actual']:
        print(f"  实际子集示例: {ex['sample_actual']}")
    print()

print("\n" + "="*80)
print("3. 介质完全不匹配的情况（前50个）- 需要扫描或名称映射")
print("="*80)
for ex in media_unmatched[:50]:
    print(f"  {ex['copyright_name']} ({ex['ep_count']}集)")

# 分析命名格式差异
print("\n" + "="*80)
print("命名格式差异分析")
print("="*80)

# 扫描表中的子集命名模式分析
patterns = {
    '第XX集': 0,
    '第XX话': 0,
    'EPxx': 0,
    '数字开头': 0,
    '其他': 0
}

for name in scan_std_names:
    if re.search(r'第\d+集', name):
        patterns['第XX集'] += 1
    elif re.search(r'第\d+话', name):
        patterns['第XX话'] += 1
    elif re.search(r'EP\d+', name, re.I):
        patterns['EPxx'] += 1
    elif re.match(r'\d+', name):
        patterns['数字开头'] += 1
    else:
        patterns['其他'] += 1

print("扫描表子集命名模式分布:")
for p, count in patterns.items():
    print(f"  {p}: {count}")

# 检查未匹配的子集示例
print("\n" + "="*80)
print("未匹配介质名称相似度分析（查找可能的映射）")
print("="*80)

# 找相似的名称
from difflib import SequenceMatcher

def find_similar(name, candidates, threshold=0.7):
    results = []
    for c in candidates:
        ratio = SequenceMatcher(None, name, c).ratio()
        if ratio >= threshold:
            results.append((c, ratio))
    return sorted(results, key=lambda x: -x[1])[:3]

print("\n未匹配介质可能的相似匹配:")
for ex in media_unmatched[:20]:
    similar = find_similar(ex['norm_name'], list(scan_media.keys()), 0.6)
    if similar:
        print(f"  {ex['copyright_name']}")
        for s, ratio in similar:
            print(f"    -> {scan_media[s]} ({ratio:.0%})")
