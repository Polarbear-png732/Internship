"""
内存缓存服务
提供简单的内存缓存机制，用于频繁查询的数据缓存
支持 TTL（过期时间）和手动失效
"""
import time
from typing import Any, Optional, Callable
from functools import wraps
import threading


class CacheEntry:
    """缓存条目"""
    __slots__ = ['value', 'expire_at']
    
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expire_at = time.time() + ttl if ttl > 0 else float('inf')
    
    def is_expired(self) -> bool:
        return time.time() > self.expire_at


class MemoryCache:
    """
    线程安全的内存缓存
    
    使用示例:
        cache = MemoryCache()
        
        # 基本用法
        cache.set('key', 'value', ttl=300)  # 缓存5分钟
        value = cache.get('key')
        
        # 装饰器用法
        @cache.cached(prefix='user', ttl=600)
        def get_user(user_id):
            return db.query_user(user_id)
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        初始化缓存
        
        Args:
            default_ttl: 默认过期时间（秒），默认5分钟
            max_size: 最大缓存条目数
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """设置缓存值"""
        if ttl is None:
            ttl = self._default_ttl
        
        with self._lock:
            # 如果超过最大容量，清理过期条目
            if len(self._cache) >= self._max_size:
                self._cleanup_expired()
            
            # 如果还是超过，清理最旧的 10% 条目
            if len(self._cache) >= self._max_size:
                self._evict_oldest(int(self._max_size * 0.1))
            
            self._cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def invalidate_prefix(self, prefix: str) -> int:
        """删除指定前缀的所有缓存条目"""
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def _cleanup_expired(self) -> int:
        """清理过期条目"""
        keys_to_delete = [k for k, v in self._cache.items() if v.is_expired()]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete)
    
    def _evict_oldest(self, count: int) -> None:
        """驱逐最快过期的条目"""
        if count <= 0:
            return
        sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k].expire_at)
        for key in sorted_keys[:count]:
            del self._cache[key]
    
    def stats(self) -> dict:
        """获取缓存统计信息"""
        with self._lock:
            total = self._hits + self._misses
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(self._hits / total, 4) if total > 0 else 0
            }
    
    def cached(self, prefix: str = '', ttl: int = None, key_builder: Callable = None):
        """
        缓存装饰器
        
        Args:
            prefix: 缓存键前缀
            ttl: 过期时间（秒）
            key_builder: 自定义键生成函数，接收 (*args, **kwargs) 返回字符串
        
        Usage:
            @cache.cached(prefix='drama', ttl=300)
            def get_drama(drama_id):
                ...
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 构建缓存键
                if key_builder:
                    cache_key = f"{prefix}:{key_builder(*args, **kwargs)}"
                else:
                    key_parts = [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
                    cache_key = f"{prefix}:{':'.join(key_parts)}" if key_parts else prefix
                
                # 尝试从缓存获取
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # 执行函数并缓存结果
                result = func(*args, **kwargs)
                if result is not None:
                    self.set(cache_key, result, ttl)
                return result
            
            # 添加缓存失效方法
            wrapper.invalidate = lambda *args, **kwargs: self.delete(
                f"{prefix}:{key_builder(*args, **kwargs)}" if key_builder 
                else f"{prefix}:{':'.join([str(a) for a in args] + [f'{k}={v}' for k, v in sorted(kwargs.items())])}"
            )
            wrapper.invalidate_all = lambda: self.invalidate_prefix(prefix)
            
            return wrapper
        return decorator


# 全局缓存实例
_global_cache = None
_cache_lock = threading.Lock()


def get_cache() -> MemoryCache:
    """获取全局缓存实例（单例模式）"""
    global _global_cache
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = MemoryCache(default_ttl=300, max_size=2000)
    return _global_cache


# 预定义的缓存键前缀
class CacheKeys:
    """缓存键前缀常量"""
    CUSTOMER_CONFIG = "config:customer"
    DRAMA_LIST = "drama:list"
    DRAMA_DETAIL = "drama:detail"
    COPYRIGHT_LIST = "copyright:list"
    COPYRIGHT_DETAIL = "copyright:detail"
    PINYIN_ABBR = "pinyin:abbr"


# 便捷函数
def cached_query(prefix: str, ttl: int = 300):
    """
    查询缓存装饰器的便捷函数
    
    Usage:
        @cached_query('drama:list', ttl=300)
        def get_dramas(customer_code, page):
            ...
    """
    return get_cache().cached(prefix=prefix, ttl=ttl)
