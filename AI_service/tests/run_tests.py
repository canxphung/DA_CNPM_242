#!/usr/bin/env python
# tests/run_tests.py

import unittest
import sys
import os
from unittest.mock import MagicMock

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch các module gây lỗi
sys.modules['redis'] = MagicMock()
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['firebase_admin.db'] = MagicMock()

# Import và patch openai + backoff
from tests.mocks.openai_mock import backoff, openai
sys.modules['backoff'] = backoff
sys.modules['openai'] = openai

# Patch database
sys.modules['src.database'] = MagicMock()
sys.modules['src.database.db_client'] = MagicMock()
sys.modules['src.database.sensor_data'] = MagicMock()
sys.modules['src.database.irrigation_events'] = MagicMock()

# Import models_storage mock
from tests.mocks.models_storage_mock import ModelMetadata

# Patch models_storage và model_storage
sys.modules['src.database.models_storage'] = MagicMock()
sys.modules['src.database.models_storage'].ModelMetadata = ModelMetadata
sys.modules['src.database.model_storage'] = MagicMock()
sys.modules['src.database.model_storage'].ModelMetadata = ModelMetadata

# Patch config
from tests.mocks.config_mock import *
sys.modules['config.config'] = sys.modules[__name__]  # Use this module as the config

if __name__ == "__main__":
    # Tạo test suite từ các test độc lập
    independent_tests = [
        'test_independent_cache_manager',
        'test_openai_client',
        'test_independent_model_registry',
        'test_independent_resource_optimizer',
        'test_independent_decision_engine',
        'test_independent_greenhouse_ai_service',
        'test_api_connectivity'
    ]

    loader = unittest.TestLoader()
    independent_suite = unittest.TestSuite()

    # Thêm các test độc lập
    for test_module in independent_tests:
        try:
            module = __import__(test_module)
            independent_suite.addTests(loader.loadTestsFromModule(module))
            print(f"Loaded independent test module: {test_module}")
        except (ImportError, AttributeError) as e:
            print(f"Could not load {test_module}: {e}")
    
    # Chạy các test độc lập trước
    print("\n==== Running Independent Tests ====\n")
    result1 = unittest.TextTestRunner(verbosity=2).run(independent_suite)
    
    # Chạy các test còn lại nếu các test độc lập thành công
    if result1.wasSuccessful():
        print("\n==== Running Standard Tests ====\n")
        standard_suite = loader.discover('tests', pattern='test_*.py')
        result2 = unittest.TextTestRunner(verbosity=2).run(standard_suite)
        sys.exit(not (result1.wasSuccessful() and result2.wasSuccessful()))
    else:
        print("\nIndependent tests failed, not running standard tests.")
        sys.exit(1)
