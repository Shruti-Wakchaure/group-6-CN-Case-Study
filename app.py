"""CloudScale root launcher.
Allows running `streamlit run app.py` directly from workspace root.
"""

import sys
from pathlib import Path

# Add cloudscale directory to Python path
cloudscale_dir = Path(__file__).resolve().parent / "cloudscale"
if str(cloudscale_dir) not in sys.path:
    sys.path.insert(0, str(cloudscale_dir))

# Execute the application
import app
