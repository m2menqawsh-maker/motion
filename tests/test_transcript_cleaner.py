import os
import sys
import pytest

# Add scripts dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

from transcript_cleaner import get_transcript_path

def test_get_transcript_path():
    path = get_transcript_path("test_session", custom_path="/custom/path")
    assert path == "/custom/path"
