import sys
import os

# Add local directory to path 
sys.path.append(os.getcwd())

print("Attempting to import main_sqlite...")
try:
    import main_sqlite
    print("Successfully imported main_sqlite!")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Exception during import: {e}")
