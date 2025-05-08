#!/usr/bin/env python
# tests/test_cache_manager.py

import os
import sys
import unittest
import tempfile
import shutil
import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch database và các module khác trước khi import
sys.modules['src.database'] = MagicMock()
sys.modules['src.database.db_client'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['firebase_admin'] = MagicMock()

# Patch config
from tests.mocks.config_mock import *
sys.modules['config.config'] = sys.modules[__name__]

# Import modules cần test
from src.external_api.cache_manager import CacheManager
from src.core.cache_manager import APICacheManager

class TestCacheManager(unittest.TestCase):
    """Test cases for the base CacheManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for cache
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(self.temp_dir, ttl=1)  # 1 second TTL for faster testing
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test that cache manager initializes correctly."""
        self.assertIsNotNone(self.cache_manager)
        self.assertEqual(self.cache_manager.cache_dir, self.temp_dir)
        self.assertEqual(self.cache_manager.ttl, 1)
        self.assertTrue(os.path.exists(self.temp_dir))
    
    def test_set_get(self):
        """Test setting and getting cache values."""
        # Test simple value
        key = "test_key"
        value = "test_value"
        
        # Set the value
        result = self.cache_manager.set(key, value)
        self.assertTrue(result)
        
        # Check that the file was created
        cache_file = self.cache_manager._get_cache_file_path(key)
        self.assertTrue(os.path.exists(cache_file))
        
        # Get the value
        cached_value = self.cache_manager.get(key)
        self.assertEqual(cached_value, value)
        
        # Test with complex value (dict)
        complex_key = "complex_key"
        complex_value = {"name": "test", "value": 123}
        
        # Set the value
        result = self.cache_manager.set(complex_key, complex_value)
        self.assertTrue(result)
        
        # Get the value
        cached_complex = self.cache_manager.get(complex_key)
        self.assertEqual(cached_complex, complex_value)
    
    def test_cache_expiration(self):
        """Test that cache entries expire correctly."""
        key = "expiring_key"
        value = "expiring_value"
        
        # Set the value
        self.cache_manager.set(key, value)
        
        # Verify it's there
        self.assertEqual(self.cache_manager.get(key), value)
        
        # Wait for it to expire
        time.sleep(1.5)  # Sleep a bit longer than TTL
        
        # Verify it's gone
        self.assertIsNone(self.cache_manager.get(key))
    
    def test_clear_expired(self):
        """Test clearing expired entries."""
        # Set multiple entries
        self.cache_manager.set("key1", "value1")
        self.cache_manager.set("key2", "value2")
        
        # Wait for entries to expire
        time.sleep(1.5)
        
        # Clear expired entries
        count = self.cache_manager.clear_expired()
        self.assertEqual(count, 2)
        
        # Set a new entry
        self.cache_manager.set("key3", "value3")
        
        # Clear again, should find no expired entries
        count = self.cache_manager.clear_expired()
        self.assertEqual(count, 0)
        
        # Verify the new entry is still there
        self.assertEqual(self.cache_manager.get("key3"), "value3")
    
    def test_clear_all(self):
        """Test clearing all cache entries."""
        # Set multiple entries
        self.cache_manager.set("key1", "value1")
        self.cache_manager.set("key2", "value2")
        self.cache_manager.set("key3", "value3")
        
        # Clear all entries
        count = self.cache_manager.clear_all()
        self.assertEqual(count, 3)
        
        # Verify they're all gone
        self.assertIsNone(self.cache_manager.get("key1"))
        self.assertIsNone(self.cache_manager.get("key2"))
        self.assertIsNone(self.cache_manager.get("key3"))
    
    def test_invalid_cache_file(self):
        """Test handling of invalid cache files."""
        key = "invalid_key"
        cache_file = self.cache_manager._get_cache_file_path(key)
        
        # Create an invalid JSON file
        with open(cache_file, "w") as f:
            f.write("This is not valid JSON")
        
        # Try to get the value
        value = self.cache_manager.get(key)
        self.assertIsNone(value)


class TestAPICacheManager(unittest.TestCase):
    """Test cases for the APICacheManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Patch config
        self.config_patcher = patch('src.core.cache_manager.CACHE_STORAGE_PATH', CACHE_STORAGE_PATH)
        self.mock_config = self.config_patcher.start()
        
        # Patch CacheManager
        self.cache_patcher = patch('src.core.cache_manager.CacheManager')
        self.mock_cache_class = self.cache_patcher.start()
        
        # Create mock instances for each cache type
        self.mock_short_cache = MagicMock()
        self.mock_medium_cache = MagicMock()
        self.mock_long_cache = MagicMock()
        
        # Configure the mock CacheManager to return our mock caches
        self.mock_cache_class.side_effect = [
            self.mock_short_cache,
            self.mock_medium_cache,
            self.mock_long_cache
        ]
        
        # Create the API cache manager
        self.api_cache = APICacheManager()
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.config_patcher.stop()
        self.cache_patcher.stop()
    
    def test_initialization(self):
        """Test that API cache manager initializes correctly."""
        self.assertIsNotNone(self.api_cache)
        self.assertEqual(self.api_cache.short_cache, self.mock_short_cache)
        self.assertEqual(self.api_cache.medium_cache, self.mock_medium_cache)
        self.assertEqual(self.api_cache.long_cache, self.mock_long_cache)
        self.assertEqual(self.api_cache.hit_count, 0)
        self.assertEqual(self.api_cache.miss_count, 0)
    
    def test_get_cache_hit(self):
        """Test get method with cache hit."""
        # Configure mock to return a value
        self.mock_medium_cache.get.return_value = "cached_value"
        
        # Get the value
        value = self.api_cache.get("test_key")
        
        # Verify result
        self.assertEqual(value, "cached_value")
        self.assertEqual(self.api_cache.hit_count, 1)
        self.assertEqual(self.api_cache.miss_count, 0)
        
        # Verify the correct cache was queried
        self.mock_medium_cache.get.assert_called_once_with("test_key")
    
    def test_get_cache_miss(self):
        """Test get method with cache miss."""
        # Configure mock to return None
        self.mock_medium_cache.get.return_value = None
        
        # Get the value
        value = self.api_cache.get("test_key")
        
        # Verify result
        self.assertIsNone(value)
        self.assertEqual(self.api_cache.hit_count, 0)
        self.assertEqual(self.api_cache.miss_count, 1)
        
        # Verify the correct cache was queried
        self.mock_medium_cache.get.assert_called_once_with("test_key")
    
    def test_get_with_cache_type(self):
        """Test get method with different cache types."""
        # Short cache
        self.api_cache.get("short_key", cache_type="short")
        self.mock_short_cache.get.assert_called_once_with("short_key")
        
        # Medium cache
        self.api_cache.get("medium_key", cache_type="medium")
        self.mock_medium_cache.get.assert_called_once_with("medium_key")
        
        # Long cache
        self.api_cache.get("long_key", cache_type="long")
        self.mock_long_cache.get.assert_called_once_with("long_key")
        
        # Unknown cache type (should default to medium)
        self.api_cache.get("unknown_key", cache_type="unknown")
        self.mock_medium_cache.get.assert_called_with("unknown_key")
    
    def test_set(self):
        """Test set method."""
        # Set a value
        self.api_cache.set("test_key", "test_value")
        
        # Verify the correct cache was used
        self.mock_medium_cache.set.assert_called_once_with("test_key", "test_value")
        
        # Set with different cache types
        self.api_cache.set("short_key", "short_value", cache_type="short")
        self.mock_short_cache.set.assert_called_once_with("short_key", "short_value")
        
        self.api_cache.set("long_key", "long_value", cache_type="long")
        self.mock_long_cache.set.assert_called_once_with("long_key", "long_value")
    
    def test_perform_maintenance(self):
        """Test perform_maintenance method."""
        # Configure mocks to return counts
        self.mock_short_cache.clear_expired.return_value = 3
        self.mock_medium_cache.clear_expired.return_value = 2
        self.mock_long_cache.clear_expired.return_value = 1
        
        # Perform maintenance
        count = self.api_cache.perform_maintenance()
        
        # Verify result
        self.assertEqual(count, 6)
        
        # Verify all caches were cleared
        self.mock_short_cache.clear_expired.assert_called_once()
        self.mock_medium_cache.clear_expired.assert_called_once()
        self.mock_long_cache.clear_expired.assert_called_once()
        
        # Verify last maintenance time was updated
        self.assertIsNotNone(self.api_cache.last_maintenance)
        
        # Test skipping maintenance if run recently
        self.api_cache.last_maintenance = datetime.now()
        count = self.api_cache.perform_maintenance()
        self.assertEqual(count, 0)
        
        # Test forcing maintenance
        count = self.api_cache.perform_maintenance(force=True)
        self.assertEqual(count, 6)
    
    def test_get_stats(self):
        """Test get_stats method."""
        # Set hit/miss counts
        self.api_cache.hit_count = 10
        self.api_cache.miss_count = 5
        
        # Get stats
        stats = self.api_cache.get_stats()
        
        # Verify result
        self.assertEqual(stats['hit_count'], 10)
        self.assertEqual(stats['miss_count'], 5)
        self.assertEqual(stats['hit_rate'], 10/15)
        self.assertIsNotNone(stats['last_maintenance'])
    
    def test_clear_cache(self):
        """Test clear_cache method."""
        # Configure mocks to return counts
        self.mock_short_cache.clear_all.return_value = 3
        self.mock_medium_cache.clear_all.return_value = 2
        self.mock_long_cache.clear_all.return_value = 1
        
        # Clear all caches
        count = self.api_cache.clear_cache()
        
        # Verify result
        self.assertEqual(count, 6)
        
        # Verify all caches were cleared
        self.mock_short_cache.clear_all.assert_called_once()
        self.mock_medium_cache.clear_all.assert_called_once()
        self.mock_long_cache.clear_all.assert_called_once()
        
        # Test clearing specific cache type
        self.mock_short_cache.clear_all.reset_mock()
        self.mock_medium_cache.clear_all.reset_mock()
        self.mock_long_cache.clear_all.reset_mock()
        
        count = self.api_cache.clear_cache(cache_type="short")
        
        # Verify only short cache was cleared
        self.assertEqual(count, 3)
        self.mock_short_cache.clear_all.assert_called_once()
        self.mock_medium_cache.clear_all.assert_not_called()
        self.mock_long_cache.clear_all.assert_not_called()


if __name__ == '__main__':
    unittest.main()
