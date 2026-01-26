"""
服务层模块包
包含Excel导入/导出服务、剧集查询服务、版权服务、缓存服务等业务逻辑处理模块
"""
# Services module
from .import_service import ExcelImportService, ImportTask
from .drama_service import (
    DramaQueryService,
    build_drama_display_dict, build_drama_display_dict_fast,
    build_episode_display_dict, build_episode_display_dict_fast,
    get_column_names, build_picture_data, build_picture_data_fast,
    preprocess_dramas, preprocess_episodes, group_episodes_by_drama,
    JIANGSU_HEADERS, JIANGSU_COL_WIDTHS
)
from .export_service import ExcelExportService
from .copyright_service import (
    CopyrightDramaService, CopyrightQueryService,
    COPYRIGHT_EXPORT_COLUMNS, convert_decimal, convert_row
)
from .cache_service import (
    MemoryCache, get_cache, CacheKeys, cached_query
)

__all__ = [
    # 导入服务
    'ExcelImportService', 'ImportTask',
    # 剧集服务
    'DramaQueryService',
    'build_drama_display_dict', 'build_drama_display_dict_fast',
    'build_episode_display_dict', 'build_episode_display_dict_fast',
    'get_column_names', 'build_picture_data', 'build_picture_data_fast',
    'preprocess_dramas', 'preprocess_episodes', 'group_episodes_by_drama',
    'JIANGSU_HEADERS', 'JIANGSU_COL_WIDTHS',
    # 导出服务
    'ExcelExportService',
    # 版权服务
    'CopyrightDramaService', 'CopyrightQueryService',
    'COPYRIGHT_EXPORT_COLUMNS', 'convert_decimal', 'convert_row',
    # 缓存服务
    'MemoryCache', 'get_cache', 'CacheKeys', 'cached_query',
]
