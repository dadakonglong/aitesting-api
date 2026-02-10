import sys
import os

# Add local directory to path 
sys.path.append(os.getcwd())

print("Attempting to import main...")
try:
    import main
    print("Successfully imported main!")
    
    # Check if data_import_service has db_path
    if hasattr(main.data_import_service, 'db_path') and main.data_import_service.db_path:
        print(f"DataImportService has DB_PATH: {main.data_import_service.db_path}")
    else:
        print("WARNING: DataImportService missing DB_PATH")

    # Check VectorService enabled status
    if hasattr(main.vector_service, 'enabled'):
         print(f"VectorService enabled: {main.vector_service.enabled}")
    
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Exception during import: {e}")
