import sys
import os

# Add project root to sys.path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import db  # Import your SQLAlchemy db instance

target_metadata = db.metadata
