import sys
import os

# Root directory of the repository
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(repo_root, "backend")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Extend app package search path to include backend/app
backend_app_dir = os.path.join(backend_dir, "app")
__path__ = [backend_app_dir]
