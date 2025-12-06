"""
PythonAnywhere WSGI Configuration Template

Copy this content to your WSGI configuration file in PythonAnywhere Web tab.
Replace YOUR_USERNAME with your actual PythonAnywhere username.
"""

import sys
import os

# ============================================
# CONFIGURATION - UPDATE THESE PATHS
# ============================================
USERNAME = 'YOUR_USERNAME'  # Replace with your PythonAnywhere username
PROJECT_NAME = 'Portfolio-Website'  # Your project folder name

# ============================================
# DO NOT MODIFY BELOW THIS LINE
# ============================================

# Add your project directory to the sys.path
project_home = f'/home/{USERNAME}/{PROJECT_NAME}'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Activate virtual environment
activate_this = f'/home/{USERNAME}/{PROJECT_NAME}/venv/bin/activate_this.py'
try:
    with open(activate_this) as file_:
        exec(file_.read(), dict(__file__=activate_this))
except FileNotFoundError:
    # If activate_this.py doesn't exist, try alternative method
    import site
    site.addsitedir(f'/home/{USERNAME}/{PROJECT_NAME}/venv/lib/python3.10/site-packages')

# Load environment variables from .env file
from dotenv import load_dotenv
project_folder = os.path.expanduser(project_home)
load_dotenv(os.path.join(project_folder, '.env'))

# Import Flask app
from app import app as application

# Optional: Set up logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info('WSGI application started successfully')
