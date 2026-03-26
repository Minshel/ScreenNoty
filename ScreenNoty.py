import tkinter as tk
import keyboard
import json
import os
import threading
import time
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

SAVE_FILE = "notes_data.json"

class StickyNote:
    def __init__(self, x=100, y=100, width=250, height=270, color=None, text="", is_rolled=False):
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        self.colors = {"green": "#6fd262", "yellow": "#e6b905", "pink": "#454545"}
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
        self.btn_frame.place(relx=1.0, x=-110, y=8) 
        for c_code in self.colors.values():
            self.create_color_btn(c_code)

        self.close_button = tk.Label(self.top_bar, text="✕", bg=self.current_bg, fg="black", font=("Arial", 11, "bold"), cursor="hand2")
        self.close_button.place(relx=1.0, x=-25, y=4)
        self.close_button.bind("<Button-1>", self.destroy_note)

        self.text_area = tk.Text(self.root, bg=self.current_bg, fg="black", insertbackground="black", 
                                 font=("Segoe UI", 12), bd=0, padx=15, pady=5, highlightthickness=0, undo=True)
        
        self.text_area.tag_configure("bold", font=("Segoe UI", 12, "bold"))
        self.text_area.tag_configure("italic", font=("Segoe UI", 12, "italic"))
        self.text_area.tag_configure("underline", underline=True)
        self.text_area.tag_configure("strike", overstrike=True)

        if not self.is_rolled:
            self.text_area.pack(fill='both', expand=True)
        self.text_area.insert("1.0", text)

        self.resizer_frames = []
        self.setup_resizers()

        self.top_bar.bind("<Button-1>", self.start_move)
        self.top_bar.bind("<B1-Motion>", self.do_move)
        self.top_bar.bind("<Double-Button-1>", self.toggle_roll)
        
        self.text_area.bind("<KeyPress>", self.handle_shortcuts)
        self.text_area.bind("<KeyRelease>", lambda e: save_all_notes())
        self.text_area.bind("<Button-3>", self.show_format_menu)
        
        self.last_update = 0
        active_notes.append(self)

    def handle_shortcuts(self, event):
        if (event.state & 0x4):
            code = event.keycode
            if code == 67: self.text_area.event_generate("<<Copy>>"); return "break"
            elif code == 86: self.text_area.event_generate("<<Paste>>"); return "break"
            elif code == 88: self.text_area.event_generate("<<Cut>>"); return "break"
            elif code == 65: self.text_area.tag_add("sel", "1.0", "end"); return "break"
            elif code == 90:
                try: self.text_area.edit_undo()
                except: pass
                return "break"

    def show_format_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Bold", command=lambda: self.apply_tag("bold"))
        menu.add_command(label="Italic", command=lambda: self.apply_tag("italic"))
        menu.add_command(label="Underline", command=lambda: self.apply_tag("underline"))
        menu.add_command(label="Strike", command=lambda: self.apply_tag("strike"))
        menu.add_separator()
        menu.add_command(label="Clear", command=self.clear_tags)
        menu.tk_popup(event.x_root, event.y_root)

    def apply_tag(self, tag):
        try:
            sel_start, sel_end = self.text_area.index("sel.first"), self.text_area.index("sel.last")
            if tag in self.text_area.tag_names(sel_start): self.text_area.tag_remove(tag, sel_start, sel_end)
            else: self.text_area.tag_add(tag, sel_start, sel_end)
            save_all_notes()
        except: pass

    def clear_tags(self):
        try:
            for t in ["bold", "italic", "underline", "strike"]: self.text_area.tag_remove(t, "sel.first", "sel.last")
            save_all_notes()
        except: pass

    def setup_resizers(self):
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
            self.resizer_frames.append(f)

    def create_color_btn(self, color_code):
        btn = tk.Frame(self.btn_frame, bg=color_code, width=14, height=14, highlightbackground="black", highlightthickness=1, cursor="hand2")
        btn.pack(side='left', padx=2)
        btn.bind("<Button-1>", lambda e: self.change_color(color_code))

    def change_color(self, color):
        self.current_bg = color
        for w in [self.root, self.top_bar, self.btn_frame, self.close_button, self.text_area] + self.resizer_frames:
            w.configure(bg=color)
        save_all_notes()

    def start_move(self, event):
        self.x, self.y = event.x, event.y
        self.root.lift()

    def do_move(self, event):
        self.root.geometry(f"+{self.root.winfo_x() + event.x - self.x}+{self.root.winfo_y() + event.y - self.y}")

    def toggle_roll(self, event=None):
        if not self.is_rolled:
            self.full_height = self.root.winfo_height()
            self.text_area.pack_forget()
            self.root.geometry(f"{self.root.winfo_width()}x30")
        else:
            self.root.geometry(f"{self.root.winfo_width()}x{self.full_height}")
            self.text_area.pack(fill='both', expand=True)
        self.is_rolled = not self.is_rolled
        save_all_notes()

    def start_resize(self, event, side):
        if self.is_rolled: return
        self.side, self.sx, self.sy = side, event.x_root, event.y_root
        self.sw, self.sh = self.root.winfo_width(), self.root.winfo_height()
        self.ox, self.oy = self.root.winfo_x(), self.root.winfo_y()

    def do_resize(self, event):
        if self.is_rolled: return
        curr = time.time()
        if curr - self.last_update < 0.01: return
        self.last_update = curr
        dx, dy = event.x_root - self.sx, event.y_root - self.sy
        nw, nh, nx, ny = self.sw, self.sh, self.ox, self.oy
        if "e" in self.side: nw = max(150, self.sw + dx)
        if "s" in self.side: nh = max(100, self.sh + dy)
        if "w" in self.side:
            nw = max(150, self.sw - dx)
            if nw > 150: nx = self.ox + dx
        if "n" in self.side:
            nh = max(100, self.sh - dy)
            if nh > 100: ny = self.oy + dy
        self.root.geometry(f"{nw}x{nh}+{nx}+{ny}")

    def destroy_note(self, event=None):
        active_notes.remove(self)
        self.root.destroy()
        save_all_notes()

def save_all_notes():
    data = []
    for n in active_notes:
        try:
            data.append({"x": n.root.winfo_x(), "y": n.root.winfo_y(), "width": n.root.winfo_width(), 
                         "height": n.full_height, "color": n.current_bg, "text": n.text_area.get("1.0", "end-1c"), "is_rolled": n.is_rolled})
        except: pass
    with open(SAVE_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def load_notes():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            try:
                for n in json.load(f): StickyNote(**n)
            except: StickyNote()
    else: StickyNote()

def setup_tray():
    size = 64
    img = Image.new('RGB', (size, size), color='black')
    d = ImageDraw.Draw(img)
    d.line([(15, 15), (15, 49)], fill="white", width=5)
    d.line([(15, 15), (49, 49)], fill="white", width=5)
    d.line([(49, 15), (49, 49)], fill="white", width=5)
    icon = Icon("ScreenNoty", img, menu=Menu(MenuItem("Quit ScreenNoty", lambda i, item: [i.stop(), root.after(0, root.quit)])))
    icon.run()

active_notes = []
root = tk.Tk()
root.withdraw()
load_notes()

keyboard.add_hotkey('alt+n', lambda: root.after(0, StickyNote), suppress=False)

threading.Thread(target=setup_tray, daemon=True).start()
root.mainloop()