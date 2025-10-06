# Relative Path: oracle_mcp\__main__.py
"""
This module allows the package to be run directly using:
python -m oracle_mcp
"""

import sys
import os

from main import start_oracle_mcp

# Add the parent directory to sys.path to allow imports from main.py
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

if __name__ == "__main__":
    start_oracle_mcp()

# End of file