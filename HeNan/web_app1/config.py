# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'polarbear',
    'database': 'operation_management',
    'charset': 'utf8mb4'
}

# 剧头数据列名顺序
DRAMA_HEADER_COLUMNS = [
    '剧头id', '剧集名称', '作者列表', '清晰度', '语言', '主演', '内容类型', '上映年份',
    '关键字', '评分', '推荐语', '总集数', '产品分类', '竖图', '描述', '横图', '版权', '二级分类'
]

# 子集数据列名顺序
SUBSET_COLUMNS = [
    '子集id', '节目名称', '媒体拉取地址', '媒体类型', '编码格式', '集数', '时长', '文件大小'
]

# 动态属性字段
DRAMA_DYNAMIC_FIELDS = [
    '作者列表', '清晰度', '语言', '主演', '内容类型', '上映年份',
    '关键字', '评分', '推荐语', '总集数', '产品分类', '竖图',
    '描述', '横图', '版权', '二级分类'
]

EPISODE_DYNAMIC_FIELDS = ['媒体拉取地址', '媒体类型', '编码格式', '集数', '时长', '文件大小']

# 版权方数据字段
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
