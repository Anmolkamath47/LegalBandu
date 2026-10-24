import sys
import os

# Automatically add 'backend' directory to sys.path so 'import app.main' works
# from root regardless of whether Root Directory was set in Render
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
