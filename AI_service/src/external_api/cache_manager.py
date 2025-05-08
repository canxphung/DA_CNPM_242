# src/external_api/cache_manager.py
import os
import json
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('cache_manager.base')

class CacheManager:
    """
    Basic cache manager for storing and retrieving API responses.
    """
    
    def __init__(self, cache_dir, ttl=3600):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        logger.debug(f"Initialized cache in {cache_dir} with TTL {ttl} seconds")
    
    def get(self, key):
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        cache_file = self._get_cache_file_path(key)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is expired
            if cache_data.get('expires_at', 0) < time.time():
                logger.debug(f"Cache expired for key: {key}")
                os.remove(cache_file)
                return None
            
            return cache_data.get('value')
            
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading cache file: {e}")
            return None
    
    def set(self, key, value):
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successful
        """
        cache_file = self._get_cache_file_path(key)
        
        try:
            cache_data = {
                'value': value,
                'created_at': time.time(),
                'expires_at': time.time() + self.ttl
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            return True
            
        except IOError as e:
            logger.error(f"Error writing cache file: {e}")
            return False
    
    def clear_expired(self):
        """
        Clear expired cache entries.
        
        Returns:
            Number of items cleared
        """
        count = 0
        
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.cache'):
                continue
            
            cache_file = os.path.join(self.cache_dir, filename)
            
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                if cache_data.get('expires_at', 0) < time.time():
                    os.remove(cache_file)
                    count += 1
                    
            except (json.JSONDecodeError, IOError):
                # Remove invalid cache files
                os.remove(cache_file)
                count += 1
        
        return count
    
    def clear_all(self):
        """
        Clear all cache entries.
        
        Returns:
            Number of items cleared
        """
        count = 0
        
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.cache'):
                continue
            
            cache_file = os.path.join(self.cache_dir, filename)
            
            try:
                os.remove(cache_file)
                count += 1
            except IOError:
                pass
        
        return count
    
    def _get_cache_file_path(self, key):
        """
        Get the file path for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            File path
        """
        safe_key = str(key).replace('/', '_').replace('\\', '_')
        return os.path.join(self.cache_dir, f"{safe_key}.cache")