import sys
import os

# Adds the root project directory to the path so Vercel can locate 'app.py' flawlessly.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the actual Flask 'app' instance from 'app.py' seamlessly.
from app import app
