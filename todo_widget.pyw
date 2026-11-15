import ctypes
from ctypes import wintypes
import json
import os
import re
import tkinter as tk
from tkinter import font as tkfont
import urllib.request

DATA_FILE = os.path.join(os.path.expanduser("~"), "desktop_todos.json")
FONT_DIR = os.path.join(os.path.expanduser("~"), ".desktop_todo_fonts")

# Curated Apple-Inspired Themes
THEMES = {
    "ocean": {
        "bg": "#0B192C",         # Deep midnight sapphire (matches blue wallpapers)
        "rim": 0x006E4521,       # Subtle steel-blue DWM border (BGR: #21456E)
        "pill": "#132743",       # Elevated pill surface
        "pill_hover": "#1B365D",
        "divider": "#162D4D",
        "accent": "#38BDF8",     # Luminous sky/cyan blue
        "accent_hover": "#7DD3FC",
        "danger": "#FF453A",
        "text": "#F1F5F9",
        "muted": "#7CA1C4",
        "done": "#4C6E91",
    },
    "graphite": {
        "bg": "#1C1C1E",         # Classic macOS Dark Mode
        "rim": 0x00444442,       # Subtle border rim (BGR: #424444)
        "pill": "#2C2C2E",
        "pill_hover": "#3A3A3C",
        "divider": "#2A2A2D",
        "accent": "#0A84FF",     # Apple System Blue
        "accent_hover": "#409CFF",
        "danger": "#FF453A",
        "text": "#F5F5F7",
        "muted": "#8E8E93",
        "done": "#636366",
    },
    "frost": {
        "bg": "#EAF2FB",         # Soft macOS Light Mode
        "rim": 0x00E6D4C2,       # Soft border (BGR: #C2D4E6)
        "pill": "#D8E6F5",
        "pill_hover": "#C7DCF2",
        "divider": "#D6E3F0",
        "accent": "#007AFF",     # Apple Light Mode Blue
        "accent_hover": "#3395FF",
        "danger": "#FF3B30",
        "text": "#0F172A",
        "muted": "#5A718A",
        "done": "#8FA3B8",
    },
}
THEME_ORDER = ["ocean", "graphite", "frost"]
WIDGET_OPACITY = 0.85  # Constant translucency (0.0 = invisible, 1.0 = solid)

# Win32 & DWM Constants
GWL_EXSTYLE = -20
GWL_HWNDPARENT = -8
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
HWND_BOTTOM = 1
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SW_RESTORE = 9
FR_PRIVATE = 0x10

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWCP_ROUND = 2

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
dwmapi = ctypes.windll.dwmapi

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
gdi32.AddFontResourceExW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
gdi32.AddFontResourceExW.restype = ctypes.c_int


def enable_retina_dpi():
    """Enables sharp High-DPI text rendering on Windows."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def ensure_apple_font():
    """Loads Inter (SF Pro's identical twin) privately for crisp macOS typography."""
    try:
        os.makedirs(FONT_DIR, exist_ok=True)
        ttf_files = [
            os.path.join(FONT_DIR, f)
            for f in os.listdir(FONT_DIR)
            if f.lower().endswith(".ttf")
        ]
        if not ttf_files:
            css_url = "https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700"
            req = urllib.request.Request(
                css_url, headers={"User-Agent": "Python-urllib/3.12"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                css = resp.read().decode("utf-8", errors="ignore")
            urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css)
            for idx, u in enumerate(urls[:3]):
                dest = os.path.join(FONT_DIR, f"Inter_{idx}.ttf")
                urllib.request.urlretrieve(u, dest)
                ttf_files.append(dest)

        for path in ttf_files:
            gdi32.AddFontResourceExW(path, FR_PRIVATE, 0)
    except Exception:
        pass


def draw_rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    points = [
        x1 + r, y1, x1 + r, y1,
        x2 - r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r, x2, y1 + r,
        x2, y2 - r, x2, y2 - r,
        x2, y2, x2 - r, y2, x2 - r, y2,
        x1 + r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y2 - r,
        x1, y1 + r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class AppleDesktopTodoApp:

    def __init__(self, root):
        self.root = root
        self.root.title("To-Do")
        self.root.overrideredirect(True)

        # Calculate display DPI scale factor
        self.scale = max(1.0, self.root.winfo_fpixels("1i") / 96.0)
        self.width = self.s(336)
        self.min_row_height = self.s(44)
        self.max_list_height = self.s(320)

        # Pick SF Pro if installed, otherwise Inter (loaded above), else Helvetica/Segoe
        available_fonts = set(tkfont.families())
        self.font_display = "Segoe UI"
        for candidate in (
            "SF Pro Display",
            "SF Pro Text",
            "Inter",
            "Helvetica Neue",
            "Segoe UI Variable Display",
        ):
            if candidate in available_fonts:
                self.font_display = candidate
                break

        self.font_text = "Segoe UI"
        for candidate in (
            "SF Pro Text",
            "SF Pro Display",
            "Inter",
            "Helvetica Neue",
            "Segoe UI Variable Text",
        ):
            if candidate in available_fonts:
                self.font_text = candidate
                break

        self.state = self.load_state()
        self.tasks = self.state["tasks"]
        self.mode = self.state.get("mode", "wallpaper")
        self.locked = self.state.get("locked", True)
        self.theme_name = self.state.get("theme", "ocean")
        if self.theme_name not in THEMES:
            self.theme_name = "ocean"
        self.t = THEMES[self.theme_name]

        x = self.state.get("x", self.s(60))
        y = self.state.get("y", self.s(60))
        self.root.geometry(f"{self.width}x{self.s(152)}+{x}+{y}")
        self.root.configure(bg=self.t["bg"])
        self.root.attributes("-alpha", WIDGET_OPACITY)

        self._drag_x = 0
        self._drag_y = 0
        self._placeholder_active = False

        self.build_ui()
        self.render_tasks()

        # Apply Win32 desktop docking + native Windows 11 rounded corners
        self.root.update_idletasks()
        self.hwnd = self.get_top_hwnd()
        self.apply_desktop_integration()

        self.root.bind("<Unmap>", self.prevent_minimize)
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.keep_alive_loop()

    def s(self, val):
        return int(round(val * self.scale))

    def get_top_hwnd(self):
        wid = self.root.winfo_id()
        parent = user32.GetParent(wid)
        return parent if parent else wid

    def apply_dwm_style(self):
        try:
            corner_pref = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                self.hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(corner_pref),
                ctypes.sizeof(corner_pref),
            )
            border_color = ctypes.c_int(self.t["rim"])
            dwmapi.DwmSetWindowAttribute(
                self.hwnd,
                DWMWA_BORDER_COLOR,
                ctypes.byref(border_color),
                ctypes.sizeof(border_color),
            )
        except Exception:
            pass

    def apply_desktop_integration(self):
        ex_style = GetWindowLongPtr(self.hwnd, GWL_EXSTYLE)
        ex_style = (ex_style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        SetWindowLongPtr(self.hwnd, GWL_EXSTYLE, ex_style)

        progman = user32.FindWindowW("Progman", None)
        if progman:
            SetWindowLongPtr(self.hwnd, GWL_HWNDPARENT, progman)

        self.apply_dwm_style()
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
        if self.mode == "wallpaper":
            self.root.after(50, self.apply_z_order)

    def draw_lock_icon(self):
        self.lock_btn.delete("all")
        if self.locked:
            self.lock_btn.create_arc(
                self.s(4), self.s(2), self.s(12), self.s(10),
                start=0, extent=180, style="arc",
                outline=self.t["accent"], width=1.6 * self.scale,
            )
            self.lock_btn.create_rectangle(
                self.s(3), self.s(7), self.s(13), self.s(14),
                fill=self.t["accent"], outline=self.t["accent"],
            )
        else:
            self.lock_btn.create_arc(
                self.s(6), self.s(1), self.s(14), self.s(9),
                start=0, extent=180, style="arc",
                outline=self.t["muted"], width=1.6 * self.scale,
            )
            self.lock_btn.create_rectangle(
                self.s(3), self.s(7), self.s(13), self.s(14),
                fill="", outline=self.t["muted"], width=1.4 * self.scale,
            )

    def build_ui(self):
        for child in self.root.winfo_children():
            child.destroy()

        self.root.configure(bg=self.t["bg"])
        drag_cursor = "" if self.locked else "fleur"

        # --- Top Header Bar ---
        self.header = tk.Frame(
            self.root, bg=self.t["bg"], height=self.s(46), cursor=drag_cursor
        )
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.title_lbl = tk.Label(
            self.header,
            text="To-Do",
            bg=self.t["bg"],
            fg=self.t["text"],
            font=(self.font_display, 14, "bold"),
            cursor=drag_cursor,
        )
        self.title_lbl.pack(side="left", padx=(self.s(16), self.s(6)), pady=(self.s(6), 0))

        self.count_lbl = tk.Label(
            self.header,
            text="0",
            bg=self.t["pill"],
            fg=self.t["accent"],
            font=(self.font_text, 9, "bold"),
            padx=self.s(7),
            pady=self.s(1),
            cursor=drag_cursor,
        )
        self.count_lbl.pack(side="left", pady=(self.s(8), 0))

        # Close button
        self.close_btn = tk.Label(
            self.header,
            text="✕",
            bg=self.t["bg"],
            fg=self.t["muted"],
            font=(self.font_text, 10, "bold"),
            cursor="hand2",
        )
        self.close_btn.pack(side="right", padx=(self.s(5), self.s(14)), pady=(self.s(6), 0))
        self.close_btn.bind("<Button-1>", lambda e: self.root.destroy())
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.config(fg=self.t["danger"]))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.config(fg=self.t["muted"]))

        # Desktop / Pinned Mode Pill
        self.mode_btn = tk.Label(
            self.header,
            text="Desktop" if self.mode == "wallpaper" else "Pinned",
            bg=self.t["pill"],
            fg=self.t["muted"] if self.mode == "wallpaper" else self.t["accent"],
            font=(self.font_text, 8, "bold"),
            padx=self.s(8),
            pady=self.s(2),
            cursor="hand2",
        )
        self.mode_btn.pack(side="right", padx=self.s(4), pady=(self.s(7), 0))
        self.mode_btn.bind("<Button-1>", lambda e: self.toggle_mode())
        self.mode_btn.bind("<Enter>", lambda e: self.mode_btn.config(bg=self.t["pill_hover"]))
        self.mode_btn.bind("<Leave>", lambda e: self.mode_btn.config(bg=self.t["pill"]))

        # Clear Done Button
        self.clear_btn = tk.Label(
            self.header,
            text="Clear",
            bg=self.t["bg"],
            fg=self.t["done"],
            font=(self.font_text, 8, "bold"),
            cursor="hand2",
        )
        self.clear_btn.pack(side="right", padx=self.s(4), pady=(self.s(7), 0))
        self.clear_btn.bind("<Button-1>", lambda e: self.clear_done())
        self.clear_btn.bind("<Enter>", lambda e: self.clear_btn.config(fg=self.t["text"]))
        self.clear_btn.bind("<Leave>", lambda e: self.update_header_states())

        # Position Lock Toggle Icon
        self.lock_btn = tk.Canvas(
            self.header,
            width=self.s(16),
            height=self.s(16),
            bg=self.t["bg"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.draw_lock_icon()
        self.lock_btn.pack(side="right", padx=self.s(4), pady=(self.s(8), 0))
        self.lock_btn.bind("<Button-1>", lambda e: self.toggle_lock())

        # Theme Cycle Dot (Ocean / Graphite / Frost)
        self.theme_dot = tk.Canvas(
            self.header,
            width=self.s(14),
            height=self.s(14),
            bg=self.t["bg"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.theme_dot.create_oval(
            self.s(2), self.s(2), self.s(12), self.s(12),
            fill=self.t["accent"], outline=self.t["muted"], width=1,
        )
        self.theme_dot.pack(side="right", padx=self.s(4), pady=(self.s(9), 0))
        self.theme_dot.bind("<Button-1>", lambda e: self.cycle_theme())

        for w in (self.header, self.title_lbl, self.count_lbl):
            w.bind("<Button-1>", self.start_drag)
            w.bind("<B1-Motion>", self.do_drag)
            w.bind("<ButtonRelease-1>", self.stop_drag)

        # --- Rounded Pill Input Bar ---
        input_wrap = tk.Frame(self.root, bg=self.t["bg"], height=self.s(44))
        input_wrap.pack(fill="x", padx=self.s(14), pady=(self.s(2), self.s(4)))
        input_wrap.pack_propagate(False)

        inner_w = self.width - self.s(28)
        self.input_canvas = tk.Canvas(
            input_wrap,
            width=inner_w,
            height=self.s(40),
            bg=self.t["bg"],
            highlightthickness=0,
            bd=0,
        )
        self.input_canvas.pack(fill="both", expand=True)

        self.input_pill = draw_rounded_rect(
            self.input_canvas,
            self.s(1),
            self.s(1),
            inner_w - self.s(2),
            self.s(38),
            self.s(12),
            fill=self.t["pill"],
            outline=self.t["divider"],
            width=1,
        )

        self.entry = tk.Entry(
            input_wrap,
            bg=self.t["pill"],
            fg=self.t["text"],
            insertbackground=self.t["accent"],
            bd=0,
            highlightthickness=0,
            font=(self.font_text, 10, "bold"),
        )
        self.entry.place(
            x=self.s(14), y=self.s(9), width=inner_w - self.s(52), height=self.s(22)
        )
        self.entry.bind("<Return>", lambda e: self.add_task())
        self.entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.entry.bind("<FocusOut>", self.on_entry_focus_out)
        self.set_placeholder()

        # Circular Add Button
        cx, cy = inner_w - self.s(20), self.s(19.5)
        self.add_circle = self.input_canvas.create_oval(
            cx - self.s(11),
            cy - self.s(11),
            cx + self.s(11),
            cy + self.s(11),
            fill=self.t["accent"],
            outline="",
        )
        self.add_plus_h = self.input_canvas.create_line(
            cx - self.s(4.5), cy, cx + self.s(4.5), cy,
            fill="#FFFFFF", width=2.0 * self.scale, capstyle="round",
        )
        self.add_plus_v = self.input_canvas.create_line(
            cx, cy - self.s(4.5), cx, cy + self.s(4.5),
            fill="#FFFFFF", width=2.0 * self.scale, capstyle="round",
        )
        for item in (self.add_circle, self.add_plus_h, self.add_plus_v):
            self.input_canvas.tag_bind(item, "<Button-1>", lambda e: self.add_task())
            self.input_canvas.tag_bind(
                item,
                "<Enter>",
                lambda e: self.input_canvas.itemconfig(
                    self.add_circle, fill=self.t["accent_hover"]
                ),
            )
            self.input_canvas.tag_bind(
                item,
                "<Leave>",
                lambda e: self.input_canvas.itemconfig(
                    self.add_circle, fill=self.t["accent"]
                ),
            )

        # --- Scrollable Task List Container ---
        self.list_container = tk.Frame(self.root, bg=self.t["bg"])
        self.list_container.pack(
            fill="both", expand=True, padx=self.s(14), pady=(self.s(2), self.s(10))
        )

        self.list_canvas = tk.Canvas(
            self.list_container,
            bg=self.t["bg"],
            highlightthickness=0,
            bd=0,
        )
        self.list_canvas.pack(fill="both", expand=True)

        self.rows_frame = tk.Frame(self.list_canvas, bg=self.t["bg"])
        self.list_window = self.list_canvas.create_window(
            (0, 0), window=self.rows_frame, anchor="nw", width=inner_w
        )

        self.rows_frame.bind(
            "<Configure>",
            lambda e: self.list_canvas.configure(
                scrollregion=self.list_canvas.bbox("all")
            ),
        )
        self.list_canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    def on_mousewheel(self, event):
        if self.rows_frame.winfo_height() > self.list_canvas.winfo_height():
            self.list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_placeholder(self):
        if not self.entry.get():
            self._placeholder_active = True
            self.entry.config(fg=self.t["muted"])
            self.entry.insert(0, "New Reminder...")

    def on_entry_focus_in(self, event=None):
        self.input_canvas.itemconfig(self.input_pill, outline=self.t["accent"])
        if self._placeholder_active:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=self.t["text"])
            self._placeholder_active = False

    def on_entry_focus_out(self, event=None):
        self.input_canvas.itemconfig(self.input_pill, outline=self.t["divider"])
        if not self.entry.get().strip():
            self.entry.delete(0, tk.END)
            self.set_placeholder()

    def toggle_lock(self):
        self.locked = not self.locked
        self.state["locked"] = self.locked
        self.save_state()
        self.draw_lock_icon()
        drag_cursor = "" if self.locked else "fleur"
        for w in (self.header, self.title_lbl, self.count_lbl):
            w.config(cursor=drag_cursor)

    def start_drag(self, event):
        self.root.focus_set()
        if self.locked:
            return
        self._drag_x = event.x
        self._drag_y = event.y

    def do_drag(self, event):
        if self.locked:
            return
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def stop_drag(self, event):
        if self.locked:
            return
        self.state["x"] = self.root.winfo_x()
        self.state["y"] = self.root.winfo_y()
        self.save_state()
        self.apply_z_order()

    def toggle_mode(self):
        self.mode = "top" if self.mode == "wallpaper" else "wallpaper"
        self.state["mode"] = self.mode
        self.mode_btn.config(
            text="Desktop" if self.mode == "wallpaper" else "Pinned",
            fg=self.t["muted"] if self.mode == "wallpaper" else self.t["accent"],
        )
        self.save_state()
        self.apply_z_order()

    def cycle_theme(self):
        next_idx = (THEME_ORDER.index(self.theme_name) + 1) % len(THEME_ORDER)
        self.theme_name = THEME_ORDER[next_idx]
        self.t = THEMES[self.theme_name]
        self.state["theme"] = self.theme_name
        self.save_state()
        self.build_ui()
        self.render_tasks()
        self.apply_dwm_style()

    def update_header_states(self):
        remaining = sum(1 for t in self.tasks if not t["done"])
        has_done = any(t["done"] for t in self.tasks)
        self.count_lbl.config(text=str(remaining))
        self.clear_btn.config(fg=self.t["accent"] if has_done else self.t["done"])

    def load_state(self):
        default = {
            "x": self.s(60),
            "y": self.s(60),
            "mode": "wallpaper",
            "theme": "ocean",
            "locked": True,
            "dpi_scaled": True,
            "tasks": [],
        }
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        default["tasks"] = data
                        return default
                    if isinstance(data, dict):
                        if not data.get("dpi_scaled") and self.scale > 1.0:
                            data["x"] = int(round(data.get("x", 60) * self.scale))
                            data["y"] = int(round(data.get("y", 60) * self.scale))
                            data["dpi_scaled"] = True
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
        if self._placeholder_active:
            return
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
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        self.update_header_states()

        anchor_x = self.state.get("x", self.s(60))
        anchor_y = self.state.get("y", self.s(60))

        if not self.tasks:
            empty = tk.Label(
                self.rows_frame,
                text="All Clear",
                bg=self.t["bg"],
                fg=self.t["done"],
                font=(self.font_text, 11, "bold"),
                pady=self.s(10),
            )
            empty.pack(fill="x")
            target_height = self.s(108) + self.min_row_height
            self.root.geometry(f"{self.width}x{target_height}+{anchor_x}+{anchor_y}")
            return

        row_width = self.width - self.s(28)
        text_max_w = row_width - self.s(60)
        total_list_height = 0

        for idx, task in enumerate(self.tasks):
            row = tk.Canvas(
                self.rows_frame,
                width=row_width,
                height=self.min_row_height,
                bg=self.t["bg"],
                highlightthickness=0,
                bd=0,
                cursor="hand2",
            )
            row.pack(fill="x")

            # Auto-wrapping task text (expands vertically so nothing is ever cut off)
            text_item = row.create_text(
                self.s(36),
                self.s(12),
                text=task["text"],
                fill=self.t["done"] if task["done"] else self.t["text"],
                font=(self.font_text, 11, "bold"),
                anchor="nw",
                width=text_max_w,
            )

            bbox = row.bbox(text_item)
            text_h = (bbox[3] - bbox[1]) if bbox else self.s(20)
            row_h = max(self.min_row_height, text_h + self.s(24))
            row.config(height=row_h)
            total_list_height += row_h

            # Circular Apple-style checkbox aligned with the first line of text
            if task["done"]:
                circle = row.create_oval(
                    self.s(6), self.s(12), self.s(25), self.s(31),
                    fill=self.t["accent"], outline=self.t["accent"],
                )
                row.create_line(
                    self.s(11.0),
                    self.s(21.8),
                    self.s(14.2),
                    self.s(25.0),
                    self.s(20.2),
                    self.s(18.2),
                    fill="#FFFFFF",
                    width=2.0 * self.scale,
                    capstyle="round",
                    joinstyle="round",
                )
            else:
                circle = row.create_oval(
                    self.s(6), self.s(12), self.s(25), self.s(31),
                    fill=self.t["bg"], outline=self.t["done"], width=1.8 * self.scale,
                )

            # Inset separator between rows
            if idx < len(self.tasks) - 1:
                row.create_line(
                    self.s(36),
                    row_h - 1,
                    row_width - self.s(4),
                    row_h - 1,
                    fill=self.t["divider"],
                )

            # Hover-only delete button
            del_item = row.create_text(
                row_width - self.s(10),
                self.s(21),
                text="✕",
                fill=self.t["bg"],
                font=(self.font_text, 9, "bold"),
            )

            def on_row_click(event, i=idx, rw=row_width):
                if event.x >= rw - self.s(24):
                    self.delete_task(i)
                else:
                    self.toggle_task(i)

            def on_row_enter(event, r=row, d=del_item, c=circle, done=task["done"]):
                r.itemconfig(d, fill=self.t["muted"])
                if not done:
                    r.itemconfig(c, outline=self.t["accent"])

            def on_row_leave(event, r=row, d=del_item, c=circle, done=task["done"]):
                r.itemconfig(d, fill=self.t["bg"])
                if not done:
                    r.itemconfig(c, outline=self.t["done"])

            def on_row_motion(event, r=row, d=del_item, rw=row_width):
                r.itemconfig(
                    d,
                    fill=self.t["danger"]
                    if event.x >= rw - self.s(24)
                    else self.t["muted"],
                )

            row.bind("<Button-1>", on_row_click)
            row.bind("<Enter>", on_row_enter)
            row.bind("<Leave>", on_row_leave)
            row.bind("<Motion>", on_row_motion)

        # Auto-size card height around all wrapped rows while anchored to saved (x, y)
        visible_h = min(total_list_height, self.max_list_height)
        target_height = self.s(108) + visible_h
        self.root.geometry(f"{self.width}x{target_height}+{anchor_x}+{anchor_y}")


if __name__ == "__main__":
    enable_retina_dpi()
    ensure_apple_font()
    root = tk.Tk()
    app = AppleDesktopTodoApp(root)
    root.mainloop()