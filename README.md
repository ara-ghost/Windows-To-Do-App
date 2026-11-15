# Desktop To-Do Widget

A lightweight, Apple-inspired desktop to-do widget for **Windows 10 & 11** that stays cleanly anchored to your wallpaper layer. Built with Python, Tkinter, and native Win32/DWM APIs.

![Desktop To-Do Widget Preview](preview.png)

---

## Features

- **Wallpaper Layer Docking (`Desktop` / `Pinned`):** Stays pinned directly to your desktop background—even when pressing `Win + D`—or toggles to always-on-top mode with a single click.
- **macOS Vibrancy Aesthetic:** Features native Windows 11 rounded corners, subtle glass border rims, constant translucency, Retina High-DPI scaling, and **Inter / SF Pro** typography.
- **3 Built-In Themes:** Cycle between **Ocean** (midnight sapphire), **Graphite** (macOS dark mode), and **Frost** (light vibrancy) using the color dot in the header.
- **Urgent Wave Alerts:** Mark any task as **Urgent** to pin it straight to the top in bold red text with a smooth 60 FPS letter-wave bounce every 10 seconds.
- **Auto-Wrapping & Dynamic Sizing:** Long tasks automatically wrap onto multiple lines and expand the widget height so nothing is ever cut off.
- **Position Lock:** Lock the widget in place with the header padlock icon so you never drag it accidentally.
- **Automatic Boot Startup (`Boot`):** Registers itself in the Windows Registry (`HKCU\...\Run`) out of the box so your tasks are waiting whenever you turn on your PC.
- **100% Local & Private:** Tasks and preferences are stored locally in `C:\Users\<YourName>\desktop_todos.json` with zero accounts, cloud sync, or background telemetry.

---

## Quick Start (Windows)

1. Go to the **[Releases](../../releases)** page and download **`DesktopTodo.exe`**.
2. Double-click **`DesktopTodo.exe`** to launch the widget.
   > **Note on Windows SmartScreen:** Because this is an independent, unsigned executable, Windows Defender may show a *"Windows protected your PC"* popup on the first launch. Click **More info → Run anyway** to start the app.
3. Drag the header to place the widget anywhere on your wallpaper, then click the **padlock icon** to lock it in position.

---

## Header Controls

| Control | Action |
| :--- | :--- |
| **Color Dot** | Cycle between **Ocean**, **Graphite**, and **Frost** themes |
| **Padlock Icon** | Lock or unlock the widget's position on your desktop |
| **Clear** | Remove all completed tasks |
| **Boot** | Toggle automatic launch when Windows starts |
| **Desktop / Pinned** | Switch between wallpaper-layer docking and always-on-top mode |
| **✕** | Close the widget |

---

## Run or Build from Source

If you want to customize the colors, opacity, or behavior directly:

1. **Clone the repository:**
   ```powershell
   git clone [https://github.com/](https://github.com/)<your-username>/<your-repo-name>.git
   cd <your-repo-name>
   ```

2. **Run directly with Python (no external packages required):**
   ```powershell
   py todo_widget.pyw
   ```

3. **Build a standalone `.exe` with PyInstaller:**
   ```powershell
   py -m pip install pyinstaller
   py make_icon.py
   py -m PyInstaller --clean --noconsole --onefile --icon=todo.ico --name "DesktopTodo" todo_widget.pyw
   ```
   The compiled executable will be generated in `dist\DesktopTodo.exe`.