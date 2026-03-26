import tkinter as tk
import keyboard
import json
import os
import threading
import time
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

SAVE_FILE = "notes_data.json"
ICON_FILE = "app_icon.ico"

class StickyNote:
    def __init__(self, x=100, y=100, width=250, height=270, color=None, text="", is_rolled=False):
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        self.colors = {"green": "#e2f3e5", "yellow": "#fff9c4", "pink": "#fce4ec"}
        self.current_bg = color if color else self.colors["green"]
        self.full_height = height
        self.is_rolled = is_rolled
        
        h = 30 if self.is_rolled else self.full_height
        self.root.geometry(f"{width}x{h}+{x}+{y}")
        self.root.configure(bg=self.current_bg)

        self.top_bar = tk.Frame(self.root, bg=self.current_bg, height=30)
        self.top_bar.pack(fill='x', side='top')
        self.top_bar.pack_propagate(False)

        self.btn_frame = tk.Frame(self.top_bar, bg=self.current_bg)
        self.btn_frame.place(relx=1.0, x=-110, y=10) 
        for c_code in self.colors.values():
            self.create_color_btn(c_code)

        self.close_button = tk.Label(self.top_bar, text="✕", bg=self.current_bg, font=("Arial", 11, "bold"), cursor="hand2")
        self.close_button.place(relx=1.0, x=-25, y=4)
        self.close_button.bind("<Button-1>", self.destroy_note)

        self.text_area = tk.Text(self.root, bg=self.current_bg, font=("Segoe UI", 12), bd=0, padx=15, pady=5, highlightthickness=0, undo=True)
        if not self.is_rolled:
            self.text_area.pack(fill='both', expand=True)
        self.text_area.insert("1.0", text)

        self.setup_resizers()

        self.top_bar.bind("<Button-1>", self.start_move)
        self.top_bar.bind("<B1-Motion>", self.do_move)
        self.top_bar.bind("<Double-Button-1>", self.toggle_roll)
        
        self.text_area.bind("<Key>", self.handle_shortcuts)
        self.text_area.bind("<KeyRelease>", lambda e: save_all_notes())
        
        self.last_update = 0 
        active_notes.append(self)

    def toggle_roll(self, event=None):
        if not self.is_rolled:
            self.full_height = self.root.winfo_height()
            self.text_area.pack_forget()
            self.root.geometry(f"{self.root.winfo_width()}x30")
            self.is_rolled = True
        else:
            self.root.geometry(f"{self.root.winfo_width()}x{self.full_height}")
            self.text_area.pack(fill='both', expand=True)
            self.is_rolled = False
        save_all_notes()

    def setup_resizers(self):
        self.resizer_frames = []
        bw, cw = 5, 10
        conf = {"n": ("size_ns", 0, 0, 1, bw, "nw"), "s": ("size_ns", 0, 1, 1, bw, "sw"),
                "e": ("size_we", 1, 0, bw, 1, "ne"), "w": ("size_we", 0, 0, bw, 1, "nw"),
                "nw": ("size_nw_se", 0, 0, cw, cw, "nw"), "ne": ("size_ne_sw", 1, 0, cw, cw, "ne"),
                "sw": ("size_ne_sw", 0, 1, cw, cw, "sw"), "se": ("size_nw_se", 1, 1, cw, cw, "se")}
        for side, (cursor, rx, ry, w, h, anc) in conf.items():
            f = tk.Frame(self.root, bg=self.current_bg, cursor=cursor)
            if w == 1: f.place(relx=rx, rely=ry, relwidth=1, height=h, anchor=anc)
            elif h == 1: f.place(relx=rx, rely=ry, relheight=1, width=w, anchor=anc)
            else: f.place(relx=rx, rely=ry, width=w, height=h, anchor=anc)
            f.bind("<Button-1>", lambda e, s=side: self.start_resize(e, s))
            f.bind("<B1-Motion>", self.do_resize)
            f.bind("<ButtonRelease-1>", lambda e: save_all_notes())
            self.resizer_frames.append(f)

    def handle_shortcuts(self, event):
        if (event.state & 0x4):
            code = event.keycode
            if code == 67: self.text_area.event_generate("<<Copy>>"); return "break"
            elif code == 86: self.text_area.event_generate("<<Paste>>"); return "break"
            elif code == 70: open_search(); return "break"
            elif code == 65: self.text_area.tag_add("sel", "1.0", "end"); return "break"
            elif code == 90:
                try: self.text_area.edit_undo()
                except: pass
                return "break"

    def create_color_btn(self, color_code):
        btn = tk.Frame(self.btn_frame, bg=color_code, width=12, height=12, highlightbackground="black", highlightthickness=1, cursor="hand2")
        btn.pack(side='left', padx=2)
        btn.bind("<Button-1>", lambda e: self.change_color(color_code))

    def change_color(self, color):
        self.current_bg = color
        for w in [self.root, self.top_bar, self.text_area, self.btn_frame, self.close_button] + self.resizer_frames:
            w.configure(bg=color)
        save_all_notes()

    def start_move(self, event):
        self.x, self.y = event.x, event.y
        self.root.lift()

    def do_move(self, event):
        nx = self.root.winfo_x() + event.x - self.x
        ny = self.root.winfo_y() + event.y - self.y
        self.root.geometry(f"+{nx}+{ny}")

    def start_resize(self, event, side):
        if self.is_rolled and any(x in side for x in "ns"): return
        self.side = side
        self.start_x_root, self.start_y_root = event.x_root, event.y_root
        self.start_x, self.start_y = self.root.winfo_x(), self.root.winfo_y()
        self.start_w, self.start_h = self.root.winfo_width(), self.root.winfo_height()

    def do_resize(self, event):
        curr_time = time.time()
        if curr_time - self.last_update < 0.012: return 
        self.last_update = curr_time
        dx, dy = event.x_root - self.start_x_root, event.y_root - self.start_y_root
        nw, nh, nx, ny = self.start_w, self.start_h, self.start_x, self.start_y
        if "e" in self.side: nw = max(150, self.start_w + dx)
        if "s" in self.side: nh = max(100, self.start_h + dy)
        if "w" in self.side:
            nw = max(150, self.start_w - dx)
            if nw > 150: nx = self.start_x + dx
        if "n" in self.side:
            nh = max(100, self.start_h - dy)
            if nh > 100: ny = self.start_y + dy
        self.root.geometry(f"{nw}x{nh}+{nx}+{ny}")
        self.root.update_idletasks()

    def destroy_note(self, event=None):
        if self in active_notes: active_notes.remove(self)
        self.root.destroy()
        save_all_notes()

def open_search():
    search_win = tk.Toplevel()
    search_win.title("Поиск")
    search_win.attributes("-topmost", True)
    search_win.geometry("200x80")
    ent = tk.Entry(search_win)
    ent.pack(pady=10, padx=10, fill='x')
    ent.focus_set()
    def do_find():
        query = ent.get().lower()
        for n in active_notes:
            if query in n.text_area.get("1.0", "end").lower():
                n.root.lift()
                n.text_area.tag_add("sel", "1.0", "end")
    ent.bind("<Return>", lambda e: [do_find(), search_win.destroy()])

def save_all_notes():
    data = []
    for n in active_notes:
        try:
            data.append({
                "x": n.root.winfo_x(), "y": n.root.winfo_y(), 
                "width": n.root.winfo_width(), "height": n.full_height, 
                "color": n.current_bg, "text": n.text_area.get("1.0", "end-1c"),
                "is_rolled": n.is_rolled
            })
        except: pass
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_notes():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not data: StickyNote()
                else:
                    for n in data: StickyNote(n['x'], n['y'], n.get('width', 250), n.get('height', 270), 
                                              n['color'], n.get('text', ""), n.get('is_rolled', False))
            except: StickyNote()
    else: StickyNote()

def quit_app(icon, item):
    save_all_notes()
    icon.stop()
    root.after(0, root.quit)

def setup_tray():
    if os.path.exists(ICON_FILE):
        img = Image.open(ICON_FILE)
    else:
        img = Image.new('RGB', (64, 64), color='#2e7d32')
        d = ImageDraw.Draw(img)
        d.rectangle([5, 5, 59, 59], fill="#43a047", outline="white", width=2)
        d.text((22, 20), "N", fill="white")
    
    icon = Icon("Notes", img, menu=Menu(MenuItem("Выход", quit_app)))
    icon.run()

active_notes = []
root = tk.Tk()
root.withdraw()
load_notes()
keyboard.add_hotkey('alt+n', lambda: root.after(0, StickyNote))
threading.Thread(target=setup_tray, daemon=True).start()
root.mainloop()