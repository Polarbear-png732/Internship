from contextlib import contextmanager
import pymysql
from config import DB_CONFIG


@contextmanager
def get_db():
    """数据库连接上下文管理器，自动关闭连接"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()
