"""Make the cbom_db package importable when running pytest from db/."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
