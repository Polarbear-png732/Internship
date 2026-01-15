# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'polarbear',
    'database': 'operation_management',
    'charset': 'utf8mb4'
}

# 版权方数据字段（用于API）
COPYRIGHT_FIELDS = [
    'media_name', 'upstream_copyright', 'category_level1', 'category_level2',
    'category_level1_henan', 'category_level2_henan', 'episode_count', 
    'single_episode_duration', 'total_duration', 'production_year', 'production_region', 
    'language', 'language_henan', 'country', 'director', 'screenwriter', 'cast_members', 
    'recommendation', 'synopsis', 'keywords', 'video_quality', 'license_number', 
    'rating', 'exclusive_status', 'copyright_start_date', 'copyright_end_date',
    'category_level2_shandong', 'authorization_region', 'authorization_platform', 
    'cooperation_mode'
]

# ============================================================
# 多客户配置
# ============================================================

CUSTOMER_CONFIGS = {
    'henan_mobile': {
        'name': '河南移动',
        'code': 'hnyd',
        'is_enabled': True,
        'export_sheets': ['剧头', '子集'],
        
        # 剧头字段配置
        'drama_columns': [
            {'col': '剧头id', 'field': 'drama_id'},
            {'col': '剧集名称', 'field': 'drama_name'},
            {'col': '作者列表', 'source': 'director', 'default': '暂无'},
            {'col': '清晰度', 'value': 1},
            {'col': '语言', 'source': 'language_henan', 'default': '简体中文'},
            {'col': '主演', 'source': 'cast_members', 'default': ''},
            {'col': '内容类型', 'source': 'category_level1_henan', 'default': '少儿'},
            {'col': '上映年份', 'source': 'production_year'},
            {'col': '关键字', 'source': 'keywords', 'default': ''},
            {'col': '评分', 'source': 'rating'},
            {'col': '推荐语', 'source': 'recommendation', 'default': ''},
            {'col': '总集数', 'source': 'episode_count', 'default': 0},
            {'col': '产品分类', 'type': 'product_category'},
            {'col': '竖图', 'type': 'image', 'image_type': 'vertical'},
            {'col': '描述', 'source': 'synopsis', 'default': ''},
            {'col': '横图', 'type': 'image', 'image_type': 'horizontal'},
            {'col': '版权', 'value': 1},
            {'col': '二级分类', 'source': 'category_level2_henan', 'default': ''},
        ],
        
        # 子集字段配置
        'episode_columns': [
            {'col': '子集id', 'field': 'episode_id'},
            {'col': '节目名称', 'field': 'episode_name'},
            {'col': '媒体拉取地址', 'type': 'media_url'},
            {'col': '媒体类型', 'value': 1},
            {'col': '编码格式', 'value': 1},
            {'col': '集数', 'type': 'episode_num'},
            {'col': '时长', 'type': 'duration'},
            {'col': '文件大小', 'type': 'file_size'},
        ],
        
        # URL模板
        'image_url': {
            'vertical': 'http://36.133.168.235:18181/img/{abbr}_st.jpg',
            'horizontal': 'http://36.133.168.235:18181/img/{abbr}_ht.jpg',
        },
        'media_url_template': 'ftp://ftpmediazjyd:rD2q0y1M5eI@36.133.168.235:2121/media/hnyd/{dir}/{abbr}/{abbr}{ep:03d}.ts',
        
        # 映射配置
        'content_dir_map': {'儿童': 'shaoer', '教育': 'mqxt', '电竞': 'rywg', '_default': 'shaoer'},
        'product_category_map': {'教育': 1, '电竞': 2, '_default': 3},
    },
    
    'shandong_mobile': {
        'name': '山东移动',
        'code': 'sdyd',
        'is_enabled': True,
        'export_sheets': ['剧头', '子集'],
        
        'drama_columns': [
            {'col': '剧头id', 'field': 'drama_id'},
            {'col': '剧集名称', 'field': 'drama_name'},
            {'col': '导演', 'source': 'director', 'default': '佚名'},
            {'col': '清晰度', 'value': 1},
            {'col': '总集数', 'source': 'episode_count', 'default': 0},
            {'col': '主演', 'source': 'cast_members', 'default': '佚名'},
            {'col': '一级分类', 'value': '电竞'},
            {'col': '二级分类', 'source': 'category_level2_shandong', 'default': '游戏主播|休闲'},
            {'col': '国家地区', 'source': 'country', 'default': '中国'},
            {'col': '上映年份', 'source': 'production_year'},
            {'col': '语言', 'source': 'language', 'default': '普通话'},
            {'col': '竖版大海报地址', 'type': 'image', 'image_type': 'vertical'},
            {'col': '横版海报地址', 'type': 'image', 'image_type': 'horizontal'},
            {'col': '产品分类', 'value': 1},
            {'col': '描述', 'source': 'synopsis', 'default': '', 'suffix': '内容来源：杭州维高'},
            {'col': '是否多集', 'type': 'is_multi_episode'},
            {'col': '单集时长（分）', 'type': 'total_duration_seconds'},
            {'col': '评分', 'source': 'rating'},
            {'col': '编剧', 'source': 'screenwriter', 'default': '佚名'},
            {'col': '版权开始时间', 'source': 'copyright_start_date', 'format': 'datetime'},
            {'col': '版权结束时间', 'source': 'copyright_end_date', 'format': 'datetime'},
            {'col': '是否付费', 'value': 1},
        ],
        
        'episode_columns': [
            {'col': '子集id', 'field': 'episode_id'},
            {'col': '节目名称', 'type': 'episode_name_format', 'format': '{drama_name}第{ep}集'},
            {'col': '媒体拉取地址', 'type': 'media_url'},
            {'col': 'md5', 'type': 'md5'},
            {'col': '时长（分）', 'type': 'duration_minutes'},
            {'col': '集数', 'type': 'episode_num'},
            {'col': '是否付费', 'value': 1},
            {'col': '片头跳过时间点（整数秒）', 'value': 0},
            {'col': '片尾跳过时间点（整数秒）', 'value': 0},
        ],
        
        'image_url': {
            'vertical': 'http://120.27.12.82:28080/img/sdyd/{abbr}01.jpg',
            'horizontal': 'http://120.27.12.82:28080/img/sdyd/{abbr}02.jpg',
        },
        'media_url_template': 'http://120.27.12.82:28080/hls/sdyd/{abbr}/{abbr}{ep:03d}/index.m3u8',
        
        'content_dir_map': {'_default': 'sdyd'},
        'product_category_map': {'_default': 1},
    },
    
    'gansu_mobile': {
        'name': '甘肃移动',
        'code': 'gsyd',
        'is_enabled': True,
        'export_sheets': ['剧头', '子集'],
        
        'drama_columns': [
            {'col': '剧头id', 'field': 'drama_id'},
            {'col': '剧集名称', 'field': 'drama_name'},
            {'col': '导演', 'source': 'director', 'default': '佚名'},
            {'col': '清晰度', 'value': 1},
            {'col': '总集数', 'source': 'episode_count', 'default': 0},
            {'col': '主演', 'source': 'cast_members', 'default': '佚名'},
            {'col': '一级分类', 'source': 'category_level1', 'default': '体育'},
            {'col': '二级分类', 'source': 'category_level2', 'default': '电竞'},
            {'col': '国家地区', 'source': 'country', 'default': '中国'},
            {'col': '上映年份', 'source': 'production_year'},
            {'col': '语言', 'source': 'language', 'default': '普通话'},
            {'col': '竖版大海报地址', 'type': 'image', 'image_type': 'vertical'},
            {'col': '横版海报地址', 'type': 'image', 'image_type': 'horizontal'},
            {'col': '产品分类', 'type': 'product_category'},
            {'col': '描述', 'source': 'synopsis', 'default': ''},
            {'col': '是否多集', 'type': 'is_multi_episode'},
            {'col': '单集时长（分）', 'source': 'single_episode_duration'},
            {'col': '评分', 'source': 'rating'},
            {'col': '编剧', 'source': 'screenwriter', 'default': '佚名'},
            {'col': '版权开始时间', 'source': 'copyright_start_date', 'format': 'datetime'},
            {'col': '版权结束时间', 'source': 'copyright_end_date', 'format': 'datetime'},
            {'col': '集数', 'source': 'episode_count'},
        ],
        
        'episode_columns': [
            {'col': '子集id', 'field': 'episode_id'},
            {'col': '节目名称', 'type': 'episode_name_format', 'format': '{drama_name}第{ep}集'},
            {'col': '媒体拉取地址', 'type': 'media_url'},
            {'col': '集数', 'type': 'episode_num'},
            {'col': 'md5值', 'type': 'md5'},
        ],
        
        'image_url': {
            'vertical': 'http://120.27.12.82:28080/img/gsyd/{abbr}01.jpg',
            'horizontal': 'http://120.27.12.82:28080/img/gsyd/{abbr}02.jpg',
        },
        'media_url_template': 'ftp://ftpmedia:rD2q0y!M5eI2@36.133.168.235:2121/media/gsyd/{dir}/{abbr}/{abbr}{ep:03d}.ts',
        
        'content_dir_map': {'体育': 'dianjing', '教育': 'jiaoyu', '动漫': 'dongman', '_default': 'jiaoyu'},
        'product_category_map': {'教育': 1, '体育': 2, '动漫': 3, '_default': 2},
    },
    
    'jiangsu_newmedia': {
        'name': '江苏新媒体',
        'code': 'jsnmt',
        'is_enabled': True,
        'export_sheets': ['剧头', '子集', '图片'],
        
        'drama_columns': [
            {'col': 'vod_no', 'type': 'sequence'},
            {'col': 'sId', 'field': 'drama_id'},
            {'col': 'appId', 'value': 2},
            {'col': 'seriesName', 'field': 'drama_name'},
            {'col': 'volumnCount', 'source': 'episode_count', 'default': 0},
            {'col': 'description', 'source': 'synopsis', 'default': ''},
            {'col': 'seriesFlag', 'value': 1},
            {'col': 'sortName', 'type': 'pinyin_abbr'},
            {'col': 'programType', 'value': '维高绘本'},
            {'col': 'releaseYear', 'source': 'production_year'},
            {'col': 'language', 'source': 'language', 'default': '国语'},
            {'col': 'rating', 'source': 'rating'},
            {'col': 'originalCountry', 'source': 'country', 'default': '中国'},
            {'col': 'pgmCategory', 'value': '少儿'},
            {'col': 'pgmSedClass', 'value': '启蒙,教育,益智'},
            {'col': 'director', 'source': 'director', 'default': '佚名'},
            {'col': 'actorDisplay', 'source': 'cast_members', 'default': '佚名'},
        ],
        
        'episode_columns': [
            {'col': 'vod_info_no', 'type': 'sequence'},
            {'col': 'vod_no', 'type': 'drama_sequence'},
            {'col': 'sId', 'field': 'drama_id'},
            {'col': 'pId', 'field': 'episode_id'},
            {'col': 'programName', 'type': 'episode_name_format', 'format': '{drama_name} {ep:03d} HD'},
            {'col': 'volumnCount', 'type': 'episode_num'},
            {'col': 'type', 'value': 1},
            {'col': 'fileURL', 'type': 'media_url'},
            {'col': 'duration', 'type': 'duration_hhmmss'},
            {'col': 'bitRateType', 'value': 8},
            {'col': 'mediaSpec', 'value': 'TS-VBR-H.264-8000-1080i-25-MP2-128'},
        ],
        
        'picture_columns': [
            {'col': 'picture_no', 'type': 'sequence'},
            {'col': 'vod_no', 'type': 'drama_sequence'},
            {'col': 'sId', 'field': 'drama_id'},
            {'col': 'picId', 'value': None},
            {'col': 'type', 'type': 'picture_type'},
            {'col': 'sequence', 'type': 'picture_sequence'},
            {'col': 'fileURL', 'type': 'picture_url'},
        ],
        
        'image_url': {
            'vertical': '/img/{abbr}/0.jpg',
            'horizontal': '/img/{abbr}/1.jpg',
        },
        'media_url_template': '/vod/{abbr}/{abbr}{ep:02d}.ts',
        
        'content_dir_map': {'_default': ''},
        'product_category_map': {'_default': 0},
    },
}

def get_enabled_customers():
    """获取所有启用的客户代码列表"""
    return [code for code, config in CUSTOMER_CONFIGS.items() if config.get('is_enabled', True)]

def get_customer_config(customer_code):
    """获取指定客户的配置"""
    return CUSTOMER_CONFIGS.get(customer_code)

def get_all_customer_names():
    """获取所有客户名称映射"""
    return {code: config['name'] for code, config in CUSTOMER_CONFIGS.items()}
