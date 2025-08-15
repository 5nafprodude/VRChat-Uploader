# VRChat Uploader

A desktop tool for uploading VRChat content with a simple, intuitive interface.  
Includes drag-and-drop support, progress tracking, and update checking.

## Features
- 📂 **File selection** — Browse or drag-and-drop your files.
- 📊 **Progress bar** — See real-time upload status.
- 🔄 **Auto-update check** — Notifies you if a newer version is available.
- 🎨 **Customizable UI** — Larger buttons and easy navigation.
- 🖼 **Custom icon** — Branded executable and window/taskbar icon.

## Installation
1. Download the latest release from the [Releases page](https://github.com/5nafprodude/VRChat-Uploader/releases).
2. Extract the files (if in a ZIP).
3. Run `VRChat Uploader.exe`.

No external Python installation or libraries are required — everything is packaged.

## Usage
1. **Browse** — Click the "Browse Files" button to select your VRChat asset(s).
2. **Upload** — The program will handle the upload process.
3. **Monitor progress** — The status bar and percentage indicator update in real-time.
4. **Updates** — Each time the program starts, it checks for a newer version on GitHub.

## Updating
The application checks GitHub every time it launches. If an update is available, you'll be prompted to download it.

## Development
If you want to run from source:
```bash
pip install -r requirements.txt
python main.py
