"""
Bootstraps Django settings so this Streamlit app can import and use the
same models, forms, and business logic as the Django project — no
duplicated code, same database, same validation rules.

Must be imported FIRST, before any `from apolice...` import, in every
Streamlit page.
"""
import os
import sys
from pathlib import Path

import django

# streamlit_app/ sits next to manage.py -- add the project root to
# sys.path so `import config.settings` and `import apolice` resolve the
# same way they do when Django itself runs.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()