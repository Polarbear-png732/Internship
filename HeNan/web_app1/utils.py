"""
工具函数模块
包含数据处理、格式化、URL生成等公共函数
"""
import json
import os
import re
import threading
from datetime import datetime
from typing import List
import pandas as pd
from functools import lru_cache
from pypinyin import pinyin, Style, load_phrases_dict
from config import CUSTOMER_CONFIGS


SCAN_MATCH_DEBUG_ENABLED = os.getenv('SCAN_MATCH_DEBUG', '1').lower() in {'1', 'true', 'yes', 'on'}
SCAN_MATCH_DEBUG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
SCAN_MATCH_HIT_LOG = os.path.join(SCAN_MATCH_DEBUG_DIR, 'scan_match_hits.log')
SCAN_MATCH_MISS_LOG = os.path.join(SCAN_MATCH_DEBUG_DIR, 'scan_match_misses.log')
_scan_match_log_lock = threading.Lock()
_scan_match_hit_media_logged = set()
_scan_match_miss_media_logged = set()

SCAN_RULE_LABELS = {
    1: '精确名-三位集数',
    2: '精确名-两位集数',
    3: '精确名-自然数',
    4: '名称+三位数字',
    5: '名称+两位数字',
    6: '名称+自然数',
    7: 'abbr+三位数字',
    8: 'abbr+两位数字',
    9: 'abbr+自然数',
    10: 'abbr前缀扫描',
    11: '文件夹索引-剧名',
    12: '文件夹索引-abbr',
}


def _normalize_match_text(value: str):
    """匹配文本归一化：去空白+小写，用于消除命名中的空格差异"""
    if value is None:
        return ''
    return re.sub(r'\s+', '', str(value)).lower()


def _format_scan_match_debug_log(payload: dict, matched: bool):
    timestamp = payload.get('timestamp', '')
    media_name = payload.get('media_name', '')
    abbr = payload.get('abbr', '')
    episode_num = payload.get('episode_num', '')
    rule = payload.get('rule')
    matched_key = payload.get('matched_key')
    attempts = payload.get('attempts') or []
    result = payload.get('result') or {}
    precheck_reason = payload.get('precheck_reason')

    if matched:
        rule_name = SCAN_RULE_LABELS.get(rule, '未知规则')
        return (
            f"[{timestamp}] 命中 | 剧名={media_name} | 拼音={abbr} | 集数={episode_num} | "
            f"规则={rule}({rule_name}) | key={matched_key} | "
            f"duration={result.get('duration_formatted') or '-'} | "
            f"size={result.get('size_bytes') or '-'} | md5={result.get('md5') or '-'}\n"
        )

    attempt_map = {item.get('rule'): item for item in attempts if isinstance(item, dict)}
    lines = [
        '=== 匹配失败 ===',
        f'时间: {timestamp}',
        f'剧名: {media_name}',
        f'拼音: {abbr}',
        f'集数: {episode_num}',
        '结果: 未命中',
        f'前置原因: {precheck_reason}' if precheck_reason else None,
        '',
        '[规则尝试明细]'
    ]
    lines = [line for line in lines if line is not None]

    for rule_no in range(1, 13):
        label = SCAN_RULE_LABELS.get(rule_no, f'规则{rule_no}')
        attempt = attempt_map.get(rule_no, {})
        matched_flag = bool(attempt.get('matched'))
        status = '命中' if matched_flag else '失败'
        reason = attempt.get('reason', '未执行')

        if rule_no in {1, 2, 3, 4, 5, 6, 7, 8, 9}:
            detail = f"key={attempt.get('key', '-') }"
        elif rule_no == 10:
            detail = (
                f"prefix={attempt.get('prefix', '-')} "
                f"candidates={attempt.get('candidates', 0)}"
            )
        else:
            detail = f"folder={attempt.get('folder', '-')} ep={attempt.get('episode', '-') }"

        lines.append(f"{rule_no:>2}. {label:<12} {detail:<45} -> {status}（{reason}）")

    lines.extend([
        '',
        '[失败结论]',
        '未找到任何可用扫描记录（duration/size/md5 全为空）',
        '================',
        ''
    ])
    return '\n'.join(lines)


def _write_scan_match_debug_log(payload: dict, matched: bool):
    if not SCAN_MATCH_DEBUG_ENABLED:
        return
    try:
        os.makedirs(SCAN_MATCH_DEBUG_DIR, exist_ok=True)
        target_file = SCAN_MATCH_HIT_LOG if matched else SCAN_MATCH_MISS_LOG
        media_name = str(payload.get('media_name') or '').strip()
        log_text = _format_scan_match_debug_log(payload, matched)
        with _scan_match_log_lock:
            if media_name:
                logged_set = _scan_match_hit_media_logged if matched else _scan_match_miss_media_logged
                if media_name in logged_set:
                    return
                logged_set.add(media_name)
            with open(target_file, 'a', encoding='utf-8') as f:
                f.write(log_text)
    except Exception:
        pass


# ============================================================
# JSON 解析
# ============================================================

def parse_json(data, field='dynamic_properties'):
    """解析 JSON 字段，返回字典"""
    if data and data.get(field):
        val = data[field]
        return json.loads(val) if isinstance(val, str) else val
    return {}


def _normalize_operator_text(value: str) -> str:
    """运营商名称归一化：去空白并转小写。"""
    return re.sub(r'\s+', '', str(value or '')).lower()


def get_customer_codes_by_operator(operator_name: str, enabled_only: bool = True) -> List[str]:
    """根据版权行中的运营商名称匹配目标客户代码（支持多值分隔）。"""
    raw_text = str(operator_name or '').strip()
    if not raw_text:
        return []

    parts = re.split(r'[,，;；、|/]+', raw_text)
    tokens = [_normalize_operator_text(part) for part in parts if _normalize_operator_text(part)]
    if not tokens:
        return []

    matched_codes = []
    for customer_code, cfg in CUSTOMER_CONFIGS.items():
        if enabled_only and not cfg.get('is_enabled', True):
            continue

        customer_name = _normalize_operator_text(cfg.get('name', ''))
        short_code = _normalize_operator_text(cfg.get('code', ''))

        for token in tokens:
            if (
                token == customer_name
                or token in customer_name
                or customer_name in token
                or (short_code and (token == short_code or short_code in token))
            ):
                matched_codes.append(customer_code)
                break

    return matched_codes


# ============================================================
# 拼音和URL生成
# ============================================================

@lru_cache(maxsize=10000)
def get_pinyin_abbr(name):
    """生成拼音首字母缩写（带LRU缓存，提升重复调用性能）"""
    if not name:
        return ""

    # 常见多音词纠偏。优先级高于默认词典，避免“音乐/快乐/长大”等误读。
    load_phrases_dict({
        '音乐': [['yin'], ['yue']],
        '快乐': [['kuai'], ['le']],
        '长大': [['zhang'], ['da']],
        '成长': [['cheng'], ['zhang']],
    })

    text = str(name)
    result = []
    # 按中文块/字母数字块切分，中文块整体转拼音，保留上下文解决多音字。
    for part in re.findall(r'[\u4e00-\u9fff]+|[A-Za-z0-9]+', text):
        if re.fullmatch(r'[\u4e00-\u9fff]+', part):
            py_list = pinyin(part, style=Style.FIRST_LETTER, heteronym=False)
            for item in py_list:
                if item and item[0]:
                    result.append(str(item[0])[0].lower())
        else:
            result.append(part.lower())

    return ''.join(result)


def get_content_dir(content_type, customer_code='henan_mobile'):
    """根据内容类型和客户获取媒体目录"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    if content_type:
        content_type = get_category_level1_mapped(content_type, customer_code)
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
        # 使用四舍五入，299秒 -> 5分钟
        return round(total_seconds / 60)
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if format_type == 'HH:MM:SS':
        return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    else:  # HHMMSS00
        return f'{hours:02d}{minutes:02d}{secs:02d}00'


def format_datetime(date_str, format_type='datetime'):
    """格式化日期时间
    format_type: 'datetime' | 'datetime_full' | 'datetime_compact' | 'date_compact'
    - datetime: YYYY-MM-DD HH:mm:ss (默认)
    - datetime_full: YYYY-MM-DD HH:mm:ss (完整格式，确保有时间部分)
    - datetime_compact: YYYYMMDDHHMMSS (紧凑格式，14位数字，如 20260120000000)
    - date_compact: YYYYMMDD (紧凑日期格式，8位数字，如 20251201)
    """
    if not date_str:
        return ''
    
    date_str = str(date_str).strip()
    
    # 紧凑格式：YYYYMMDDHHMMSS（14位数字）
    if format_type == 'datetime_compact':
        import re
        # 移除非数字字符，提取日期时间部分
        digits = re.sub(r'[^\d]', '', date_str)
        
        if len(digits) >= 8:
            year = digits[:4]
            month = digits[4:6]
            day = digits[6:8]
            # 如果有时间部分
            if len(digits) >= 14:
                hour = digits[8:10]
                minute = digits[10:12]
                second = digits[12:14]
            elif len(digits) >= 12:
                hour = digits[8:10]
                minute = digits[10:12]
                second = '00'
            elif len(digits) >= 10:
                hour = digits[8:10]
                minute = '00'
                second = '00'
            else:
                hour, minute, second = '00', '00', '00'
            return f"{year}{month}{day}{hour}{minute}{second}"
        return ''
    
    # 紧凑日期格式：YYYYMMDD（8位数字）
    if format_type == 'date_compact':
        import re
        digits = re.sub(r'[^\d]', '', date_str)
        if len(digits) >= 8:
            return digits[:8]  # 只取年月日部分
        return ''
    
    # 如果已经是完整格式，直接返回
    if isinstance(date_str, str):
        if len(date_str) >= 19 and ':' in date_str:
            return date_str
        # 如果只有日期部分，添加时间
        if format_type == 'datetime_full' and len(date_str) >= 10:
            if ' ' not in date_str:
                return date_str + ' 00:00:00'
            return date_str
        if len(date_str) >= 10:
            return date_str
    
    return str(date_str)


def get_genre(content_type, customer_code='henan_mobile'):
    """根据内容类型和客户获取流派"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    mapping = config.get('genre_map', {})
    if content_type and mapping:
        for key, value in mapping.items():
            if key != '_default' and key in str(content_type):
                return value
    return mapping.get('_default', '')


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


def extract_episode_number(name: str):
    """从文件名或集名中提取集数"""
    if not name:
        return None
    base = os.path.splitext(str(name))[0]
    match = re.search(r'第\s*(\d{1,3})\s*集', base)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d{1,3})$', base)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d{1,3})(?!.*\d)', base)
    if match:
        return int(match.group(1))
    return None


def _chinese_numeral_to_int(text: str):
    """将中文数字（含两）转为整数，失败返回None"""
    if not text:
        return None

    text = str(text).strip()
    if text.isdigit():
        return int(text)

    char_map = {
        '零': 0, '〇': 0,
        '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9
    }
    unit_map = {'十': 10, '百': 100, '千': 1000}

    total = 0
    section = 0
    number = 0
    for ch in text:
        if ch in char_map:
            number = char_map[ch]
        elif ch in unit_map:
            unit = unit_map[ch]
            number = 1 if number == 0 else number
            section += number * unit
            number = 0
        else:
            return None

    total = section + number
    return total if total > 0 else None


def _int_to_chinese_numeral(num: int):
    if not isinstance(num, int) or num <= 0:
        return ''

    digits = '零一二三四五六七八九'
    if num < 10:
        return digits[num]
    if num < 20:
        return '十' if num == 10 else f"十{digits[num - 10]}"
    if num < 100:
        tens = num // 10
        ones = num % 10
        return f"{digits[tens]}十{digits[ones] if ones else ''}"
    return str(num)


def normalize_season_to_arabic(name: str):
    """将“第二季/第2季”等统一为“第2季”"""
    if not name:
        return ''

    def _replace(match):
        season_text = (match.group(1) or '').strip()
        season_num = _chinese_numeral_to_int(season_text)
        if season_num is None:
            return match.group(0)
        return f"第{season_num}季"

    return re.sub(r'第\s*([零〇一二两三四五六七八九十百千\d]+)\s*季', _replace, str(name))


def normalize_season_to_chinese(name: str):
    """将“第2季/第二季”等统一为“第二季”"""
    if not name:
        return ''

    def _replace(match):
        season_text = (match.group(1) or '').strip()
        season_num = _chinese_numeral_to_int(season_text)
        if season_num is None:
            return match.group(0)
        season_cn = _int_to_chinese_numeral(season_num)
        return f"第{season_cn}季" if season_cn else match.group(0)

    return re.sub(r'第\s*([零〇一二两三四五六七八九十百千\d]+)\s*季', _replace, str(name))


def build_media_name_variants(name: str):
    """构建媒体名匹配变体（原始 + 季数中阿双向归一化）"""
    if not name:
        return []

    original = str(name).strip()
    normalized_arabic = normalize_season_to_arabic(original).strip()
    normalized_chinese = normalize_season_to_chinese(original).strip()
    variants = []
    for value in [original, normalized_arabic, normalized_chinese]:
        if value and value not in variants:
            variants.append(value)
    return variants


def find_scan_match(scan_results, media_name, abbr, episode_num):
    """按优先级匹配扫描结果，支持文件名与文件夹命名"""
    if not media_name or not episode_num:
        payload = {
            "timestamp": datetime.now().isoformat(timespec='seconds'),
            "media_name": media_name,
            "abbr": abbr,
            "episode_num": episode_num,
            "matched": False,
            "rule": None,
            "matched_key": None,
            "attempts": [],
            "precheck_reason": "media_name或episode_num为空，未进入规则匹配",
            "result": {
                "duration_formatted": None,
                "size_bytes": None,
                "md5": None,
            }
        }
        _write_scan_match_debug_log(payload, False)
        return {}

    if not scan_results:
        payload = {
            "timestamp": datetime.now().isoformat(timespec='seconds'),
            "media_name": media_name,
            "abbr": abbr,
            "episode_num": episode_num,
            "matched": False,
            "rule": None,
            "matched_key": None,
            "attempts": [],
            "precheck_reason": "scan_results为空，未进入规则匹配",
            "result": {
                "duration_formatted": None,
                "size_bytes": None,
                "md5": None,
            }
        }
        _write_scan_match_debug_log(payload, False)
        return {}

    attempts = []
    match = {}
    matched_rule = None
    matched_key = None
    normalized_scan_map = {}
    normalized_origin_key_map = {}

    for scan_key, scan_value in scan_results.items():
        if scan_key == '_folder_index' or not isinstance(scan_key, str):
            continue
        normalized_key = _normalize_match_text(scan_key)
        if normalized_key and normalized_key not in normalized_scan_map:
            normalized_scan_map[normalized_key] = scan_value
            normalized_origin_key_map[normalized_key] = scan_key

    def _lookup_scan_value(candidate_key: str):
        normalized_candidate = _normalize_match_text(candidate_key)
        hit = normalized_scan_map.get(normalized_candidate, {})
        origin_key = normalized_origin_key_map.get(normalized_candidate)
        return hit, origin_key

    media_name_variants = build_media_name_variants(media_name)

    candidate_rules = []
    for media_name_variant in media_name_variants:
        candidate_rules.extend([
            (1, f"{media_name_variant}第{episode_num:03d}集"),
            (2, f"{media_name_variant}第{episode_num:02d}集"),
            (3, f"{media_name_variant}第{episode_num}集"),
            (4, f"{media_name_variant}{episode_num:03d}"),
            (5, f"{media_name_variant}{episode_num:02d}"),
            (6, f"{media_name_variant}{episode_num}"),
        ])
    if abbr:
        candidate_rules.extend([
            (7, f"{abbr}{episode_num:03d}"),
            (8, f"{abbr}{episode_num:02d}"),
            (9, f"{abbr}{episode_num}"),
        ])

    for rule_no, key in candidate_rules:
        match, origin_key = _lookup_scan_value(key)
        attempts.append({
            "rule": rule_no,
            "key": key,
            "matched": bool(match),
            "reason": "命中" if match else "索引无此键"
        })
        if match:
            matched_rule = rule_no
            matched_key = origin_key or key
            break

    if not match and abbr:
        abbr_prefix = _normalize_match_text(abbr)
        prefix_candidate_count = 0
        for normalized_key, candidate in normalized_scan_map.items():
            if not normalized_key.startswith(abbr_prefix):
                continue
            prefix_candidate_count += 1
            origin_key = normalized_origin_key_map.get(normalized_key)
            ep = extract_episode_number(origin_key)
            if ep == episode_num:
                match = candidate or {}
                matched_rule = 10
                matched_key = origin_key
                break

        if match:
            rule10_reason = "命中"
        elif prefix_candidate_count == 0:
            rule10_reason = "无候选文件名前缀"
        else:
            rule10_reason = "候选存在但提取集数不一致"

        attempts.append({
            "rule": 10,
            "prefix": abbr,
            "candidates": prefix_candidate_count,
            "matched": bool(match),
            "reason": rule10_reason
        })

    if not match:
        folder_index = scan_results.get('_folder_index', {})
        normalized_folder_index = {
            _normalize_match_text(folder_name): folder_data
            for folder_name, folder_data in folder_index.items()
            if isinstance(folder_name, str)
        }

        for media_name_variant in media_name_variants:
            folder_match = normalized_folder_index.get(_normalize_match_text(media_name_variant), {})
            match = folder_match.get(episode_num, {}) if folder_match else {}
            if match:
                rule11_reason = "命中"
            elif not folder_match:
                rule11_reason = "文件夹不存在"
            else:
                rule11_reason = "文件夹存在但该集不存在"
            attempts.append({
                "rule": 11,
                "folder": media_name_variant,
                "episode": episode_num,
                "matched": bool(match),
                "reason": rule11_reason
            })
            if match:
                matched_rule = 11
                matched_key = media_name_variant
                break
        if not match and abbr:
            folder_match = normalized_folder_index.get(_normalize_match_text(abbr), {})
            match = folder_match.get(episode_num, {}) if folder_match else {}
            if match:
                rule12_reason = "命中"
            elif not folder_match:
                rule12_reason = "文件夹不存在"
            else:
                rule12_reason = "文件夹存在但该集不存在"
            attempts.append({
                "rule": 12,
                "folder": abbr,
                "episode": episode_num,
                "matched": bool(match),
                "reason": rule12_reason
            })
            if match:
                matched_rule = 12
                matched_key = abbr

    payload = {
        "timestamp": datetime.now().isoformat(timespec='seconds'),
        "media_name": media_name,
        "abbr": abbr,
        "episode_num": episode_num,
        "matched": bool(match),
        "rule": matched_rule,
        "matched_key": matched_key,
        "attempts": attempts,
        "result": {
            "duration_formatted": match.get('duration_formatted') if match else None,
            "size_bytes": match.get('size_bytes') if match else None,
            "md5": match.get('md5') if match else None,
        }
    }
    _write_scan_match_debug_log(payload, bool(match))

    return match or {}



# ============================================================
# 数据构建函数（剧头、子集）
# ============================================================

def build_drama_props(data, media_name, customer_code, scan_results=None, pinyin_cache=None):
    """构建剧头属性（配置驱动）"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    abbr = pinyin_cache.get(media_name) if pinyin_cache else get_pinyin_abbr(media_name)
    props = {}
    
    for c in config.get('drama_columns', []):
        col = c['col']
        if 'field' in c:
            continue
        if 'value' in c:
            props[col] = c['value']
        elif 'source' in c:
            source_name = c.get('source')
            # 版权起止时间不再引用主表默认值，未在客户授权中填写前保持为空
            if source_name in ('copyright_start_date', 'copyright_end_date'):
                v = ''
            else:
                v = data.get(source_name)
            # 只有配置了 default 才使用默认值
            if (v is None or v == '') and 'default' in c:
                v = c['default']
            # 分隔符转换
            if v and c.get('separator'):
                v = re.sub(r'[,，、/／\\]', c['separator'], str(v))
            if v and c.get('suffix'):
                v = str(v) + c['suffix']
            # 日期时间格式化
            if c.get('format') == 'datetime':
                v = format_datetime(v, 'datetime') if v else ''
            elif c.get('format') == 'datetime_full':
                v = format_datetime(v, 'datetime_full') if v else ''
            elif c.get('format') == 'datetime_compact':
                v = format_datetime(v, 'datetime_compact') if v else ''
            elif c.get('format') == 'date_compact':
                v = format_datetime(v, 'date_compact') if v else ''
            # 数值格式化：整数
            elif c.get('format') == 'int':
                try:
                    v = int(float(v)) if v else ''
                except (ValueError, TypeError):
                    v = ''
            # 支持映射转换（如一级分类映射）
            if v and c.get('mapping'):
                v = get_category_level1_mapped(v, customer_code)
            # 字符串长度限制
            if v and c.get('max_length'):
                v = str(v)[:c['max_length']]
            props[col] = v if v is not None else ''
        elif c.get('type') == 'image':
            props[col] = get_image_url(abbr, c.get('image_type', 'vertical'), customer_code)
        elif c.get('type') == 'product_category':
            cat1 = data.get('category_level1') or ''
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
                    match = find_scan_match(scan_results, media_name, abbr, ep)
                    total_dur += match.get('duration', 0)
            props[col] = int(total_dur) if total_dur else 0
        elif c.get('type') == 'pinyin_abbr':
            props[col] = abbr
        elif c.get('type') == 'genre':
            cat1 = data.get('category_level1') or ''
            props[col] = get_genre(cat1, customer_code) if cat1 else ''
        elif c.get('type') == 'sequence':
            props[col] = None
    
    return props


def build_episodes(drama_id, media_name, total_episodes, data, customer_code, scan_results, pinyin_cache=None):
    """构建子集数据列表"""
    config = CUSTOMER_CONFIGS.get(customer_code, {})
    abbr = pinyin_cache.get(media_name) if pinyin_cache else get_pinyin_abbr(media_name)
    cat1 = data.get('category_level1') or ''
    content_dir = get_content_dir(cat1, customer_code) if cat1 else ''
    
    result = []
    for ep in range(1, total_episodes + 1):
        ep_name = f"{media_name}第{ep:02d}集"
        
        match = find_scan_match(scan_results, media_name, abbr, ep)
        
        dur = match.get('duration', 0)
        dur_formatted = match.get('duration_formatted', '00000000')
        size = match.get('size', 0)
        md5_value = match.get('md5', '')
        
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
            elif c.get('type') == 'duration_seconds':
                props[col] = int(dur) if dur else 0
            elif c.get('type') == 'duration_hhmmss':
                props[col] = format_duration(dur, 'HH:MM:SS') if dur else '00:00:00'
            elif c.get('type') == 'file_size':
                props[col] = size
            elif c.get('type') == 'md5':
                props[col] = md5_value
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
    '运营商': 'operator_name',
    '一级分类': 'category_level1', '二级分类': 'category_level2',
    '集数': 'episode_count', '单集时长': 'single_episode_duration', '总时长': 'total_duration',
    '出品年代': 'production_year', '首播日期': 'premiere_date', '制作地区': 'production_region', '出品地区': 'production_region',
    '语言': 'language', '语言-河南标准': 'language_henan', '语言-河南': 'language_henan',
    '国别': 'country', '国家': 'country', '导演': 'director', '编剧': 'screenwriter',
    '主演/嘉宾/主持人': 'cast_members', '主演\\嘉宾\\主持人': 'cast_members', '主演': 'cast_members',
    '作者': 'author',
    '推荐语': 'recommendation', '推荐语/一句话介绍': 'recommendation', '简介': 'synopsis',
    '关键字': 'keywords', '关键词': 'keywords', '清晰度': 'video_quality', '视频质量': 'video_quality',
    '标清\\高清\\4K\\3D\\杜比': 'video_quality', '许可编号': 'license_number', '许可证号': 'license_number',
    '发行许可编号\\备案号等': 'license_number', '评分': 'rating',
    '行业内相关网站的评级、评分（骨朵\\艺恩\\猫眼\\豆瓣\\时光网\\百度\\其他主流视频网站等评分': 'rating',
    '独家/非独': 'exclusive_status', '独家\\非独': 'exclusive_status', '独家状态': 'exclusive_status',
    '版权开始时间': 'copyright_start_date', '版权开始日期': 'copyright_start_date',
    '版权结束时间': 'copyright_end_date', '版权结束日期': 'copyright_end_date',
    '授权区域': 'authorization_region',
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
    'media_name', 'upstream_copyright', 'operator_name', 'category_level1', 'category_level2',
    'episode_count',
    'single_episode_duration', 'total_duration', 'production_year', 'premiere_date',
    'production_region', 'language', 'language_henan', 'country', 'director', 
    'screenwriter', 'cast_members', 'author', 'recommendation', 'synopsis', 
    'keywords', 'video_quality', 'license_number', 'rating', 'exclusive_status', 
    'copyright_start_date', 'copyright_end_date',
    'authorization_region', 'authorization_platform', 'cooperation_mode', 'drama_ids'
]
