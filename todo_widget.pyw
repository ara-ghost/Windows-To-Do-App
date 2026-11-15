import ctypes
from ctypes import wintypes
import json
import os
import tkinter as tk
from tkinter import font as tkfont

DATA_FILE = os.path.join(os.path.expanduser("~"), "desktop_todos.json")

# Curated Apple-Inspired Vibrancy Themes
THEMES = {
    "ocean": {
        "bg": "#0B192C",         # Deep midnight sapphire (matches blue wallpapers)
        "rim": 0x006E4521,       # Subtle steel-blue DWM border (BGR: #21456E)
        "pill": "#132743",       # Elevated glass pill
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
        "rim": 0x00444442,       # Subtle glass rim (BGR: #424444)
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
        "bg": "#EAF2FB",         # Soft macOS Light Vibrancy
        "rim": 0x00E6D4C2,       # Soft frosted border (BGR: #C2D4E6)
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

WIDTH = 330
ROW_HEIGHT = 44
MAX_VISIBLE_ROWS = 6

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

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWCP_ROUND = 2

user32 = ctypes.windll.user32
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

        available_fonts = set(tkfont.families())
        self.font_display = (
            "Segoe UI Variable Display"
            if "Segoe UI Variable Display" in available_fonts
            else "Segoe UI"
        )
        self.font_text = (
            "Segoe UI Variable Text"
            if "Segoe UI Variable Text" in available_fonts
            else "Segoe UI"
        )

        self.state = self.load_state()
        self.tasks = self.state["tasks"]
        self.mode = self.state.get("mode", "wallpaper")
        self.locked = self.state.get("locked", True)
        self.theme_name = self.state.get("theme", "ocean")
        if self.theme_name not in THEMES:
            self.theme_name = "ocean"
        self.t = THEMES[self.theme_name]

        x = self.state.get("x", 60)
        y = self.state.get("y", 60)
        self.root.geometry(f"{WIDTH}x152+{x}+{y}")
        self.root.configure(bg=self.t["bg"])
        self.root.attributes("-alpha", 0.90)

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
        self.root.bind("<Enter>", lambda e: self.root.attributes("-alpha", 0.97))
        self.root.bind("<Leave>", self.on_mouse_leave)
        self.keep_alive_loop()

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
        self.root.attributes("-alpha", 0.90)
        if self.mode == "wallpaper":
            self.root.after(50, self.apply_z_order)

    def on_mouse_leave(self, event=None):
        if self.root.focus_get() is None:
            self.root.attributes("-alpha", 0.90)

    def draw_lock_icon(self):
        self.lock_btn.delete("all")
        if self.locked:
            # Closed padlock shackle + filled accent body
            self.lock_btn.create_arc(
                4, 2, 12, 10, start=0, extent=180, style="arc",
                outline=self.t["accent"], width=1.6
            )
            self.lock_btn.create_rectangle(
                3, 7, 13, 14, fill=self.t["accent"], outline=self.t["accent"]
            )
        else:
            # Open padlock shackle + muted outline body
            self.lock_btn.create_arc(
                6, 1, 14, 9, start=0, extent=180, style="arc",
                outline=self.t["muted"], width=1.6
            )
            self.lock_btn.create_rectangle(
                3, 7, 13, 14, fill="", outline=self.t["muted"], width=1.4
            )

    def build_ui(self):
        for child in self.root.winfo_children():
            child.destroy()

        self.root.configure(bg=self.t["bg"])
        drag_cursor = "" if self.locked else "fleur"

        # --- Top Header Bar ---
        self.header = tk.Frame(self.root, bg=self.t["bg"], height=46, cursor=drag_cursor)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.title_lbl = tk.Label(
            self.header,
            text="To-Do",
            bg=self.t["bg"],
            fg=self.t["text"],
            font=(self.font_display, 15, "bold"),
            cursor=drag_cursor,
        )
        self.title_lbl.pack(side="left", padx=(16, 6), pady=(6, 0))

        self.count_lbl = tk.Label(
            self.header,
            text="0",
            bg=self.t["pill"],
            fg=self.t["accent"],
            font=(self.font_text, 9, "bold"),
            padx=7,
            pady=1,
            cursor=drag_cursor,
        )
        self.count_lbl.pack(side="left", pady=(8, 0))

        # Close button
        self.close_btn = tk.Label(
            self.header,
            text="✕",
            bg=self.t["bg"],
            fg=self.t["muted"],
            font=(self.font_text, 11, "bold"),
            cursor="hand2",
        )
        self.close_btn.pack(side="right", padx=(5, 14), pady=(6, 0))
        self.close_btn.bind("<Button-1>", lambda e: self.root.destroy())
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.config(fg=self.t["danger"]))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.config(fg=self.t["muted"]))

        # Desktop / Pinned Mode Pill
        self.mode_btn = tk.Label(
            self.header,
            text="Desktop" if self.mode == "wallpaper" else "Pinned",
            bg=self.t["pill"],
            fg=self.t["muted"] if self.mode == "wallpaper" else self.t["accent"],
            font=(self.font_text, 9, "bold"),
            padx=8,
            pady=2,
            cursor="hand2",
        )
        self.mode_btn.pack(side="right", padx=4, pady=(7, 0))
        self.mode_btn.bind("<Button-1>", lambda e: self.toggle_mode())
        self.mode_btn.bind("<Enter>", lambda e: self.mode_btn.config(bg=self.t["pill_hover"]))
        self.mode_btn.bind("<Leave>", lambda e: self.mode_btn.config(bg=self.t["pill"]))

        # Clear Done Button
        self.clear_btn = tk.Label(
            self.header,
            text="Clear",
            bg=self.t["bg"],
            fg=self.t["done"],
            font=(self.font_text, 9, "bold"),
            cursor="hand2",
        )
        self.clear_btn.pack(side="right", padx=4, pady=(7, 0))
        self.clear_btn.bind("<Button-1>", lambda e: self.clear_done())
        self.clear_btn.bind("<Enter>", lambda e: self.clear_btn.config(fg=self.t["text"]))
        self.clear_btn.bind("<Leave>", lambda e: self.update_header_states())

        # Position Lock Toggle Icon
        self.lock_btn = tk.Canvas(
            self.header,
            width=16,
            height=16,
            bg=self.t["bg"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.draw_lock_icon()
        self.lock_btn.pack(side="right", padx=4, pady=(8, 0))
        self.lock_btn.bind("<Button-1>", lambda e: self.toggle_lock())

        # Theme Cycle Dot (Ocean / Graphite / Frost)
        self.theme_dot = tk.Canvas(
            self.header,
            width=14,
            height=14,
            bg=self.t["bg"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.theme_dot.create_oval(
            2, 2, 12, 12, fill=self.t["accent"], outline=self.t["muted"], width=1
        )
        self.theme_dot.pack(side="right", padx=4, pady=(9, 0))
        self.theme_dot.bind("<Button-1>", lambda e: self.cycle_theme())

        for w in (self.header, self.title_lbl, self.count_lbl):
            w.bind("<Button-1>", self.start_drag)
            w.bind("<B1-Motion>", self.do_drag)
            w.bind("<ButtonRelease-1>", self.stop_drag)

        # --- Rounded Pill Input Bar ---
        input_wrap = tk.Frame(self.root, bg=self.t["bg"], height=44)
        input_wrap.pack(fill="x", padx=14, pady=(2, 4))
        input_wrap.pack_propagate(False)

        inner_w = WIDTH - 28
        self.input_canvas = tk.Canvas(
            input_wrap,
            width=inner_w,
            height=40,
            bg=self.t["bg"],
            highlightthickness=0,
            bd=0,
        )
        self.input_canvas.pack(fill="both", expand=True)

        self.input_pill = draw_rounded_rect(
            self.input_canvas,
            1,
            1,
            inner_w - 2,
            38,
            12,
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
            font=(self.font_text, 11, "bold"),
        )
        self.entry.place(x=14, y=9, width=inner_w - 52, height=22)
        self.entry.bind("<Return>", lambda e: self.add_task())
        self.entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.entry.bind("<FocusOut>", self.on_entry_focus_out)
        self.set_placeholder()

        # Circular Add Button
        cx, cy = inner_w - 20, 19.5
        self.add_circle = self.input_canvas.create_oval(
            cx - 11, cy - 11, cx + 11, cy + 11, fill=self.t["accent"], outline=""
        )
        self.add_plus_h = self.input_canvas.create_line(
            cx - 4.5, cy, cx + 4.5, cy, fill="#FFFFFF", width=2.0, capstyle="round"
        )
        self.add_plus_v = self.input_canvas.create_line(
            cx, cy - 4.5, cx, cy + 4.5, fill="#FFFFFF", width=2.0, capstyle="round"
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
        self.list_container.pack(fill="both", expand=True, padx=14, pady=(2, 10))

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
        if len(self.tasks) > MAX_VISIBLE_ROWS:
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
            "x": 60,
            "y": 60,
            "mode": "wallpaper",
            "theme": "ocean",
            "locked": True,
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

        # Auto-size height around active tasks while anchored to saved (x, y)
        visible_rows = max(1, min(len(self.tasks), MAX_VISIBLE_ROWS))
        target_height = 108 + (visible_rows * ROW_HEIGHT)
        anchor_x = self.state.get("x", 60)
        anchor_y = self.state.get("y", 60)
        self.root.geometry(f"{WIDTH}x{target_height}+{anchor_x}+{anchor_y}")

        if not self.tasks:
            empty = tk.Label(
                self.rows_frame,
                text="All Clear",
                bg=self.t["bg"],
                fg=self.t["done"],
                font=(self.font_text, 11, "bold"),
                pady=10,
            )
            empty.pack(fill="x")
            return

        row_width = WIDTH - 28
        for idx, task in enumerate(self.tasks):
            row = tk.Canvas(
                self.rows_frame,
                width=row_width,
                height=ROW_HEIGHT,
                bg=self.t["bg"],
                highlightthickness=0,
                bd=0,
                cursor="hand2",
            )
            row.pack(fill="x")

            # Circular Apple-style checkbox
            if task["done"]:
                circle = row.create_oval(
                    6, 12, 25, 31, fill=self.t["accent"], outline=self.t["accent"]
                )
                row.create_line(
                    11.0,
                    21.8,
                    14.2,
                    25.0,
                    20.2,
                    18.2,
                    fill="#FFFFFF",
                    width=2.0,
                    capstyle="round",
                    joinstyle="round",
                )
            else:
                circle = row.create_oval(
                    6, 12, 25, 31, fill=self.t["bg"], outline=self.t["done"], width=1.8
                )

            display_text = task["text"]
            if len(display_text) > 27:
                display_text = display_text[:26] + "…"

            row.create_text(
                36,
                22,
                text=display_text,
                fill=self.t["done"] if task["done"] else self.t["text"],
                font=(self.font_text, 12, "bold"),
                anchor="w",
            )

            # Inset separator between rows
            if idx < len(self.tasks) - 1:
                row.create_line(
                    36, ROW_HEIGHT - 1, row_width - 4, ROW_HEIGHT - 1, fill=self.t["divider"]
                )

            # Hover-only delete button
            del_item = row.create_text(
                row_width - 10,
                22,
                text="✕",
                fill=self.t["bg"],
                font=(self.font_text, 10, "bold"),
            )

            def on_row_click(event, i=idx, rw=row_width):
                if event.x >= rw - 24:
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
                    d, fill=self.t["danger"] if event.x >= rw - 24 else self.t["muted"]
                )

            row.bind("<Button-1>", on_row_click)
            row.bind("<Enter>", on_row_enter)
            row.bind("<Leave>", on_row_leave)
            row.bind("<Motion>", on_row_motion)


if __name__ == "__main__":
    root = tk.Tk()
    app = AppleDesktopTodoApp(root)
    root.mainloop()