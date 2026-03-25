import tkinter as tk
import keyboard
import json
import os

SAVE_FILE = "notes_data.json"

class StickyNote:
    def __init__(self, x=100, y=100, width=250, height=270, color=None, text=""):
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        self.colors = {
            "green": "#e2f3e5",
            "yellow": "#fff9c4",
            "pink": "#fce4ec"
        }
        
        self.current_bg = color if color else self.colors["green"]
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(bg=self.current_bg)

        self.top_bar = tk.Frame(self.root, bg=self.current_bg, height=25)
        self.top_bar.pack(fill='x', side='top')

        self.close_button = tk.Label(
            self.top_bar, text="✕", bg=self.current_bg, fg="black",
            font=("Arial", 11, "bold"), cursor="hand2"
        )
        self.close_button.pack(side='right', padx=5)
        self.close_button.bind("<Button-1>", self.destroy_note)

        self.text_area = tk.Text(
            self.root, bg=self.current_bg, font=("Segoe UI", 12),
            bd=0, padx=15, pady=5, highlightthickness=0, undo=True
        )
        self.text_area.pack(fill='both', expand=True)
        self.text_area.insert("1.0", text)

        self.btn_frame = tk.Frame(self.root, bg=self.current_bg)
        self.btn_frame.place(relx=1.0, rely=1.0, anchor='se', x=-20, y=-5)

        for c_code in self.colors.values():
            self.create_color_btn(c_code)

        self.resizer = tk.Frame(self.root, bg=self.current_bg, cursor="size_nw_se", width=15, height=15)
        self.resizer.place(relx=1.0, rely=1.0, anchor='se')

        for widget in (self.text_area, self.top_bar, self.btn_frame):
            widget.bind("<Button-2>", self.start_move)
            widget.bind("<B2-Motion>", self.do_move)
            widget.bind("<ButtonRelease-2>", lambda e: save_all_notes())

        self.resizer.bind("<Button-1>", self.start_resize)
        self.resizer.bind("<B1-Motion>", self.do_resize)
        self.resizer.bind("<ButtonRelease-1>", lambda e: save_all_notes())

        self.text_area.bind("<Control-c>", lambda e: self.text_area.event_generate("<<Copy>>") or "break")
        self.text_area.bind("<Control-v>", lambda e: self.text_area.event_generate("<<Paste>>") or "break")
        self.text_area.bind("<Control-a>", lambda e: self.text_area.tag_add("sel", "1.0", "end") or "break")
        self.text_area.bind("<Control-x>", lambda e: self.text_area.event_generate("<<Cut>>") or "break")
        self.text_area.bind("<KeyRelease>", lambda e: save_all_notes())

        active_notes.append(self)

    def create_color_btn(self, color_code):
        btn = tk.Frame(self.btn_frame, bg=color_code, width=15, height=15, 
                       highlightbackground="black", highlightthickness=1, cursor="hand2")
        btn.pack(pady=2)
        btn.bind("<Button-1>", lambda e: self.change_color(color_code))

    def change_color(self, color):
        self.current_bg = color
        for w in [self.root, self.top_bar, self.text_area, self.btn_frame, self.close_button, self.resizer]:
            w.configure(bg=color)
        save_all_notes()

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        nx = self.root.winfo_x() + (event.x - self.x)
        ny = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{nx}+{ny}")

    def start_resize(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.start_w = self.root.winfo_width()
        self.start_h = self.root.winfo_height()

    def do_resize(self, event):
        nw = max(150, self.start_w + (event.x_root - self.start_x))
        nh = max(100, self.start_h + (event.y_root - self.start_y))
        self.root.geometry(f"{nw}x{nh}")

    def destroy_note(self, event):
        active_notes.remove(self)
        self.root.destroy()
        save_all_notes()

def save_all_notes():
    data = []
    for note in active_notes:
        data.append({
            "x": note.root.winfo_x(), "y": note.root.winfo_y(),
            "width": note.root.winfo_width(), "height": note.root.winfo_height(),
            "color": note.current_bg, "text": note.text_area.get("1.0", "end-1c")
        })
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_notes():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for n in data:
                    StickyNote(n['x'], n['y'], n.get('width', 250), n.get('height', 270), n['color'], n['text'])
            except:
                StickyNote()
    else:
        StickyNote()

active_notes = []
root = tk.Tk()
root.withdraw()
load_notes()
keyboard.add_hotkey('alt+n', lambda: StickyNote())
root.mainloop()