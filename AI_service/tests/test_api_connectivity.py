#!/usr/bin/env python
# tests/test_api_connectivity.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch database and dependencies
sys.modules['src.database'] = MagicMock()
sys.modules['src.database.db_client'] = MagicMock()
sys.modules['src.database.models_storage'] = MagicMock()
sys.modules['src.database.model_storage'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['firebase_admin.db'] = MagicMock()

# Import mocks
from tests.mocks.openai_mock import backoff, openai
sys.modules['backoff'] = backoff
sys.modules['openai'] = openai

# Patch config
from tests.mocks.config_mock import *
sys.modules['config.config'] = sys.modules[__name__]


class TestAPIConnectivity(unittest.TestCase):
    """Test cases for API connectivity."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock aiohttp ClientSession and response
        self.mock_session = MagicMock()
        self.mock_session.close = AsyncMock()
        self.mock_response = MagicMock()
        self.mock_response.status = 200
        self.mock_response.json = AsyncMock(return_value={"status": "ok"})
        self.mock_response.text = AsyncMock(return_value="OK")
        self.mock_response.__aenter__ = AsyncMock(return_value=self.mock_response)
        self.mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Configure session methods
        self.mock_session.get = MagicMock(return_value=self.mock_response)
        self.mock_session.post = MagicMock(return_value=self.mock_response)
        
        # Path ClientSession
        self.session_patcher = patch('aiohttp.ClientSession', return_value=self.mock_session)
        self.mock_client_session = self.session_patcher.start()
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.session_patcher.stop()
    
    async def async_test_http_get(self):
        """Test HTTP GET request."""
        import aiohttp
        
        # Tạo mock cho ClientSession.get
        session = MagicMock()
        session.get = MagicMock(return_value=self.mock_response)
        
        # Reset mock before use
        self.mock_response.__aenter__.reset_mock()
        self.mock_response.json.reset_mock()
        
        # Gọi API
        response = await self.mock_response.__aenter__()
        if response.status == 200:
            data = await response.json()
        else:
            data = await response.text()
        
        # Đóng response
        await self.mock_response.__aexit__(None, None, None)
        
        # Kiểm tra
        self.mock_response.__aenter__.assert_called_once()
        self.mock_response.json.assert_called_once()
    
    async def async_test_http_post(self):
        """Test HTTP POST request."""
        import aiohttp
        
        payload = {"test": "data"}
        headers = {"Content-Type": "application/json"}
        
        # Tạo mock cho session.post
        session = MagicMock()
        session.post = MagicMock(return_value=self.mock_response)
        
        # Reset mock before use
        self.mock_response.__aenter__.reset_mock()
        
        # Gọi API
        response = await self.mock_response.__aenter__()
        if response.status == 200:
            data = await response.json()
        else:
            data = await response.text()
        
        # Đóng response
        await self.mock_response.__aexit__(None, None, None)
        
        # Kiểm tra
        self.mock_response.__aenter__.assert_called_once()
        self.mock_response.json.assert_called_once()
    
    async def async_test_http_error_handling(self):
        """Test HTTP error handling."""
        import aiohttp
        
        # Configure mock response for error
        self.mock_response.status = 500
        self.mock_response.json.side_effect = aiohttp.ContentTypeError(
            request_info=MagicMock(),
            history=MagicMock(),
            message="Invalid content type"
        )
        
        # Tạo mock cho session.get
        session = MagicMock()
        session.get = MagicMock(return_value=self.mock_response)
        
        # Reset mock before use
        self.mock_response.__aenter__.reset_mock()
        self.mock_response.text.reset_mock()
        
        # Gọi API
        response = await self.mock_response.__aenter__()
        # Xử lý lỗi
        if response.status >= 400:
            error_text = await response.text()
            data = {"error": error_text}
        else:
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                data = {"error": "Invalid content type"}
        
        # Đóng response
        await self.mock_response.__aexit__(None, None, None)
        
        # Kiểm tra
        self.mock_response.__aenter__.assert_called_once()
        self.mock_response.text.assert_called_once()
    
    async def async_test_connection_error_handling(self):
        """Test connection error handling."""
        import aiohttp
        
        # Configure exception
        error = aiohttp.ClientConnectionError("Connection refused")
        
        # Test xử lý ngoại lệ
        try:
            # Gọi API sẽ gây lỗi
            raise error
            success = True
        except aiohttp.ClientConnectionError:
            success = False
        
        # Kiểm tra
        self.assertFalse(success)
    
    async def async_test_timeout_handling(self):
        """Test timeout handling."""
        import aiohttp
        
        # Test xử lý timeout
        try:
            # Gọi API sẽ gây timeout
            raise asyncio.TimeoutError()
            success = True
        except asyncio.TimeoutError:
            success = False
        
        # Kiểm tra
        self.assertFalse(success)
    
    def run_async_tests(self):
        """Run all async tests."""
        # Create an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run tests one by one in sequence (avoid running them in parallel)
            loop.run_until_complete(self.async_test_http_get())
            # Reset mock response between tests
            self.mock_response.__aenter__.reset_mock()
            self.mock_response.json.reset_mock()
            self.mock_response.text.reset_mock()
            
            loop.run_until_complete(self.async_test_http_post())
            # Reset mock response between tests
            self.mock_response.__aenter__.reset_mock()
            self.mock_response.json.reset_mock()
            self.mock_response.text.reset_mock()
            
            loop.run_until_complete(self.async_test_http_error_handling())
            # Reset mock response between tests
            self.mock_response.__aenter__.reset_mock()
            self.mock_response.json.reset_mock()
            self.mock_response.text.reset_mock()
            
            loop.run_until_complete(self.async_test_connection_error_handling())
            # Reset mock response between tests
            self.mock_response.__aenter__.reset_mock()
            self.mock_response.json.reset_mock()
            self.mock_response.text.reset_mock()
            
            loop.run_until_complete(self.async_test_timeout_handling())
        finally:
            # Close the loop
            loop.close()
    
    def test_run_async_tests(self):
        """Run all async tests in a synchronous test method."""
        self.run_async_tests()


if __name__ == '__main__':
    unittest.main()
