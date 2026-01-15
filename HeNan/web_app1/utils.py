import json
from pypinyin import pinyin, Style


def parse_json(data, field='dynamic_properties'):
    """解析 JSON 字段，返回字典"""
    if data and data.get(field):
        val = data[field]
        return json.loads(val) if isinstance(val, str) else val
    return {}


def build_drama_dict(drama, props=None):
    """构建剧头数据字典"""
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
    """构建子集数据字典"""
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


def get_content_dir(content_type):
    """根据内容类型获取媒体目录"""
    if "教育" in str(content_type):
        return "mqxt"
    elif "电竞" in str(content_type):
        return "rywg"
    return "shaoer"


def get_product_category(content_type):
    """根据内容类型获取产品分类"""
    if content_type:
        if "教育" in str(content_type):
            return 1
        elif "电竞" in str(content_type):
            return 2
    return 3
