#!/usr/bin/env python
# tests/test_independent_cache_manager.py

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

# Import directly from external_api without dependencies
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/external_api")))
from cache_manager import CacheManager

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

if __name__ == '__main__':
    unittest.main()
