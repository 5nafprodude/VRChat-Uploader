# uploader.py
# This module handles the file upload logic for the VRChat Uploader application.

import os
import requests
from .utils import log_error, extract_vrchat_id
from .constants import WEBHOOK_URL, DISCORD_MAX_FILE_SIZE

def is_duplicate(filepath, upload_history):
    """Checks if the file has already been uploaded (by hash or name)."""
    filename = os.path.basename(filepath)
    return filename in upload_history

def is_too_large(filepath):
    """Checks if the file is larger than Discord's max file size."""
    return os.path.getsize(filepath) > DISCORD_MAX_FILE_SIZE

def send_to_webhook(filepath, vrc_id):
    """Sends the VRChat asset URL to the Discord webhook."""
    url = f"https://vrchat.com/home/avatar/{vrc_id}"
    payload = {"content": f"New VRChat asset detected: {url}"}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        log_error(f"Failed to send to webhook: {e}")
        return False

def process_upload(filepath, upload_history):
    """Processes a single file for upload, returns status string."""
    vrc_id = extract_vrchat_id(filepath)
    if not vrc_id:
        return "Failed (No VRChat ID)"
    if is_duplicate(filepath, upload_history):
        return "Skipped (Duplicate)"
    if is_too_large(filepath):
        return "Failed (Too Large)"
    success = send_to_webhook(filepath, vrc_id)
    if success:
        upload_history[os.path.basename(filepath)] = vrc_id
        return "Success"
    else:
        return "Failed (Webhook Error)"