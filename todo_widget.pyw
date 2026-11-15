import json
import os
import tkinter as tk

DATA_FILE = os.path.join(os.path.expanduser("~"), "desktop_todos.json")

# Colors (Sleek Dark Theme)
BG_COLOR = "#1e1e24"
HEADER_BG = "#282830"
ACCENT = "#4cc9f0"
TEXT_COLOR = "#f1f1f1"
DONE_COLOR = "#6c7086"
BTN_HOVER = "#383842"


class DesktopTodoApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Desktop To-Do")
        self.root.geometry("300x400+50+50")
        self.root.configure(bg=BG_COLOR)
        self.root.overrideredirect(True)  # Removes standard title bar

        self.on_top = True
        self.root.attributes("-topmost", self.on_top)
        self.root.attributes("-alpha", 0.95)  # Slight transparency

        self.tasks = self.load_tasks()
        self._drag_x = 0
        self._drag_y = 0

        self.build_ui()
        self.render_tasks()

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

        # Close button
        close_btn = tk.Button(
            header,
            text="✕",
            bg=HEADER_BG,
            fg=TEXT_COLOR,
            bd=0,
            font=("Segoe UI", 10),
            activebackground="#e63946",
            activeforeground="white",
            command=self.root.destroy,
            cursor="hand2",
        )
        close_btn.pack(side="right", padx=6)

        # Always-on-top toggle button
        self.pin_btn = tk.Button(
            header,
            text="Top: ON",
            bg=HEADER_BG,
            fg=ACCENT,
            bd=0,
            font=("Segoe UI", 8, "bold"),
            activebackground=BTN_HOVER,
            activeforeground=ACCENT,
            command=self.toggle_top,
            cursor="hand2",
        )
        self.pin_btn.pack(side="right", padx=6)

        # Bind drag events to header and title
        for widget in (header, title):
            widget.bind("<Button-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.do_drag)

        # --- Task Input ---
        input_frame = tk.Frame(self.root, bg=BG_COLOR, pady=10, padx=10)
        input_frame.pack(fill="x")

        self.entry = tk.Entry(
            input_frame,
            bg=HEADER_BG,
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
        self.list_frame = tk.Frame(self.root, bg=BG_COLOR, padx=10)
        self.list_frame.pack(fill="both", expand=True)

    def start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def toggle_top(self):
        self.on_top = not self.on_top
        self.root.attributes("-topmost", self.on_top)
        self.pin_btn.config(
            text=f"Top: {'ON' if self.on_top else 'OFF'}",
            fg=ACCENT if self.on_top else DONE_COLOR,
        )

    def load_tasks(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save_tasks(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, indent=2)

    def add_task(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.tasks.append({"text": text, "done": False})
        self.entry.delete(0, tk.END)
        self.save_tasks()
        self.render_tasks()

    def toggle_task(self, index):
        self.tasks[index]["done"] = not self.tasks[index]["done"]
        self.save_tasks()
        self.render_tasks()

    def delete_task(self, index):
        self.tasks.pop(index)
        self.save_tasks()
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
    app = DesktopTodoApp(root)
    root.mainloop()