"""Pytest configuration to ensure core package is on python path."""

import sys
from pathlib import Path

# Add cloudscale directory to path
cloudscale_dir = Path(__file__).resolve().parent
if str(cloudscale_dir) not in sys.path:
    sys.path.insert(0, str(cloudscale_dir))
