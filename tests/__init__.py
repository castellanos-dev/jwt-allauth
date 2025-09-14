import os
import sys
from pathlib import Path

# Ensure project root and tests directory are on sys.path
current_file_path = Path(__file__).resolve()
tests_dir = str(current_file_path.parent)
project_root = str(current_file_path.parent.parent)

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

# Ensure Django uses tests.settings unless already provided externally
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django

django.setup()
