"""
theme.py  --  Colours, fonts and reusable widgets for every Asik page.

The look (green farm colours, soft pastel cards, dark-blue sidebar) is
taken from the original FarmMate design you sent, so all pages match.

Reusable pieces defined here:
    C ................ colour palette
    label / button / card .. styled tkinter widgets
    page_header ...... big title + subtitle at the top of a page
    Scrollable ....... a frame that scrolls with the mouse wheel
    LocationPicker ... Region -> Province -> Municipality -> Barangay drop-downs
    SearchBar ........ search box with a clickable "Search" button
    load_logo ........ loads asik_logo.png (falls back to a leaf emoji)
    avatar ........... profile photo label (reads from disk every call)
    clear_image_caches clears cached images (call on logout)
    peso ............. formats numbers as Philippine peso
"""

import os
import tkinter as tk
from tkinter import ttk

import config
import database as db

# ---------------- Colour palette (same as the original design) ----------------
C = {
    # page + cards (soft farm greens and cream, as in the new design)
    "bg": "#E8F2DC", "white": "#FFFFFF", "dark": "#1F4A32",
    "green": "#2F7A4A", "green_dark": "#1F5A38", "mint": "#DDF0DA",
    "blue": "#DCEBFF", "blue_dark": "#3868B7",
    "yellow": "#FFF0C5", "yellow_dark": "#A87312",
    "purple": "#EDE3FF", "purple_dark": "#7752B5",
    "pink": "#FFE3E6", "pink_dark": "#BD5267",
    "orange": "#FFE8D6", "orange_dark": "#B66A31",
    "text": "#2A4435", "muted": "#6E8575", "border": "#D5E4C4",
    "red": "#C44747", "cream": "#FDFBEF",
    # sidebar: light green with a dark-green "pill" for the active page
    "sidebar": "#D9EBC6", "sidebar_hover": "#C8E0B0",
    "sidebar_active": "#2F6B47", "sidebar_text": "#1F4D33",
    "sidebar_ink": "#1F4A32", "sidebar_muted": "#4F7A5A",
    "character_bg": "#CFE5B9",
}

FONT = "Segoe UI"

# True = the scroll bar is always visible.  False = it appears only when the person scrolls or moves
# the pointer to the right edge, then hides again (the mouse wheel and touchpad always work).
SHOW_SCROLLBAR = False


def peso(amount):
    """Format a number as Philippine peso, e.g. 1234 -> ₱1,234"""
    amount = float(amount)
    return f"₱{amount:,.0f}" if amount == int(amount) else f"₱{amount:,.2f}"


def setup_styles():
    """Style the ttk widgets (tables, drop-downs) once at start-up."""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background=C["white"], fieldbackground=C["white"],
                    foreground=C["text"], rowheight=32, font=(FONT, 10))
    style.configure("Treeview.Heading", background=C["blue"], foreground=C["dark"],
                    font=(FONT, 10, "bold"), padding=8)
    style.configure("TCombobox", padding=5)
    # Turning the mouse wheel over ANY drop-down must scroll the page, not change the choice.
    root = tk._default_root
    if root is not None:
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            root.bind_class("TCombobox", seq, _combobox_wheel)


def _combobox_wheel(event):
    step = wheel_step(event)
    w = event.widget.master
    while w is not None:
        if isinstance(w, tk.Canvas):
            w.yview_scroll(step, "units")
            break
        w = getattr(w, "master", None)
    return "break"


# ---------------- Scrolling helpers (mouse wheel, touchpad, arrow keys) ----------------
_wheel_acc = 0.0


def wheel_step(event):
    """
    Units to scroll for a wheel event. A mouse wheel sends +-120 per click, but a
    laptop touchpad sends many small values (like 8 or 15). Rounding each one to
    zero made touchpads do nothing, so the small values are added up here.
    """
    global _wheel_acc
    if getattr(event, "num", 0) == 4:
        return -1
    if getattr(event, "num", 0) == 5:
        return 1
    _wheel_acc += -event.delta / 120.0
    n = int(_wheel_acc)
    _wheel_acc -= n
    return n


_TYPING = ("Text", "Entry", "TEntry", "TCombobox", "Listbox", "Treeview", "Spinbox",
           "TSpinbox", "Scale", "TScale")


def key_scroll(canvas, event):
    """Up/Down/PageUp/PageDown/Home/End scroll the canvas (unless the user is typing)."""
    try:
        if event.widget.winfo_class() in _TYPING:
            return
        if event.widget.winfo_toplevel() is not canvas.winfo_toplevel():
            return
        k = event.keysym
        if k == "Up":
            canvas.yview_scroll(-2, "units")
        elif k == "Down":
            canvas.yview_scroll(2, "units")
        elif k == "Prior":
            canvas.yview_scroll(-1, "pages")
        elif k == "Next":
            canvas.yview_scroll(1, "pages")
        elif k == "Home":
            canvas.yview_moveto(0)
        elif k == "End":
            canvas.yview_moveto(1)
    except tk.TclError:
        pass


SCROLL_KEYS = ("<Up>", "<Down>", "<Prior>", "<Next>", "<Home>", "<End>")


def bind_scroll_keys(owner, canvas):
    for k in SCROLL_KEYS:
        owner.bind_all(k, lambda e, c=canvas: key_scroll(c, e))


def unbind_scroll_keys(owner):
    for k in SCROLL_KEYS:
        try:
            owner.unbind_all(k)
        except tk.TclError:
            pass


def join_address(street, barangay):
    """Street and barangay are stored together in the one address column."""
    return ", ".join(x for x in ((street or "").strip(), (barangay or "").strip()) if x)


def split_address(address, barangays):
    """Split a saved 'street, barangay' text back into (street, barangay)."""
    address = (address or "").strip()
    last = address.rsplit(",", 1)[-1].strip()
    if last and last in set(barangays):
        street = address[: len(address) - len(last)].rstrip(" ,")
        return street, last
    return address, ""


# ---------------- Basic styled widgets ----------------
def label(parent, text, size=10, fg=None, bg=None, bold=False, **kw):
    """A tk.Label with the app font and default colours."""
    return tk.Label(parent, text=text,
                    font=(FONT, size, "bold" if bold else "normal"),
                    fg=fg or C["text"], bg=bg or C["bg"], **kw)


def button(parent, text, command, bg=None, fg=None, size=10, **kw):
    """A flat button that changes colour when the mouse hovers over it."""
    hover = kw.pop("hover_color", C["green_dark"])
    normal = bg or C["green"]
    padx = kw.pop("padx", 13)
    pady = kw.pop("pady", 9)
    b = tk.Button(parent, text=text, command=command,
                  font=(FONT, size, "bold"), bg=normal, fg=fg or C["white"],
                  activebackground=hover, activeforeground=C["white"],
                  relief="flat", bd=0, cursor="hand2", padx=padx, pady=pady, **kw)
    b.bind("<Enter>", lambda e: b.configure(bg=hover))
    b.bind("<Leave>", lambda e: b.configure(bg=normal))
    return b


def card(parent, color=None):
    """A white box with a thin border."""
    return tk.Frame(parent, bg=color or C["white"],
                    highlightbackground=C["border"], highlightthickness=1)


def entry(parent, textvariable=None, width=None, show=None):
    """A bordered text box."""
    kw = {"width": width} if width else {}
    return tk.Entry(parent, textvariable=textvariable, font=(FONT, 10),
                    relief="solid", bd=1, show=show, **kw)


def field(parent, caption, bg=None):
    """Small bold caption above an input (used in forms)."""
    label(parent, caption.upper(), 8, C["dark"], bg or C["white"], True
          ).pack(anchor="w", pady=(10, 4))


def page_header(parent, title, subtitle, accent=None):
    """Big page title + grey subtitle. Returns the header frame."""
    h = tk.Frame(parent, bg=C["bg"])
    h.pack(fill="x", padx=28, pady=(12, 8))
    label(h, title, 20, accent or C["dark"], C["bg"], True).pack(anchor="w")
    label(h, subtitle, 10, C["muted"], C["bg"]).pack(anchor="w", pady=(4, 0))
    return h


def clear(widget):
    """Remove everything inside a widget."""
    for child in widget.winfo_children():
        child.destroy()


# ---------------- Image caches (safe to clear on logout) ----------------
_logo_cache = {}


def clear_image_caches():
    """Drop every cached image. Call this on logout so photos never bleed
    from one user session into another."""
    _logo_cache.clear()


# ---------------- Logo ----------------
def load_logo(height):
    """
    Return a PhotoImage of asik_logo.png scaled to `height` pixels,
    or None if the picture is missing (pages then show a leaf emoji).
    Pillow gives the best quality; without it tkinter's own resize is used.
    """
    if height in _logo_cache:
        return _logo_cache[height]
    img = None
    if os.path.exists(config.LOGO_FILE):
        try:
            from PIL import Image, ImageTk
            pic = Image.open(config.LOGO_FILE).convert("RGBA")
            w = int(pic.width * height / pic.height)
            img = ImageTk.PhotoImage(pic.resize((w, height), Image.LANCZOS))
        except ImportError:
            try:
                raw = tk.PhotoImage(file=config.LOGO_FILE)
                factor = max(1, raw.height() // height)
                img = raw.subsample(factor, factor)
            except tk.TclError:
                img = None
        except Exception:
            img = None
    _logo_cache[height] = img
    return img


def logo_widget(parent, height, bg, fallback_size=30):
    """A label showing the logo (or a leaf emoji if the file is missing)."""
    img = load_logo(height)
    if img:
        lbl = tk.Label(parent, image=img, bg=bg)
        lbl.image = img                      # keep a reference so it is not erased
        return lbl
    return label(parent, "🌿", fallback_size, C["white"], bg)


def avatar(parent, photo_path, size, bg, emoji_size=None):
    """
    Profile picture label. Reads the photo from disk on EVERY call, so a
    stale image from a previous session can never be shown.
    Falls back to a 👤 emoji when there is no photo or the file is missing.
    JPG/PNG/GIF all work when Pillow is installed (pip install pillow);
    without Pillow only PNG and GIF are supported.
    """
    img = None
    if photo_path and os.path.exists(photo_path):
        try:
            from PIL import Image, ImageTk
            pic = Image.open(photo_path).convert("RGB")
            # crop to a centred square, then resize
            side = min(pic.size)
            left, top = (pic.width - side) // 2, (pic.height - side) // 2
            pic = pic.crop((left, top, left + side, top + side)).resize((size, size))
            img = ImageTk.PhotoImage(pic)
        except ImportError:
            try:
                raw = tk.PhotoImage(file=photo_path)
                factor = max(1, max(raw.width(), raw.height()) // size)
                img = raw.subsample(factor, factor)
            except tk.TclError:
                img = None
        except Exception:
            img = None
    if img:
        lbl = tk.Label(parent, image=img, bg=bg)
        lbl.image = img                      # required: keep a reference
        return lbl
    return label(parent, "👤", emoji_size or max(14, size // 2), C["muted"], bg)


# ---------------- Scrollable area ----------------

def autohide_scrollbar(canvas, bar):
    """Scroll bar that stays out of the way: it is hidden until the person scrolls (mouse wheel,
    touchpad, dragging) or moves the pointer to the right edge of the area, then it fades out again
    after a moment.  It floats over the right edge, so showing or hiding it never moves the page.
    Set SHOW_SCROLLBAR = True to keep a normal always-visible bar instead."""
    st = {"job": None, "last": None, "over": False}

    def hide():
        st["job"] = None
        if not st["over"]:
            bar.place_forget()
        else:
            st["job"] = canvas.after(1200, hide)

    def show():
        bar.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        bar.lift()
        if st["job"]:
            canvas.after_cancel(st["job"])
        st["job"] = canvas.after(1200, hide)

    def on_set(lo, hi):
        bar.set(lo, hi)
        if float(lo) <= 0 and float(hi) >= 1:      # everything fits: nothing to scroll
            bar.place_forget()
        elif st["last"] is not None and st["last"] != (lo, hi):
            show()
        st["last"] = (lo, hi)

    def on_motion(e):
        if e.x >= canvas.winfo_width() - 30 and not (float(canvas.yview()[0]) <= 0 and float(canvas.yview()[1]) >= 1):
            show()
    canvas.configure(yscrollcommand=on_set)
    canvas.bind("<Motion>", on_motion, add="+")
    bar.bind("<Enter>", lambda e: st.update(over=True))
    bar.bind("<Leave>", lambda e: st.update(over=False))


class Scrollable(tk.Frame):
    """
    A frame whose content scrolls vertically.
    Put widgets inside `self.inner`.
    """

    def __init__(self, parent, bg=None):
        super().__init__(parent, bg=bg or C["bg"])
        self.canvas = tk.Canvas(self, bg=bg or C["bg"], highlightthickness=0, height=260)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg or C["bg"])
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        # keep scroll region and inner width in sync with the canvas size
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))
        self.canvas.pack(side="left", fill="both", expand=True)
        if SHOW_SCROLLBAR:
            self.canvas.configure(yscrollcommand=bar.set)
            bar.pack(side="right", fill="y")
        else:
            autohide_scrollbar(self.canvas, bar)
        # mouse-wheel scrolling while the pointer is over this area
        def _on():
            self.canvas.bind_all("<MouseWheel>", self._wheel)
            self.canvas.bind_all("<Button-4>", self._wheel)
            self.canvas.bind_all("<Button-5>", self._wheel)
            bind_scroll_keys(self.canvas, self.canvas)

        def _off():
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.canvas.unbind_all(seq)
            unbind_scroll_keys(self.canvas)
        self.canvas.bind("<Enter>", lambda e: _on())
        self.canvas.bind("<Leave>", lambda e: _off())

    def _wheel(self, event):
        self.canvas.yview_scroll(wheel_step(event), "units")


# ---------------- Region > Province > Municipality > Barangay ----------------
class LocationPicker(tk.Frame):
    """
    Four linked drop-downs:
        Region  ->  Province  ->  Municipality  ->  Barangay

    Picking a Region loads its Provinces.
    Picking a Province loads its Municipalities.
    Picking a Municipality loads its Barangays (from the `barangays` table).

    all_option=True  -> adds "All ..." entries (used for FILTERS).
    all_option=False -> real choices only (used for FORMS).
    on_change(region, province, municipality, barangay) is called after each change.
    show_barangay=False hides the 4th dropdown (useful for filter panels).
    """

    def __init__(self, parent, all_option=False, on_change=None, bg=None,
                 horizontal=False, show_barangay=True):
        super().__init__(parent, bg=bg or C["white"])
        self.all_option = all_option
        self.on_change = on_change
        self.show_barangay = show_barangay
        bg = bg or C["white"]
        self.region_var = tk.StringVar()
        self.province_var = tk.StringVar()
        self.muni_var = tk.StringVar()
        self.barangay_var = tk.StringVar()

        def make(caption, var):
            box = tk.Frame(self, bg=bg)
            label(box, caption, 8, C["dark"], bg, True).pack(anchor="w")
            cb = ttk.Combobox(box, textvariable=var, state="readonly", width=28)
            cb.pack(fill="x", pady=(2, 6))
            # A ttk Combobox changes its value when the mouse wheel turns over it,
            # which silently changed (and reset) the address while scrolling the page.
            # Block that and scroll the surrounding page instead.
            cb.bind("<MouseWheel>", self._scroll_page_instead)
            cb.bind("<Button-4>", self._scroll_page_instead)
            cb.bind("<Button-5>", self._scroll_page_instead)
            return box, cb

        b1, self.region_cb = make("REGION", self.region_var)
        b2, self.province_cb = make("PROVINCE", self.province_var)
        b3, self.muni_cb = make("MUNICIPALITY / CITY", self.muni_var)
        b4, self.barangay_cb = make("BARANGAY", self.barangay_var)

        boxes = (b1, b2, b3, b4) if show_barangay else (b1, b2, b3)
        for i, b in enumerate(boxes):
            if horizontal:
                b.grid(row=0, column=i, padx=(0, 10), sticky="ew")
                self.columnconfigure(i, weight=1)
            else:
                b.pack(fill="x")

        prefix = ["All Regions"] if all_option else []
        self.region_cb["values"] = prefix + db.get_regions()
        self.region_var.set("All Regions" if all_option else "")
        self._reset_province()

        self.region_cb.bind("<<ComboboxSelected>>", self._region_picked)
        self.province_cb.bind("<<ComboboxSelected>>", self._province_picked)
        self.muni_cb.bind("<<ComboboxSelected>>", self._municipality_picked)
        self.barangay_cb.bind("<<ComboboxSelected>>", lambda e: self._notify())

    # -- internal helpers
    def _scroll_page_instead(self, event):
        """Mouse wheel over a drop-down: scroll the page, never change the choice."""
        step = wheel_step(event)
        w = self.master
        while w is not None:
            if isinstance(w, tk.Canvas):
                w.yview_scroll(step, "units")
                break
            w = getattr(w, "master", None)
        return "break"

    def _reset_province(self):
        self.province_cb["values"] = ["All Provinces"] if self.all_option else []
        self.province_var.set("All Provinces" if self.all_option else "")
        self._reset_muni()

    def _reset_muni(self):
        self.muni_cb["values"] = ["All Municipalities"] if self.all_option else []
        self.muni_var.set("All Municipalities" if self.all_option else "")
        self._reset_barangay()

    def _reset_barangay(self):
        if not self.show_barangay:
            return
        self.barangay_cb["values"] = ["All Barangays"] if self.all_option else []
        self.barangay_var.set("All Barangays" if self.all_option else "")

    def _region_picked(self, _e=None):
        region = self.region_var.get()
        if region.startswith("All"):
            self._reset_province()
        else:
            provs = db.get_provinces(region)
            self.province_cb["values"] = (["All Provinces"] if self.all_option else []) + provs
            self.province_var.set("All Provinces" if self.all_option else "")
            self._reset_muni()
        self._notify()

    def _province_picked(self, _e=None):
        prov = self.province_var.get()
        if prov.startswith("All"):
            self._reset_muni()
        else:
            munis = db.get_municipalities(prov)
            self.muni_cb["values"] = (["All Municipalities"] if self.all_option else []) + munis
            self.muni_var.set("All Municipalities" if self.all_option else "")
            self._reset_barangay()
        self._notify()

    def _municipality_picked(self, _e=None):
        """Called when the user picks a municipality -> load its barangays."""
        if not self.show_barangay:
            self._notify()
            return
        muni = self.muni_var.get()
        if muni.startswith("All") or not muni:
            self._reset_barangay()
        else:
            prov = self.province_var.get()
            brgys = db.get_barangays(muni, prov if prov and not prov.startswith("All") else None)
            self.barangay_cb["values"] = (["All Barangays"] if self.all_option else []) + brgys
            self.barangay_var.set("All Barangays" if self.all_option else "")
        self._notify()

    def _notify(self):
        if self.on_change:
            self.on_change(*self.get())

    # -- public API
    def get(self):
        """Return (region, province, municipality, barangay); '' means 'All'."""
        vals = []
        for var in (self.region_var, self.province_var, self.muni_var, self.barangay_var):
            v = var.get()
            vals.append("" if v.startswith("All") else v)
        return tuple(vals)

    def set(self, region="", province="", municipality="", barangay=""):
        """Fill the drop-downs (used for autofill and editing)."""
        if region:
            self.region_var.set(region)
            self._region_picked()
            if province:
                self.province_var.set(province)
                self._province_picked()
                if municipality:
                    self.muni_var.set(municipality)
                    self._municipality_picked()
                    if barangay and self.show_barangay:
                        self.barangay_var.set(barangay)
        else:
            self.reset()

    def reset(self):
        """Back to the empty/'All' state."""
        self.region_var.set("All Regions" if self.all_option else "")
        self._reset_province()


# ---------------- Search bar with a clickable button ----------------
class SearchBar(tk.Frame):
    """
    A search box + a green "Search" button + a "Clear" button.
    Pressing Enter also searches. `command` is called with no arguments;
    read the text with `.text()`.
    """

    def __init__(self, parent, command, placeholder="Search...", bg=None):
        super().__init__(parent, bg=bg or C["bg"])
        self.var = tk.StringVar()
        self.command = command
        box = tk.Frame(self, bg=C["white"], highlightbackground=C["border"],
                       highlightthickness=1)
        # the buttons are packed FIRST (on the right) so a narrow window or a long translation
        # shrinks the search box, never the buttons
        button(self, "Clear", self.clear, bg=C["muted"], size=10,
               hover_color=C["dark"]).pack(side="right", padx=(6, 0))
        button(self, "Search", command, size=10).pack(side="right", padx=(8, 0))
        box.pack(side="left", fill="x", expand=True)
        label(box, "🔍", 12, C["green"], C["white"]).pack(side="left", padx=8)
        self.entry = tk.Entry(box, textvariable=self.var, font=(FONT, 10),
                              bd=0, bg=C["white"], width=8)
        self.entry.pack(side="left", fill="x", expand=True, ipady=9)
        self.entry.bind("<Return>", lambda e: command())
        self.placeholder = placeholder
        self._show_placeholder()
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", lambda e: self._show_placeholder())

    def _show_placeholder(self):
        if not self.var.get():
            self.entry.insert(0, self.placeholder)
            self.entry.configure(fg=C["muted"])

    def _focus_in(self, _e):
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, "end")
            self.entry.configure(fg=C["text"])

    def text(self):
        """The typed search text ('' if only the placeholder is showing)."""
        t = self.var.get().strip()
        return "" if t == self.placeholder else t

    def clear(self):
        self.entry.delete(0, "end")
        self._show_placeholder()
        self.command()