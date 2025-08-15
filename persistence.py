# persistence.py
# This module handles loading and saving upload counts and history.

import os
import json

def load_upload_count(upload_count_file):
    if os.path.exists(upload_count_file):
        try:
            with open(upload_count_file, 'r') as f:
                data = json.load(f)
                return data.get("count", 0)
        except (IOError, json.JSONDecodeError):
            print(f"Error reading {upload_count_file}, starting count at 0.")
    return 0

def save_upload_count(upload_count_file, count):
    try:
        with open(upload_count_file, 'w') as f:
            json.dump({"count": count}, f)
    except IOError as e:
        print(f"Error saving upload count file: {e}")

def load_upload_history(upload_history_file):
    if os.path.exists(upload_history_file):
        try:
            with open(upload_history_file, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            print(f"Error reading {upload_history_file}, starting with empty history.")
    return {}

def save_upload_history(upload_history_file, history):
    try:
        with open(upload_history_file, 'w') as f:
            json.dump(history, f, indent=4)
    except IOError as e:
        print(f"Error saving upload history file: {e}")