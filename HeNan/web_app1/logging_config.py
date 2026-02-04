"""
日志配置模块
使用 loguru 提供结构化日志记录，支持控制台和文件输出
"""
import sys
from pathlib import Path
from loguru import logger

# ============================================================
# 日志配置
# ============================================================

# 日志目录
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 移除默认处理器
logger.remove()

# 控制台输出 - 彩色格式，INFO及以上级别
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# 普通日志文件 - 每天轮换，保留30天
logger.add(
    LOG_DIR / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="00:00",  # 每天午夜轮换
    retention="30 days",  # 保留30天
    encoding="utf-8",
    enqueue=True  # 异步写入，提高性能
)

# 错误日志文件 - 单独记录ERROR及以上级别
logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
    level="ERROR",
    rotation="00:00",
    retention="60 days",  # 错误日志保留更久
    encoding="utf-8",
    enqueue=True,
    backtrace=True,  # 启用详细的错误追踪
    diagnose=True    # 显示变量值
)


def get_logger(name: str = None):
    """
    获取带模块名称的日志器
    
    Args:
        name: 模块名称，如 "routers.dramas"
    
    Returns:
        配置好的 logger 实例
    """
    if name:
        return logger.bind(name=name)
    return logger


# 导出主日志器
__all__ = ['logger', 'get_logger']
