# tests/mocks/openai_mock.py
"""
Mock for OpenAI and backoff modules
"""
from unittest.mock import MagicMock

# Create a mock for backoff decorator
def on_exception(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

# Mock backoff module
backoff = MagicMock()
backoff.on_exception = on_exception

# Mock OpenAI modules and classes
class ChatCompletion:
    @staticmethod
    def create(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Mock AI response"
                )
            )
        ]
        return mock_response

class Error(Exception):
    """Base class for OpenAI errors"""
    pass

class RateLimitError(Error):
    """Rate limit error"""
    pass
    
class APIError(Error):
    """API error"""
    pass

class ServiceUnavailableError(Error):
    """Service unavailable error"""
    pass

# Create the OpenAI mock
openai = MagicMock()
openai.ChatCompletion = ChatCompletion
openai.error = MagicMock()
openai.error.RateLimitError = RateLimitError
openai.error.APIError = APIError
openai.error.ServiceUnavailableError = ServiceUnavailableError
