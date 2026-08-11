"""
Git Reverse Frontend Directory Wrapper
Delegates execution to the root main.py script with explicit absolute path resolution.
"""
from pathlib import Path
import os
import sys

# Resolve root directory using Path
ROOT_DIR = str(Path(__file__).resolve().parent.parent)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.chdir(ROOT_DIR)

# Execute root main.py
if __name__ == "__main__":
    import main
    main.main()
