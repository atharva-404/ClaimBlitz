"""Pytest configuration for backend tests."""

import os
from pathlib import Path

# Add the parent directory to the path so we can import app modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture(scope="session")
def test_app():
    """Create a test app instance."""
    os.environ['TESTING'] = 'true'
    from app.main import app
    return app
