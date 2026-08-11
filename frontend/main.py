"""
Git Reverse Frontend Directory Wrapper
Delegates execution to the root main.py script.
"""
import os
import sys

# Change working directory to parent root
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
os.chdir(root_dir)

# Execute root main.py
if __name__ == "__main__":
    import main
    main.main()
