# config.py
import os
import sys

# Detect if running as a compiled executable
if getattr(sys, 'frozen', False):
    # If it's an .exe, the base dir is where the .exe is located
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # If running normally via PyCharm, use the script location
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_FILE = os.path.join(DATA_DIR, "passwords.db")
OLD_DATA_FILE = "data.json"