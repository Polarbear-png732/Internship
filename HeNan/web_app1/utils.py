import json
from pypinyin import pinyin, Style
from config import CUSTOMER_CONFIGS


def parse_json(data, field='dynamic_properties'):
    """解析 JSON 字段，返回字典"""
    if data and data.get(field):
        val = data[field]
        return json.loads(val) if isinstance(val, str) else val
    return {}


def build_drama_dict(drama, props=None):
    """构建剧头数据字典（河南移动格式，保持兼容）"""
    if props is None:
        props = parse_json(drama)
    return {
        '剧头id': drama['drama_id'],
        '剧集名称': drama['drama_name'],
        '作者列表': props.get('作者列表', ''),
        '清晰度': props.get('清晰度', 0),
        '语言': props.get('语言', ''),
        '主演': props.get('主演', ''),
        '内容类型': props.get('内容类型', ''),
        '上映年份': props.get('上映年份', 0),
        '关键字': props.get('关键字', ''),
        '评分': props.get('评分', 0.0),
        '推荐语': props.get('推荐语', ''),
        '总集数': props.get('总集数', 0),
        '产品分类': props.get('产品分类', 0),
        '竖图': props.get('竖图', ''),
        '描述': props.get('描述', ''),
        '横图': props.get('横图', ''),
        '版权': props.get('版权', 0),
        '二级分类': props.get('二级分类', '')
    }


def build_episode_dict(episode, props=None):
    """构建子集数据字典（河南移动格式，保持兼容）"""
    if props is None:
        props = parse_json(episode)
    return {
        '子集id': episode['episode_id'],
        '节目名称': episode['episode_name'],
        '媒体拉取地址': props.get('媒体拉取地址', ''),
        '媒体类型': props.get('媒体类型', 0),
        '编码格式': props.get('编码格式', 0),
        '集数': props.get('集数', 0),
        '时长': props.get('时长', 0),
        '文件大小': props.get('文件大小', 0)
    }


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
    return mapping.get('_default', 3)


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
    # 如果已经是正确格式，直接返回
    if isinstance(date_str, str) and len(date_str) >= 10:
        return date_str
    return str(date_str)
