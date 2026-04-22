import sys
import os
from pathlib import Path

# Add the 'backend' directory to sys.path so that tests can import 
# modules like 'agents', 'db', 'config' directly.
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
