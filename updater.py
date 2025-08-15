# updater.py
# This module handles checking for updates and applying them for the VRChat Uploader application.

import os, sys, json, hashlib, tempfile, time, subprocess
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import tkinter as tk
from tkinter import messagebox

APP_VERSION = "1.1.0"
UPDATE_MANIFEST_URL = "https://your.host/vrchat-uploader/manifest.json"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _ver_tuple(v):
    return tuple(int(p) for p in v.split("."))

def check_for_update(current_version: str, manifest_url: str, parent=None):
    """Return (is_update_available, manifest_dict or None, error_str or None)."""
    try:
        req = Request(manifest_url, headers={"User-Agent": "VRChatUploader/UpdateCheck"})
        with urlopen(req, timeout=8) as r:
            manifest = json.load(r)
    except (URLError, HTTPError, TimeoutError, ValueError) as e:
        return False, None, f"Update check failed: {e}"

    remote_ver = manifest.get("version")
    if not remote_ver:
        return False, None, "Manifest missing 'version'."

    if _ver_tuple(remote_ver) > _ver_tuple(current_version):
        return True, manifest, None
    return False, manifest, None

def prompt_and_update(manifest: dict, parent=None):
    url = manifest["url"]
    sha = manifest.get("sha256")
    notes = manifest.get("notes", "")
    if not messagebox.askyesno(
        "Update Available",
        f"A new version is available.\n\n{notes}\n\nDownload and install now?"
    ):
        return False

    tmp_dir = tempfile.gettempdir()
    new_exe = os.path.join(tmp_dir, os.path.basename(url))
    try:
        req = Request(url, headers={"User-Agent": "VRChatUploader/UpdateDownload"})
        with urlopen(req, timeout=60) as r, open(new_exe, "wb") as f:
            while True:
                chunk = r.read(1024*64)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        messagebox.showerror("Update", f"Download failed:\n{e}")
        return False

    if sha:
        actual = _sha256(new_exe)
        if actual.lower() != sha.lower():
            messagebox.showerror("Update", "Downloaded file hash mismatch.\nAborting.")
            try: os.remove(new_exe)
            except OSError: pass
            return False

    current_exe = sys.executable  
    target = current_exe
    backup = current_exe + ".bak"
    swap_bat = os.path.join(tmp_dir, "vrchat_uploader_swap.bat")

    bat = rf"""@echo off
    setlocal
    REM wait for app to close
    ping 127.0.0.1 -n 2 >nul
    :loop
    tasklist /FI "IMAGENAME eq {os.path.basename(current_exe)}" | find /I "{os.path.basename(current_exe)}" >nul
    if %errorlevel%==0 (
      timeout /T 1 >nul
      goto loop
    )
    REM swap
    del "{backup}" >nul 2>&1
    rename "{target}" "{os.path.basename(backup)}"
    copy /Y "{new_exe}" "{target}" >nul
    if %errorlevel% neq 0 (
      echo Failed to copy new exe.
      exit /b 1
    )
    del "{new_exe}" >nul 2>&1
    start "" "{target}"
    exit /b 0
    """
    with open(swap_bat, "w", encoding="utf-8") as f:
        f.write(bat)

    try:
        subprocess.Popen([swap_bat], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        subprocess.Popen(['cmd', '/c', swap_bat])
    return True
