"""
工具函数模块
包含数据处理、格式化、URL生成等公共函数
"""
import json
import re
import pandas as pd
from pypinyin import pinyin, Style
from config import CUSTOMER_CONFIGS


# ============================================================
# JSON 解析
# ============================================================

def parse_json(data, field='dynamic_properties'):
    """解析 JSON 字段，返回字典"""
    if data and data.get(field):
        val = data[field]
        return json.loads(val) if isinstance(val, str) else val
    return {}


# ============================================================
# 拼音和URL生成
# ============================================================

def get_pinyin_abbr(name):
    """生成拼音首字母缩写"""
    if not name:
        return ""
    result = []
    for char in name:
        if '\u4e00' <= char <= '\u9fff':
            py = pinyin(char, style=Style.FIRST_LETTER)
            if py and py[0]:
                result.append(py[0][0])
        elif char.isalnum():
            result.append(char.lower())
    return ''.join(result)


def get_content_dir(content_type, customer_code='henan_mobile'):
    """根据内容类型和客户获取媒体目录"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    mapping = config.get('content_dir_map', {})
    if content_type and mapping:
        for key, value in mapping.items():
            if key != '_default' and key in str(content_type):
                return value
    return mapping.get('_default', 'shaoer')


def get_product_category(content_type, customer_code='henan_mobile'):
    """根据内容类型和客户获取产品分类"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    mapping = config.get('product_category_map', {})
    if content_type and mapping:
        for key, value in mapping.items():
            if key != '_default' and key in str(content_type):
                return value
    # 返回默认值（如果配置了_default），否则返回空字符串
    # 这样每个客户可以自己决定是否需要默认值
    return mapping.get('_default', '')


def get_category_level1_mapped(content_type, customer_code='henan_mobile'):
    """根据内容类型和客户获取映射后的一级分类"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    mapping = config.get('category_level1_map', {})
    if content_type and mapping:
        for key, value in mapping.items():
            if key != '_default' and key in str(content_type):
                return value
    # 如果没有映射规则或没有匹配，返回原值
    return content_type if content_type else ''


def get_image_url(abbr, image_type, customer_code='henan_mobile'):
    """生成图片URL"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    url_templates = config.get('image_url', {})
    template = url_templates.get(image_type, '')
    return template.format(abbr=abbr) if template else ''


def get_media_url(abbr, episode_num, content_dir, customer_code='henan_mobile'):
    """生成媒体拉取地址"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    template = config.get('media_url_template', '')
    return template.format(dir=content_dir, abbr=abbr, ep=episode_num) if template else ''


# ============================================================
# 格式化函数
# ============================================================

def format_duration(seconds, format_type='HHMMSS00'):
    """格式化时长
    format_type: 'HHMMSS00' | 'minutes' | 'HH:MM:SS'
    """
    if not seconds:
        return 0 if format_type == 'minutes' else '00:00:00' if format_type == 'HH:MM:SS' else '00000000'
    
    try:
        total_seconds = int(seconds)
    except (ValueError, TypeError):
        return 0 if format_type == 'minutes' else '00:00:00' if format_type == 'HH:MM:SS' else '00000000'
    
    if format_type == 'minutes':
        return total_seconds // 60
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if format_type == 'HH:MM:SS':
        return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    else:  # HHMMSS00
        return f'{hours:02d}{minutes:02d}{secs:02d}00'


def format_datetime(date_str):
    """格式化日期时间为 YYYY-MM-DD HH:mm:ss"""
    if not date_str:
        return ''
    if isinstance(date_str, str) and len(date_str) >= 10:
        return date_str
    return str(date_str)


# ============================================================
# 数据清洗函数
# ============================================================

def clean_numeric(value, field_type):
    """清洗数值字段"""
    if value is None or value == '' or (isinstance(value, float) and pd.isna(value)):
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
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s or s.lower() in ['nan', 'none', 'null']:
        return None
    return s[:max_len] if len(s) > max_len else s



# ============================================================
# 数据构建函数（剧头、子集）
# ============================================================

def build_drama_props(data, media_name, customer_code, scan_results=None):
    """构建剧头属性（配置驱动）"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
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
            # 只有配置了 default 才使用默认值
            if (v is None or v == '') and 'default' in c:
                v = c['default']
            # 分隔符转换
            if v and c.get('separator'):
                v = re.sub(r'[,，、/／\\]', c['separator'], str(v))
            if v and c.get('suffix'):
                v = str(v) + c['suffix']
            if c.get('format') == 'datetime':
                v = format_datetime(v) if v else ''
            # 支持映射转换（如一级分类映射）
            if v and c.get('mapping'):
                v = get_category_level1_mapped(v, customer_code)
            props[col] = v if v is not None else ''
        elif c.get('type') == 'image':
            props[col] = get_image_url(abbr, c.get('image_type', 'vertical'), customer_code)
        elif c.get('type') == 'product_category':
            cat1 = data.get('category_level1_henan') or data.get('category_level1') or ''
            props[col] = get_product_category(cat1, customer_code) if cat1 else ''
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


def build_episodes(drama_id, media_name, total_episodes, data, customer_code, scan_results):
    """构建子集数据列表"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    abbr = get_pinyin_abbr(media_name)
    cat1 = data.get('category_level1_henan') or data.get('category_level1') or ''
    content_dir = get_content_dir(cat1, customer_code) if cat1 else ''
    
    result = []
    for ep in range(1, total_episodes + 1):
        ep_name = f"{media_name}第{ep:02d}集"
        match = scan_results.get(ep_name, {})
        dur = match.get('duration', 0)
        dur_formatted = match.get('duration_formatted', '00000000')
        size = match.get('size', 0)
        
        props = {}
        for c in config.get('episode_columns', []):
            col = c['col']
            if 'field' in c:
                continue
            if 'value' in c:
                props[col] = c['value']
            elif c.get('type') == 'media_url':
                props[col] = get_media_url(abbr, ep, content_dir, customer_code)
            elif c.get('type') == 'episode_num':
                props[col] = ep
            elif c.get('type') == 'duration':
                props[col] = dur_formatted
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


# ============================================================
# 常量定义
# ============================================================

# Excel列名映射
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

# 数值字段类型
NUMERIC_FIELDS = {
    'episode_count': int, 
    'production_year': int, 
    'single_episode_duration': float, 
    'total_duration': float, 
    'rating': float
}

# 版权表插入字段
INSERT_FIELDS = [
    'media_name', 'upstream_copyright', 'category_level1', 'category_level2', 
    'category_level1_henan', 'category_level2_henan', 'episode_count', 
    'single_episode_duration', 'total_duration', 'production_year', 'production_region', 
    'language', 'language_henan', 'country', 'director', 'screenwriter', 'cast_members', 
    'recommendation', 'synopsis', 'keywords', 'video_quality', 'license_number', 
    'rating', 'exclusive_status', 'copyright_start_date', 'copyright_end_date',
    'category_level2_shandong', 'authorization_region', 'authorization_platform', 
    'cooperation_mode', 'drama_ids'
]
