import os
import sys
from pathlib import Path

# Add project root to sys.path and PYTHONPATH so 'backend' package is always resolvable
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.environ["PYTHONPATH"] = str(project_root) + os.pathsep + os.environ.get("PYTHONPATH", "")

from backend.app.core.encoding import setup_utf8_environment
setup_utf8_environment()

import uvicorn

if __name__ == "__main__":
    # Start the server on localhost:8000 using the proper package import string
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
