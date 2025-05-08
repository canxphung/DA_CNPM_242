# src/core/cache_manager.py
import os
import sys
import json
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.external_api.cache_manager import CacheManager
from config.config import CACHE_STORAGE_PATH

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('cache_manager')

class APICacheManager:
    """
    Manager for API response caching and optimization.
    """
    
    def __init__(self):
        """Initialize the API cache manager."""
        self.cache_dir = os.path.join(CACHE_STORAGE_PATH, 'api_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Create cache storages with different TTLs
        self.short_cache = CacheManager(
            os.path.join(self.cache_dir, 'short'),
            ttl=3600  # 1 hour
        )
        
        self.medium_cache = CacheManager(
            os.path.join(self.cache_dir, 'medium'),
            ttl=86400  # 24 hours
        )
        
        self.long_cache = CacheManager(
            os.path.join(self.cache_dir, 'long'),
            ttl=604800  # 1 week
        )
        
        # Cache usage statistics
        self.hit_count = 0
        self.miss_count = 0
        self.last_maintenance = datetime.now()
    
    def get(self, key, cache_type='medium'):
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            cache_type: Type of cache ('short', 'medium', 'long')
            
        Returns:
            Cached value or None
        """
        cache = self._get_cache_by_type(cache_type)
        value = cache.get(key)
        
        if value is not None:
            self.hit_count += 1
            logger.debug(f"Cache hit for key: {key}")
            return value
        
        self.miss_count += 1
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    def set(self, key, value, cache_type='medium'):
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            cache_type: Type of cache ('short', 'medium', 'long')
            
        Returns:
            True if successful
        """
        cache = self._get_cache_by_type(cache_type)
        logger.debug(f"Caching value with key: {key}")
        return cache.set(key, value)
    
    def perform_maintenance(self, force=False):
        """
        Perform cache maintenance (clear expired items).
        
        Args:
            force: Whether to force maintenance regardless of last run time
            
        Returns:
            Number of items cleared
        """
        now = datetime.now()
        # Only run maintenance once a day unless forced
        if not force and now - self.last_maintenance < timedelta(days=1):
            return 0
        
        logger.info("Performing cache maintenance")
        
        count = 0
        count += self.short_cache.clear_expired()
        count += self.medium_cache.clear_expired()
        count += self.long_cache.clear_expired()
        
        self.last_maintenance = now
        
        logger.info(f"Cache maintenance complete. Cleared {count} items")
        return count
    
    def get_stats(self):
        """
        Get cache usage statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate,
            'last_maintenance': self.last_maintenance.isoformat()
        }
    
    def clear_cache(self, cache_type=None):
        """
        Clear all items from the cache.
        
        Args:
            cache_type: Optional type to clear (or all if None)
            
        Returns:
            Number of items cleared
        """
        count = 0
        
        if cache_type is None or cache_type == 'short':
            count += self.short_cache.clear_all()
        
        if cache_type is None or cache_type == 'medium':
            count += self.medium_cache.clear_all()
        
        if cache_type is None or cache_type == 'long':
            count += self.long_cache.clear_all()
        
        logger.info(f"Cleared {count} items from cache")
        return count
    
    def _get_cache_by_type(self, cache_type):
        """
        Get cache storage by type.
        
        Args:
            cache_type: Type of cache ('short', 'medium', 'long')
            
        Returns:
            CacheManager instance
        """
        if cache_type == 'short':
            return self.short_cache
        elif cache_type == 'medium':
            return self.medium_cache
        elif cache_type == 'long':
            return self.long_cache
        else:
            logger.warning(f"Unknown cache type: {cache_type}, using medium")
            return self.medium_cache