# tests/mocks/db_mock.py
from unittest.mock import MagicMock

# Tạo các mock object cho database
Session = MagicMock()
engine = MagicMock()
Base = MagicMock()

# Mock function cho get_db_session
def get_db_session():
    """Trả về một session giả để test."""
    mock_session = MagicMock()
    return mock_session

# Mock classes cho models
class SensorData:
    @staticmethod
    def create(session, **kwargs):
        return MagicMock()
    
    @staticmethod
    def get_latest(session):
        return None

class IrrigationEvent:
    @staticmethod
    def create(session, **kwargs):
        return MagicMock()
    
    @staticmethod
    def get_latest(session):
        return None
