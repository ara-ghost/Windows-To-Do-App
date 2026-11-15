import ctypes
from ctypes import wintypes
import json
import os
import tkinter as tk

DATA_FILE = os.path.join(os.path.expanduser("~"), "desktop_todos.json")

# Colors (Translucent Dark Glass for Wallpapers)
BG_COLOR = "#16161d"
HEADER_BG = "#1f1f29"
INPUT_BG = "#252532"
ACCENT = "#4cc9f0"
TEXT_COLOR = "#f4f4f8"
DONE_COLOR = "#6c7086"
BTN_HOVER = "#323242"

# Win32 Constants
GWL_EXSTYLE = -20
GWL_HWNDPARENT = -8
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
HWND_BOTTOM = 1
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SW_RESTORE = 9

user32 = ctypes.windll.user32
GetWindowLongPtr = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
SetWindowLongPtr = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)

GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongPtr.restype = ctypes.c_ssize_t
SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
SetWindowLongPtr.restype = ctypes.c_ssize_t
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND


class WallpaperTodoApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Desktop To-Do")
        self.root.configure(bg=BG_COLOR)
        self.root.overrideredirect(True)

        self.state = self.load_state()
        self.tasks = self.state["tasks"]
        self.mode = self.state.get("mode", "wallpaper")  # "wallpaper" or "top"
        x = self.state.get("x", 60)
        y = self.state.get("y", 60)

        self.root.geometry(f"310x420+{x}+{y}")
        self.root.attributes("-alpha", 0.82)

        self._drag_x = 0
        self._drag_y = 0

        self.build_ui()
        self.render_tasks()

        # Apply Win32 desktop integration once window handle exists
        self.root.update_idletasks()
        self.hwnd = self.get_top_hwnd()
        self.apply_desktop_integration()

        # Keep widget alive on desktop if Win+D or Win+M is pressed
        self.root.bind("<Unmap>", self.prevent_minimize)
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.root.bind("<Enter>", lambda e: self.root.attributes("-alpha", 0.96))
        self.root.bind("<Leave>", self.on_mouse_leave)
        self.keep_alive_loop()

    def get_top_hwnd(self):
        wid = self.root.winfo_id()
        parent = user32.GetParent(wid)
        return parent if parent else wid

    def apply_desktop_integration(self):
        # Hide from Alt+Tab and Taskbar
        ex_style = GetWindowLongPtr(self.hwnd, GWL_EXSTYLE)
        ex_style = (ex_style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        SetWindowLongPtr(self.hwnd, GWL_EXSTYLE, ex_style)

        # Attach owner to Windows desktop manager (Progman) so it stays with wallpaper
        progman = user32.FindWindowW("Progman", None)
        if progman:
            SetWindowLongPtr(self.hwnd, GWL_HWNDPARENT, progman)

        self.apply_z_order()

    def apply_z_order(self):
        if self.mode == "top":
            self.root.attributes("-topmost", True)
            user32.SetWindowPos(
                self.hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        else:
            self.root.attributes("-topmost", False)
            user32.SetWindowPos(
                self.hwnd,
                HWND_BOTTOM,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )

    def prevent_minimize(self, event=None):
        if user32.IsIconic(self.hwnd):
            user32.ShowWindow(self.hwnd, SW_RESTORE)
        self.apply_z_order()

    def keep_alive_loop(self):
        # Ensures Win+D (Show Desktop) never hides the widget
        if user32.IsIconic(self.hwnd):
            user32.ShowWindow(self.hwnd, SW_RESTORE)
        if self.mode == "wallpaper" and self.root.focus_get() is None:
            user32.SetWindowPos(
                self.hwnd,
                HWND_BOTTOM,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        self.root.after(400, self.keep_alive_loop)

    def on_focus_out(self, event=None):
        self.root.attributes("-alpha", 0.82)
        if self.mode == "wallpaper":
            self.root.after(50, self.apply_z_order)

    def on_mouse_leave(self, event=None):
        if self.root.focus_get() is None:
            self.root.attributes("-alpha", 0.82)

    def build_ui(self):
        # --- Draggable Header ---
        header = tk.Frame(self.root, bg=HEADER_BG, height=34)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="  TO-DO",
            bg=HEADER_BG,
            fg=ACCENT,
            font=("Segoe UI", 10, "bold"),
        )
        title.pack(side="left")

        close_btn = tk.Button(
            header,
            text="✕",
            bg=HEADER_BG,
            fg=DONE_COLOR,
            bd=0,
            font=("Segoe UI", 10),
            activebackground="#e63946",
            activeforeground="white",
            command=self.root.destroy,
            cursor="hand2",
        )
        close_btn.pack(side="right", padx=(2, 6))

        self.mode_btn = tk.Button(
            header,
            text="Wallpaper" if self.mode == "wallpaper" else "On Top",
            bg=HEADER_BG,
            fg=ACCENT if self.mode == "top" else DONE_COLOR,
            bd=0,
            font=("Segoe UI", 8, "bold"),
            activebackground=BTN_HOVER,
            activeforeground=ACCENT,
            command=self.toggle_mode,
            cursor="hand2",
        )
        self.mode_btn.pack(side="right", padx=6)

        clear_btn = tk.Button(
            header,
            text="Clear",
            bg=HEADER_BG,
            fg=DONE_COLOR,
            bd=0,
            font=("Segoe UI", 8),
            activebackground=BTN_HOVER,
            activeforeground=TEXT_COLOR,
            command=self.clear_done,
            cursor="hand2",
        )
        clear_btn.pack(side="right", padx=4)

        for widget in (header, title):
            widget.bind("<Button-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.do_drag)
            widget.bind("<ButtonRelease-1>", self.stop_drag)

        # --- Task Input ---
        input_frame = tk.Frame(self.root, bg=BG_COLOR, pady=10, padx=12)
        input_frame.pack(fill="x")

        self.entry = tk.Entry(
            input_frame,
            bg=INPUT_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            bd=0,
            font=("Segoe UI", 10),
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        self.entry.bind("<Return>", lambda e: self.add_task())

        add_btn = tk.Button(
            input_frame,
            text="+",
            bg=ACCENT,
            fg="#11111b",
            bd=0,
            font=("Segoe UI", 11, "bold"),
            width=3,
            command=self.add_task,
            cursor="hand2",
        )
        add_btn.pack(side="right", ipady=2)

        # --- Task List Container ---
        self.list_frame = tk.Frame(self.root, bg=BG_COLOR, padx=12)
        self.list_frame.pack(fill="both", expand=True)

    def start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def stop_drag(self, event):
        self.state["x"] = self.root.winfo_x()
        self.state["y"] = self.root.winfo_y()
        self.save_state()
        self.apply_z_order()

    def toggle_mode(self):
        self.mode = "top" if self.mode == "wallpaper" else "wallpaper"
        self.state["mode"] = self.mode
        self.mode_btn.config(
            text="Wallpaper" if self.mode == "wallpaper" else "On Top",
            fg=ACCENT if self.mode == "top" else DONE_COLOR,
        )
        self.save_state()
        self.apply_z_order()

    def load_state(self):
        default = {"x": 60, "y": 60, "mode": "wallpaper", "tasks": []}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Migrate old list format automatically
                    if isinstance(data, list):
                        default["tasks"] = data
                        return default
                    if isinstance(data, dict):
                        default.update(data)
                        return default
            except (json.JSONDecodeError, IOError):
                pass
        return default

    def save_state(self):
        self.state["tasks"] = self.tasks
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def add_task(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.tasks.append({"text": text, "done": False})
        self.entry.delete(0, tk.END)
        self.save_state()
        self.render_tasks()

    def toggle_task(self, index):
        self.tasks[index]["done"] = not self.tasks[index]["done"]
        self.save_state()
        self.render_tasks()

    def delete_task(self, index):
        self.tasks.pop(index)
        self.save_state()
        self.render_tasks()

    def clear_done(self):
        self.tasks = [t for t in self.tasks if not t["done"]]
        self.save_state()
        self.render_tasks()

    def render_tasks(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        for idx, task in enumerate(self.tasks):
            row = tk.Frame(self.list_frame, bg=BG_COLOR, pady=3)
            row.pack(fill="x")

            check_char = "☑" if task["done"] else "☐"
            fg_color = DONE_COLOR if task["done"] else TEXT_COLOR
            font_style = (
                ("Segoe UI", 10, "overstrike")
                if task["done"]
                else ("Segoe UI", 10)
            )

            lbl = tk.Label(
                row,
                text=f"{check_char}  {task['text']}",
                bg=BG_COLOR,
                fg=fg_color,
                font=font_style,
                anchor="w",
                cursor="hand2",
            )
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, i=idx: self.toggle_task(i))

            del_btn = tk.Button(
                row,
                text="×",
                bg=BG_COLOR,
                fg=DONE_COLOR,
                bd=0,
                font=("Segoe UI", 11),
                activebackground=BG_COLOR,
                activeforeground="#e63946",
                command=lambda i=idx: self.delete_task(i),
                cursor="hand2",
            )
            del_btn.pack(side="right")


if __name__ == "__main__":
    root = tk.Tk()
    app = WallpaperTodoApp(root)
    root.mainloop()