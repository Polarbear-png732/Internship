"""
数据库连接池管理
"""
from contextlib import contextmanager
import pymysql
from dbutils.pooled_db import PooledDB
import logging

from config import DB_CONFIG

logger = logging.getLogger(__name__)

# 连接池配置
POOL_CONFIG = {
    'creator': pymysql,
    'maxconnections': 20,      # 最大连接数
    'mincached': 5,            # 初始化时创建的连接数
    'maxcached': 10,           # 最大空闲连接数
    'maxshared': 0,            # 最大共享连接数（0表示所有连接都是专用的）
    'blocking': True,          # 连接池耗尽时是否阻塞等待
    'maxusage': None,          # 单个连接最大复用次数
    'setsession': [],          # 开始会话前执行的SQL
    'ping': 1,                 # ping MySQL服务器检查连接是否可用
    **DB_CONFIG
}

# 全局连接池实例
_pool = None


def get_pool():
    """获取数据库连接池（单例模式）"""
    global _pool
    if _pool is None:
        logger.info("初始化数据库连接池...")
        _pool = PooledDB(**POOL_CONFIG)
        logger.info(f"数据库连接池初始化完成，最大连接数: {POOL_CONFIG['maxconnections']}")
    return _pool


def close_pool():
    """关闭连接池"""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
        logger.info("数据库连接池已关闭")


@contextmanager
def get_db():
    """从连接池获取数据库连接（上下文管理器）"""
    pool = get_pool()
    conn = pool.connection()
    try:
        yield conn
    finally:
        conn.close()  # 归还连接到连接池


@contextmanager
def get_db_cursor(dict_cursor=True):
    """获取数据库游标的便捷方法"""
    with get_db() as conn:
        cursor_class = pymysql.cursors.DictCursor if dict_cursor else pymysql.cursors.Cursor
        cursor = conn.cursor(cursor_class)
        try:
            yield cursor, conn
        finally:
            cursor.close()


def get_pool_status():
    """获取连接池状态信息"""
    pool = get_pool()
    return {
        'max_connections': POOL_CONFIG['maxconnections'],
        'min_cached': POOL_CONFIG['mincached'],
        'max_cached': POOL_CONFIG['maxcached'],
    }
