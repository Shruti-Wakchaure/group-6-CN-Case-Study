"""Pytest configuration for workspace root."""

import sys
from pathlib import Path

cloudscale_dir = Path(__file__).resolve().parent / "cloudscale"
if str(cloudscale_dir) not in sys.path:
    sys.path.insert(0, str(cloudscale_dir))
