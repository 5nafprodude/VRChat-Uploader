# utils.py
# This module contains utility functions for logging errors and extracting VRChat IDs.

import os
import sys
import re
from pathlib import Path

def log_error(message):
    """Logs error messages to a file in the app data directory."""
    appdata_path = get_appdata_path()
    log_path = os.path.join(appdata_path, "error.log")
    try:
        os.makedirs(appdata_path, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass

def get_appdata_path():
    """Returns the correct application data directory for the current OS."""
    if sys.platform == "win32":
        path = os.path.join(os.getenv("APPDATA"), "VRChatUploader")
    elif sys.platform == "darwin":
        path = os.path.join(os.path.expanduser("~/Library/Application Support"), "VRChatUploader")
    else:
        path = os.path.join(os.path.expanduser("~/.vrchat_uploader"))
    return path

def extract_vrchat_id(filepath):
    """Extracts the VRChat avatar ID from a file path or file name."""
    AVATAR_RE = re.compile(r"(avtr_[0-9a-fA-F-]+)", re.IGNORECASE)
    match = AVATAR_RE.search(str(filepath))
    if match:
        return match.group(1)
    return None