try:
    import multipart
    print("python-multipart is installed.")
except ImportError:
    print("WARNING: python-multipart is NOT installed. UploadFile requires it.")
    import sys
    sys.exit(1)
