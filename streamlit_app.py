"""
IntelliPulse — Production Entry Point for Streamlit Community Cloud.

This root entry point delegates directly to the primary application module
(app/main.py) while ensuring the project root is properly configured in sys.path
for cross-environment portability (local macOS, Linux containers, Streamlit Cloud).
"""

import sys
from pathlib import Path

# Resolve project root and register with sys.path before any local imports
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Run main application
if __name__ == "__main__":
    import runpy
    runpy.run_path(str(PROJECT_ROOT / "app" / "main.py"), run_name="__main__")
else:
    # When imported by Streamlit runner
    import app.main  # noqa: F401
