"""
CORS settings tests.
"""
from app.core.config import settings


def test_cors_allows_loopback_dev_frontend():
    assert "http://127.0.0.1:5173" in settings.CORS_ORIGINS
