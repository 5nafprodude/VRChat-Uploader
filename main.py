# main.py
# This is the main entry point for the VRChat Uploader application.

import tkinter as tk
from tkinter import messagebox, filedialog
import re
import threading
import queue
from pathlib import Path
import os
import sys
import json
import time
from datetime import datetime
import logging
import requests

try:
    from app_ui import setup_ui
except ImportError:
    from files.app_ui import setup_ui

try:
    from constants import WEBHOOK_URL, DISCORD_MAX_FILE_SIZE, MAX_RETRIES, AVATAR_RE
except ImportError:
    from files.constants import WEBHOOK_URL, DISCORD_MAX_FILE_SIZE, MAX_RETRIES, AVATAR_RE

try:
    from updater import APP_VERSION, UPDATE_MANIFEST_URL, check_for_update, prompt_and_update
except ImportError:
    from files.updater import APP_VERSION, UPDATE_MANIFEST_URL, check_for_update, prompt_and_update
try:
    import tkinterdnd2 as tkdnd
    HAS_DND = True
    class App(tkdnd.TkinterDnD.Tk):
        pass
except Exception:
    print("WARNING: tkinterdnd2 not found. Drag-and-drop will be disabled.")
    HAS_DND = False
    class App(tk.Tk):
        pass

def resource_path(relative_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relative_path)

def set_appusermodel_id(aumid: str = "Naf.VRChatUploader") -> None:
    try:
        import ctypes  
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(aumid)
    except Exception:
        pass

def get_appdata_path():
    if sys.platform == "win32":
        path = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'VRChatAvatarUploader')
    elif sys.platform == "darwin":
        path = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'VRChatAvatarUploader')
    else:
        path = os.path.join(os.path.expanduser('~'), '.local', 'share', 'VRChatAvatarUploader')
    os.makedirs(path, exist_ok=True)
    return path

APPDATA_PATH = get_appdata_path()
UPLOAD_COUNT_FILE = os.path.join(APPDATA_PATH, "upload_count.json")
UPLOAD_HISTORY_FILE = os.path.join(APPDATA_PATH, "upload_history.json")

def do_update_check():
    try:
        from updater import check_for_update, prompt_and_update
        avail, manifest, err = check_for_update(APP_VERSION, UPDATE_MANIFEST_URL, parent=app)
        if err:
            print("[Update] Check error:", err)
            return
        if avail and manifest:
            did_launch_swapper = prompt_and_update(manifest, parent=app)
            if did_launch_swapper:
                app.destroy()
    except Exception as e:
        print("[Update] Unexpected error:", e)

update_available, manifest, err = check_for_update(APP_VERSION, UPDATE_MANIFEST_URL)
if err:
    print(err)  
elif update_available:
    if prompt_and_update(manifest):
        sys.exit(0)  

def show_status(label, message, kind="default"):
    colors = {
        "default": "#495057",
        "success": "#28a745",
        "error":   "#dc3545",
        "warning": "#ffc107",
        "info":    "#0d6efd",
    }
    label.config(text=message, foreground=colors.get(kind, colors["default"]))


class AvatarUploaderApp(App):
    LANGUAGES = {
        "English": {
            "title": "VRChat Avatar Uploader",
            "export": "Export History",
            "search": "Search...",
            "success": "Success!",
            "failed": "Failed",
        },
        "Español": {
            "title": "Subidor de Avatares VRChat",
            "export": "Exportar Historial",
            "search": "Buscar...",
            "success": "¡Éxito!",
            "failed": "Fallido",
        }
    }

    def __init__(self):
        print("Application started.")
        super().__init__()
        self.title("VRChat Avatar Uploader")
        self.geometry("900x720")
        self.minsize(780, 600)

        self.ui_queue = queue.Queue()
        self.upload_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.upload_thread = None
        self.is_upload_canceled = False
        self.file_id_map = {}  

        self.files_to_upload = 0
        self.files_uploaded_so_far = 0

        self.upload_count = self.load_upload_count()
        self.upload_history = self.load_upload_history()

        self.file_path_var = tk.StringVar(value="Drag and drop files here, or click Browse.")
        self.status_var = tk.StringVar(value="Ready")
        self.progress_bar_var = tk.DoubleVar(value=0)
        self.upload_count_var = tk.StringVar(value=f"Total Uploads: {self.upload_count}")
        self.upload_progress_var = tk.StringVar(value="")
        self.current_file_var = tk.StringVar(value="")

        (self.browse_button, self.upload_queue_tree,
         self.progress_bar, self.status_label, self.progress_label,
         self.current_file_label) = setup_ui(
            root=self,
            file_path_var=self.file_path_var,
            status_var=self.status_var,
            progress_bar_var=self.progress_bar_var,
            upload_count_var=self.upload_count_var,
            upload_progress_var=self.upload_progress_var,
            current_file_var=self.current_file_var,
            browse_callback=self.browse_file,
            has_dnd=HAS_DND,
        )

        self.export_button = tk.Button(self, text="Export History", command=self.export_history)
        self.export_button.pack(pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self, textvariable=self.search_var)
        self.search_entry.pack(pady=5)
        self.search_entry.bind("<KeyRelease>", self.filter_treeview)
        self.language_var = tk.StringVar(value="English")
        self.language_menu = tk.OptionMenu(self, self.language_var, *self.LANGUAGES.keys(), command=self.change_language)
        self.language_menu.pack(pady=5)

        if HAS_DND:
            self.drop_target_register(tkdnd.DND_FILES)
            self.dnd_bind('<<Drop>>', self.on_drop)

        self.after(100, self.check_ui_queue)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_upload_count(self):
        if os.path.exists(UPLOAD_COUNT_FILE):
            try:
                with open(UPLOAD_COUNT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("count", 0)
            except Exception:
                pass
        return 0

    def save_upload_count(self):
        try:
            with open(UPLOAD_COUNT_FILE, 'w', encoding='utf-8') as f:
                json.dump({"count": self.upload_count}, f)
            self.upload_count_var.set(f"Total Uploads: {self.upload_count}")
        except Exception as e:
            print(f"Error saving upload count: {e}")

    def load_upload_history(self):
        if os.path.exists(UPLOAD_HISTORY_FILE):
            try:
                with open(UPLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_upload_history(self):
        try:
            with open(UPLOAD_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.upload_history, f, indent=2)
        except Exception as e:
            print(f"Error saving upload history file: {e}")

    def change_language(self, lang):
        strings = self.LANGUAGES.get(lang, self.LANGUAGES["English"])
        self.title(strings["title"])
        self.export_button.config(text=strings["export"])
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, strings["search"])

    def check_ui_queue(self):
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                self.handle_ui_queue_message(msg)
        except queue.Empty:
            pass
        except Exception as e:
            logging.error(f"Error handling UI queue message: {e}")
        self.after(100, self.check_ui_queue)

    def on_drop(self, event):
        raw = event.data
        parts = [p.strip('{}') for p in raw.split(' ') if p]
        paths = [p for p in parts if os.path.isfile(p)]
        if paths:
            self.add_files_to_queue(paths)
        else:
            show_status(self.status_label, "Dropped items are not valid files.", "error")

    def browse_file(self):
        print("Opening file browser dialog...")
        paths = filedialog.askopenfilenames(
            title="Select VRChat Files",
            filetypes=[
                ("VRChat Files", "*.unity3d *.vrca *.vrcw *.prefab"),
                ("All Files", "*.*"),
            ],
        )
        if paths:
            print(f"Selected {len(paths)} files via browser.")
            self.add_files_to_queue(list(paths))
        else:
            print("File selection cancelled by user.")

    def add_files_to_queue(self, file_paths):
        added = 0
        for filepath in file_paths:
            if not filepath.lower().endswith((".unity3d", ".vrca", ".vrcw", ".prefab")):
                continue
            if filepath in self.file_id_map:
                continue
            item_id = self.upload_queue_tree.insert("", "end", values=(Path(filepath).name, "Pending", "0%"))
            self.file_id_map[filepath] = item_id
            self.upload_queue.put(filepath)
            added += 1

        self.files_to_upload = self.upload_queue.qsize()
        self.upload_progress_var.set(f"{self.files_uploaded_so_far}/{self.files_to_upload} uploaded")

        if added == 1:
            self.file_path_var.set(f"Selected: {os.path.basename(file_paths[0])}")
        elif added > 1:
            self.file_path_var.set(f"Selected: {added} new files added to queue")

        show_status(self.status_label, f"Added {added} files to the queue.")

        if added and (not self.upload_thread or not self.upload_thread.is_alive()):
            print("Starting new upload thread.")
            self.is_upload_canceled = False
            self.upload_thread = threading.Thread(target=self.upload_worker, daemon=True)
            self.upload_thread.start()

    def cancel_upload(self):
        if self.upload_thread and self.upload_thread.is_alive():
            print("Cancellation requested by user.")
            self.is_upload_canceled = True
            with self.upload_queue.mutex:
                self.upload_queue.queue.clear()
            self.ui_queue.put(("reset_ui", "Uploads canceled."))
        else:
            print("No active upload to cancel.")

    def export_history(self):
        import csv
        export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not export_path:
            return
        with open(export_path, "w", newline='', encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Avatar ID", "Upload Times"])
            for avatar_id, times in self.upload_history.items():
                writer.writerow([avatar_id, "; ".join(times)])
        messagebox.showinfo("Export", f"History exported to {export_path}")

    def upload_worker(self):
        while not self.is_upload_canceled and not self.upload_queue.empty():
            filepath = self.upload_queue.get()
            if self.is_upload_canceled:
                self.upload_queue.task_done()
                break

            filename = Path(filepath).name
            item_id = self.file_id_map.get(filepath)
            if item_id:
                self.ui_queue.put(("update_queue_status", item_id, "Uploading..."))
            self.ui_queue.put(("current_file", filename))

            m = AVATAR_RE.search(filename)
            if not m:
                if item_id:
                    self.ui_queue.put(("update_queue_status", item_id, "Failed (No VRC ID)"))
                self.files_uploaded_so_far += 1
                self.ui_queue.put(("update_progress", None))
                self.upload_queue.task_done()
                continue

            avatar_id = m.group(1)

            is_bulk = self.files_to_upload > 1
            if avatar_id in self.upload_history and is_bulk:
                if item_id:
                    self.ui_queue.put(("update_queue_status", item_id, "Skipped (Duplicate)"))
                self.files_uploaded_so_far += 1
                self.ui_queue.put(("update_progress", None))
                self.upload_queue.task_done()
                continue

            if avatar_id in self.upload_history and not is_bulk:
                self.ui_queue.put(("ask_upload_again", f"Avatar '{filename}' was uploaded before. Upload again?"))
                try:
                    resp = self.response_queue.get(timeout=60)
                    if not resp:
                        if item_id:
                            self.ui_queue.put(("update_queue_status", item_id, "Skipped (User choice)"))
                        self.files_uploaded_so_far += 1
                        self.ui_queue.put(("update_progress", None))
                        self.upload_queue.task_done()
                        continue
                except queue.Empty:
                    if item_id:
                        self.ui_queue.put(("update_queue_status", item_id, "Skipped (Timeout)"))
                    self.files_uploaded_so_far += 1
                    self.ui_queue.put(("update_progress", None))
                    self.upload_queue.task_done()
                    continue

            retries = 0
            while retries < MAX_RETRIES and not self.is_upload_canceled:
                try:
                    size = os.path.getsize(filepath)
                    if size > DISCORD_MAX_FILE_SIZE:
                        if item_id:
                            self.ui_queue.put(("update_queue_status", item_id, "Failed (Too Large)"))
                        self.files_uploaded_so_far += 1
                        self.ui_queue.put(("update_progress", None))
                        break

                    vrchat_url = f"https://vrchat.com/home/avatar/{avatar_id}"
                    with open(filepath, 'rb') as f:
                        files = {'file': (filename, f, 'application/octet-stream')}
                        data = {'content': f"New Avatar Uploaded!\n**VRChat URL:** {vrchat_url}"}
                        resp = requests.post(WEBHOOK_URL, data=data, files=files, timeout=60)

                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", 1))
                        show_status(self.status_label, f"Rate limit hit. Retrying in {retry_after}s...", "warning")
                        time.sleep(retry_after)
                        retries += 1
                        continue

                    resp.raise_for_status()
                    if resp.status_code in (200, 204):
                        ts = datetime.now().strftime("%H:%M:%S")
                        if item_id:
                            self.ui_queue.put(("update_queue_status", item_id, f"Success! ({ts})"))
                            self.upload_queue_tree.set(item_id, column="Progress", value="100%")
                        self.upload_history.setdefault(avatar_id, []).append(datetime.now().isoformat())
                        self.save_upload_history()
                        try:
                            os.remove(filepath)
                        except OSError:
                            pass
                        self.files_uploaded_so_far += 1
                        self.upload_count += 1
                        self.save_upload_count()
                        self.ui_queue.put(("update_progress", None))
                        break

                except requests.exceptions.RequestException:
                    retries += 1
                    if retries >= MAX_RETRIES:
                        if item_id:
                            self.ui_queue.put(("update_queue_status", item_id, "Failed (Network)"))
                        self.files_uploaded_so_far += 1
                        self.ui_queue.put(("update_progress", None))
                        break
                except Exception:
                    if item_id:
                        self.ui_queue.put(("update_queue_status", item_id, "Failed (Error)"))
                    self.files_uploaded_so_far += 1
                    self.ui_queue.put(("update_progress", None))
                    break

            self.upload_queue.task_done()
            if self.is_upload_canceled:
                break
            time.sleep(0.25)

        if not self.is_upload_canceled:
            self.ui_queue.put(("finish", "All uploads completed."))
            self.is_upload_canceled = True

    def handle_ui_queue_message(self, message: tuple) -> None:
        if not message:
            return
        mtype, *data = message
        if mtype == 'status_update':
            self.status_label.config(text=data[0] if data else "")
        elif mtype == 'progress_update':
            self.progress_bar['value'] = data[0] if data else 0
        elif mtype == 'error':
            logging.error(data[0] if data else "Unknown error")
            messagebox.showerror("Error", data[0] if data else "Unknown error")
        elif mtype == 'finish':
            show_status(self.status_label, "Uploads finished.", "success")
        elif mtype == 'update_queue_status':
            if len(data) >= 2:
                item_id, status = data[0], data[1]
                self.upload_queue_tree.set(item_id, column="Status", value=status)
                self.focus_on_file(item_id)
                if "Too Large" in status:
                    self.upload_queue_tree.item(item_id, tags=("too_big",))
                elif "Duplicate" in status:
                    self.upload_queue_tree.item(item_id, tags=("duplicate",))
                elif "Success" in status:
                    self.upload_queue_tree.item(item_id, tags=("success",))
                elif "Skipped" in status:
                    self.upload_queue_tree.item(item_id, tags=("skipped",))
                else:
                    self.upload_queue_tree.item(item_id, tags=())
        elif mtype == 'current_file':
            self.current_file_var.set(data[0] if data else "")
        elif mtype == 'update_progress':
            self.upload_progress_var.set(f"{self.files_uploaded_so_far}/{self.files_to_upload} uploaded")
            self.progress_bar_var.set((self.files_uploaded_so_far / self.files_to_upload) * 100 if self.files_uploaded_so_far and self.files_to_upload else 0)
        elif mtype == 'skipped':
            show_status(self.status_label, data[0] if data else "Skipped.", "info")
        elif mtype == 'success':
            show_status(self.status_label, data[0] if data else "Success!", "success")
        elif mtype == 'error_single':
            show_status(self.status_label, data[0] if data else "Error.", "error")
            messagebox.showerror("Error", data[0] if data else "Error.")
        elif mtype == 'ask_upload_again':
            response = messagebox.askyesno("Duplicate Upload", data[0] if data else "Upload again?")
            self.response_queue.put(response)
        elif mtype == 'indeterminate_progress':
            if data and data[0]:
                self.progress_bar.config(mode="indeterminate")
                self.progress_bar.start()
            else:
                self.progress_bar.stop()
                self.progress_bar.config(mode="determinate")
        elif mtype == 'reset_ui':
            show_status(self.status_label, data[0] if data else "Reset.", "info")
            self.progress_bar_var.set(0)
            self.upload_progress_var.set("")
            self.current_file_var.set("")
            self.files_uploaded_so_far = 0
            self.files_to_upload = 0
            for item in self.upload_queue_tree.get_children():
                self.upload_queue_tree.delete(item)
            self.file_id_map.clear()
        else:
            logging.warning(f"Unknown UI queue message type: {mtype}")

    def focus_on_file(self, item_id):
        self.upload_queue_tree.selection_set(item_id)
        self.upload_queue_tree.see(item_id)

    def filter_treeview(self, event=None):
        text = self.search_var.get().lower()
        for item in self.upload_queue_tree.get_children():
            filename = self.upload_queue_tree.item(item, "values")[0].lower()
            if text in filename:
                self.upload_queue_tree.reattach(item, '', 'end')
            else:
                self.upload_queue_tree.detach(item)

    def on_close(self):
        try:
            self.is_upload_canceled = True
        finally:
            self.destroy()


if __name__ == "__main__":
    set_appusermodel_id("Naf.VRChatUploader")

    app = AvatarUploaderApp()

    try:
        app.iconbitmap(resource_path("Icon.ico"))
    except Exception as e:
        print(f"[DEBUG] Failed to set iconbitmap: {e}")

    app.after(100, app.check_ui_queue) 
    app.mainloop()
