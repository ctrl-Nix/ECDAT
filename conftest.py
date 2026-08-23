"""Put the repo root on sys.path so `import backend.db...` works under pytest."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
