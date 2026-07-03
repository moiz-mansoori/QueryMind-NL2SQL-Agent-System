import sys
import os
from pathlib import Path

# Add the 'backend' directory to sys.path so that tests can import 
# modules like 'agents', 'db', 'config' directly.
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pytest

@pytest.fixture(autouse=True)
def reset_global_caches():
    """Reset global cache singletons in agents.nodes.utils before each test to prevent test state leakage."""
    try:
        import agents.nodes.utils
        agents.nodes.utils._embed_model = None
        agents.nodes.utils._groq_client = None
    except ImportError:
        pass
