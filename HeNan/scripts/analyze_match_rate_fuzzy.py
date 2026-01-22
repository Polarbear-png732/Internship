"""
版权方数据与扫描结果匹配率分析（增强模糊匹配版）

支持的匹配方式：
1. 精确匹配 - 名称完全一致
2. 去空格匹配 - 忽略空格后匹配
3. 拼音首字母匹配 - 中文转拼音首字母后匹配
4. 包含关系匹配 - 一方包含另一方
5. 去除常见后缀匹配 - 去除"系列"、"动画"等后缀
"""
import pandas as pd
import os
import re
from pypinyin import lazy_pinyin, Style


def get_pinyin_abbr(text: str) -> str:
    """获取中文的拼音首字母缩写"""
    if not text:
        return ''
    # 只处理中文字符
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    if not chinese_chars:
        return text.lower()
    
    abbr = ''.join(lazy_pinyin(chinese_chars, style=Style.FIRST_LETTER))
    return abbr.lower()


def normalize_name(name: str) -> str:
    """标准化名称：去除空格、括号、特殊字符"""
    if not name:
        return ''
    # 去除空格
    name = re.sub(r'\s+', '', name)
    # 统一括号
    name = name.replace('（', '(').replace('）', ')')
    # 去除常见后缀
    name = re.sub(r'(系列|动画|全集|合集|第[一二三四五六七八九十\d]+季)$', '', name)
    return name.lower()


def extract_core_name(name: str) -> str:
    """提取核心名称：去除所有非核心内容"""
    if not name:
        return ''
    # 去除空格、括号及其内容
    name = re.sub(r'\s+', '', name)
    name = re.sub(r'[（\(][^）\)]*[）\)]', '', name)
    # 去除常见后缀
    name = re.sub(r'(系列|动画|全集|合集|第[一二三四五六七八九十\d]+季|[第]?\d+季)$', '', name)
    # 去除英文前缀（如果后面有中文）
    if re.search(r'[\u4e00-\u9fff]', name):
        name = re.sub(r'^[a-zA-Z0-9\-_\.]+', '', name)
    return name


def analyze_match_rate_fuzzy():
    base_dir = os.path.dirname(__file__)
    tables_dir = os.path.join(base_dir, '..', 'tables')
    
    # 读取数据
    print("📂 正在读取数据...")
    copyright_df = pd.read_excel(os.path.join(tables_dir, '版权方数据表.xlsx'))
    scan_df = pd.read_csv(os.path.join(tables_dir, 'scan_result_with_standard_name.csv'))
    
    # 获取扫描结果中的标准化子集名称
    scan_episode_names = set(scan_df['标准化子集名称'].dropna().astype(str).str.strip())
    print(f"📊 扫描结果子集名称数量: {len(scan_episode_names)}")
    
    # 从扫描结果提取剧名（去掉"第XX集"后缀）
    scan_drama_names = set()
    for name in scan_episode_names:
        match = re.match(r'^(.+?)第\d+集$', name)
        if match:
            scan_drama_names.add(match.group(1))
    
    # 构建多种索引用于模糊匹配
    print("🔧 正在构建匹配索引...")
    
    # 索引1: 原始名称
    scan_names_original = {name: name for name in scan_drama_names}
    
    # 索引2: 标准化名称（去空格等）
    scan_names_normalized = {}
    for name in scan_drama_names:
        normalized = normalize_name(name)
        if normalized:
            scan_names_normalized[normalized] = name
    
    # 索引3: 拼音首字母
    scan_names_pinyin = {}
    for name in scan_drama_names:
        pinyin = get_pinyin_abbr(name)
        if pinyin and len(pinyin) >= 3:  # 至少3个字符
            if pinyin not in scan_names_pinyin:
                scan_names_pinyin[pinyin] = []
            scan_names_pinyin[pinyin].append(name)
    
    # 索引4: 核心名称
    scan_names_core = {}
    for name in scan_drama_names:
        core = extract_core_name(name)
        if core and len(core) >= 2:
            if core not in scan_names_core:
                scan_names_core[core] = []
            scan_names_core[core].append(name)
    
    print(f"  - 原始名称索引: {len(scan_names_original)}")
    print(f"  - 标准化名称索引: {len(scan_names_normalized)}")
    print(f"  - 拼音首字母索引: {len(scan_names_pinyin)}")
    print(f"  - 核心名称索引: {len(scan_names_core)}")
    
    # 获取版权方数据
    media_col = [c for c in copyright_df.columns if '介质名称' in str(c)][0]
    episode_col = [c for c in copyright_df.columns if '集数' in str(c)][0]
    
    # 去重获取介质名称
    seen_media = set()
    media_list = []
    for _, row in copyright_df.iterrows():
        name = str(row[media_col]).strip() if pd.notna(row[media_col]) else ''
        if name and name != 'nan' and name not in seen_media:
            seen_media.add(name)
            ep_str = str(row[episode_col]).strip() if pd.notna(row[episode_col]) else '0'
            ep_match = re.search(r'\d+', ep_str)
            episode_count = int(ep_match.group()) if ep_match else 0
            media_list.append({'name': name, 'episode_count': episode_count})
    
    print(f"📊 版权方介质名称数量: {len(media_list)}")
    
    # 开始匹配
    print("\n🔍 开始模糊匹配分析...")
    
    match_results = []
    total_episodes = 0
    matched_episodes = 0
    
    for item in media_list:
        media_name = item['name']
        episode_count = item['episode_count']
        total_episodes += episode_count
        
        # 尝试多种匹配方式
        matched_scan_name = None
        match_type = '未匹配'
        
        # 1. 精确匹配
        if media_name in scan_names_original:
            matched_scan_name = media_name
            match_type = '精确匹配'
        
        # 2. 标准化名称匹配
        if not matched_scan_name:
            normalized = normalize_name(media_name)
            if normalized in scan_names_normalized:
                matched_scan_name = scan_names_normalized[normalized]
                match_type = '标准化匹配'
        
        # 3. 核心名称匹配
        if not matched_scan_name:
            core = extract_core_name(media_name)
            if core and core in scan_names_core:
                # 如果有多个匹配，选第一个
                matched_scan_name = scan_names_core[core][0]
                match_type = '核心名称匹配'
        
        # 4. 拼音首字母匹配
        if not matched_scan_name:
            pinyin = get_pinyin_abbr(media_name)
            if pinyin and len(pinyin) >= 4 and pinyin in scan_names_pinyin:
                # 拼音匹配需要额外验证长度接近
                candidates = scan_names_pinyin[pinyin]
                for candidate in candidates:
                    # 验证长度相近（允许差3个字符）
                    if abs(len(media_name) - len(candidate)) <= 3:
                        matched_scan_name = candidate
                        match_type = '拼音首字母匹配'
                        break
        
        # 5. 包含关系匹配（较宽松）
        if not matched_scan_name:
            media_core = extract_core_name(media_name)
            if media_core and len(media_core) >= 4:
                for scan_name in scan_drama_names:
                    scan_core = extract_core_name(scan_name)
                    if scan_core and len(scan_core) >= 4:
                        if media_core in scan_core or scan_core in media_core:
                            matched_scan_name = scan_name
                            match_type = '包含关系匹配'
                            break
        
        # 统计子集匹配
        ep_matched = 0
        if matched_scan_name and episode_count > 0:
            for ep in range(1, episode_count + 1):
                ep_name = f"{matched_scan_name}第{ep:02d}集"
                if ep_name in scan_episode_names:
                    ep_matched += 1
        
        matched_episodes += ep_matched
        
        match_results.append({
            '介质名称': media_name,
            '总集数': episode_count,
            '匹配到的扫描名称': matched_scan_name or '',
            '匹配类型': match_type,
            '匹配子集数': ep_matched,
            '子集匹配率': f"{ep_matched/episode_count*100:.1f}%" if episode_count > 0 else '0%'
        })
    
    # 统计
    match_type_counts = {}
    for r in match_results:
        t = r['匹配类型']
        match_type_counts[t] = match_type_counts.get(t, 0) + 1
    
    total_dramas = len(match_results)
    matched_dramas = total_dramas - match_type_counts.get('未匹配', 0)
    
    print("\n" + "="*70)
    print("📊 模糊匹配分析结果")
    print("="*70)
    
    print(f"\n【剧集维度】")
    print(f"  总剧集数:           {total_dramas}")
    for match_type, count in sorted(match_type_counts.items(), key=lambda x: -x[1]):
        print(f"  {match_type}:       {count} ({count/total_dramas*100:.1f}%)")
    print(f"  ---------------")
    print(f"  匹配成功总计:       {matched_dramas} ({matched_dramas/total_dramas*100:.1f}%)")
    
    print(f"\n【子集维度】")
    print(f"  总子集数:           {total_episodes}")
    print(f"  匹配成功:           {matched_episodes} ({matched_episodes/total_episodes*100:.1f}%)")
    print(f"  未匹配:             {total_episodes - matched_episodes} ({(total_episodes - matched_episodes)/total_episodes*100:.1f}%)")
    print("="*70)
    
    # 导出结果
    output_path = os.path.join(tables_dir, '模糊匹配分析结果.xlsx')
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: 所有匹配结果
        results_df = pd.DataFrame(match_results)
        results_df = results_df.sort_values(by=['匹配类型', '匹配子集数'], ascending=[True, False])
        results_df.to_excel(writer, sheet_name='匹配详情', index=False)
        
        # Sheet 2: 未匹配
        unmatched = [r for r in match_results if r['匹配类型'] == '未匹配']
        pd.DataFrame(unmatched).to_excel(writer, sheet_name='未匹配', index=False)
        
        # Sheet 3: 拼音匹配示例
        pinyin_matched = [r for r in match_results if r['匹配类型'] == '拼音首字母匹配']
        pd.DataFrame(pinyin_matched).to_excel(writer, sheet_name='拼音匹配', index=False)
        
        # Sheet 4: 统计摘要
        summary = {
            '匹配类型': list(match_type_counts.keys()) + ['匹配成功总计', '总剧集数', '子集匹配数', '子集总数'],
            '数量': list(match_type_counts.values()) + [matched_dramas, total_dramas, matched_episodes, total_episodes]
        }
        pd.DataFrame(summary).to_excel(writer, sheet_name='统计摘要', index=False)
    
    print(f"\n📁 已生成分析文件: {output_path}")


if __name__ == '__main__':
    analyze_match_rate_fuzzy()
