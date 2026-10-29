"""
languages.py  --  language support for Asik: English (default), Filipino, Kapampangan and Bisaya.

HOW IT WORKS
  * translations.py holds the translated texts:   "English text": (Filipino, Kapampangan, Bisaya)
  * install() teaches Tkinter to translate every label, button, tab title, window title,
    table heading and message box text just before it is shown. So the pages do NOT need
    to be changed: they keep writing English, and the person sees the chosen language.
  * Only texts that are in translations.py are changed. Names, posts, messages, prices and
    everything typed by users are never touched.
  * The choice is saved in language.txt (next to this file) so Asik remembers it.
  * The language is picked on the Login page (and on My Profile). English is the default.

USE
    import languages
    languages.install()                 # once, before the window is created (main.py does this)
    languages.set_language("fil")       # "en", "fil", "pam" or "ceb"; the page must be rebuilt after
    languages.tr("Save")                # translate one text yourself
"""

import os
import re
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

LANGUAGES = [("en", "English"), ("fil", "Filipino"), ("pam", "Kapampangan"), ("ceb", "Bisaya")]
_INDEX = {"fil": 0, "pam": 1, "ceb": 2}
_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "language.txt")

current = "en"
_installed = False
_cache = {}
_tables = {}        # per language: (exact, by_core, templates)

# leading symbols/emoji/spaces + the words + trailing punctuation
_SPLIT = re.compile(r"^([^A-Za-z0-9{“\"'(]*)(.*?)([\s.:!?…→▾▸»]*)$", re.S)
_HOLE = re.compile(r"\{(\d)\}")


# ------------------------------------------------------------------
# choosing and remembering the language
# ------------------------------------------------------------------
def load_saved():
    global current
    try:
        with open(_FILE, encoding="utf-8") as f:
            code = f.read().strip()
        if code in dict(LANGUAGES):
            current = code
    except OSError:
        pass


def set_language(code):
    """Switch language (the caller rebuilds the screen) and remember the choice."""
    global current
    if code not in dict(LANGUAGES):
        return
    current = code
    _cache.clear()
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            f.write(code)
    except OSError:
        pass


def language_name(code=None):
    return dict(LANGUAGES)[code or current]


# ------------------------------------------------------------------
# translating one text
# ------------------------------------------------------------------
def _core(text):
    m = _SPLIT.match(text)
    return m.group(1), m.group(2), m.group(3)


def _build(lang):
    from translations import TRANSLATIONS
    i = _INDEX[lang]
    exact, by_core, templates = {}, {}, []
    for en, row in TRANSLATIONS.items():
        tx = row[i]
        if not tx or tx == en:
            continue
        if _HOLE.search(en):                                   # a sentence with {0}, {1} ... inside
            literal = _HOLE.sub("", en)
            if not re.search(r"[A-Za-z]{2}", literal):
                continue
            parts = _HOLE.split(en)[::2]
            pattern = "(.*?)".join(re.escape(p) for p in parts)
            templates.append((len(literal), re.compile("^" + pattern + "$", re.S), _HOLE.findall(en), tx))
        else:
            exact[en] = tx
            _, c_en, _ = _core(en)
            _, c_tx, _ = _core(tx)
            if c_en and c_tx:
                by_core.setdefault(c_en, c_tx)
    templates.sort(key=lambda t: -t[0])
    return exact, by_core, templates


def tr(text):
    """Translate a text into the current language. Unknown texts come back unchanged."""
    if current == "en" or not isinstance(text, str) or len(text) < 2:
        return text
    hit = _cache.get(text)
    if hit is not None:
        return hit
    if current not in _tables:
        try:
            _tables[current] = _build(current)
        except Exception:
            _tables[current] = ({}, {}, [])
    exact, by_core, templates = _tables[current]
    result = exact.get(text)
    if result is None:
        pre, core, post = _core(text)
        if core in by_core:
            result = pre + by_core[core] + post
    if result is None and ("{" not in text):
        for _, regex, holes, tx in templates:
            m = regex.match(text)
            if m:
                groups = [g if g != "s" else "" for g in m.groups()]          # English plural "s"
                values = {}
                for hole, g in zip(holes, groups):
                    values[hole] = tr(g) if len(g) > 1 else g
                result = _HOLE.sub(lambda h: values.get(h.group(1), ""), tx)
                break
    if result is None:
        result = text
    if len(_cache) > 6000:
        _cache.clear()
    _cache[text] = result
    return result


# ------------------------------------------------------------------
# teach Tkinter to translate (done once)
# ------------------------------------------------------------------
def _wrap_init(cls):
    original = cls.__init__

    def init(self, *args, **kw):
        if isinstance(kw.get("text"), str):
            kw["text"] = tr(kw["text"])
        original(self, *args, **kw)
    cls.__init__ = init


def _wrap_method(cls, name, keys=("text",), positional=None):
    original = getattr(cls, name)

    def method(self, *args, **kw):
        for k in keys:
            if isinstance(kw.get(k), str):
                kw[k] = tr(kw[k])
        return original(self, *args, **kw)
    setattr(cls, name, method)


def _wrap_message_box(name):
    original = getattr(messagebox, name)

    def box(title=None, message=None, **options):
        return original(tr(title) if title else title, tr(message) if message else message, **options)
    setattr(messagebox, name, box)


def install():
    """Patch Tkinter so that texts are translated as widgets are made. Safe to call twice."""
    global _installed
    if _installed:
        return
    _installed = True
    load_saved()
    for cls in (tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton, tk.LabelFrame, tk.Menubutton,
                ttk.Label, ttk.Button, ttk.Checkbutton, ttk.Radiobutton, ttk.LabelFrame):
        _wrap_init(cls)

    original_configure = tk.Misc.configure

    def configure(self, cnf=None, **kw):
        if isinstance(kw.get("text"), str):
            kw["text"] = tr(kw["text"])
        return original_configure(self, cnf, **kw)
    tk.Misc.configure = configure
    tk.Misc.config = configure

    _wrap_method(tk.Canvas, "create_text")
    _wrap_method(tk.Canvas, "itemconfigure")
    tk.Canvas.itemconfig = tk.Canvas.itemconfigure
    _wrap_method(ttk.Notebook, "add")
    _wrap_method(ttk.Notebook, "tab")
    _wrap_method(ttk.Treeview, "heading")
    original_title = tk.Wm.wm_title

    def wm_title(self, string=None):
        return original_title(self, tr(string) if isinstance(string, str) else string)
    tk.Wm.wm_title = wm_title
    tk.Wm.title = wm_title

    for name in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askretrycancel",
                 "askquestion", "askyesnocancel"):
        _wrap_message_box(name)
    for name in ("askstring", "askinteger", "askfloat"):
        original = getattr(simpledialog, name)

        def ask(title, prompt, _original=original, **kw):
            return _original(tr(title), tr(prompt), **kw)
        setattr(simpledialog, name, ask)


# ------------------------------------------------------------------
# the language buttons (used on the Login page and on My Profile)
# ------------------------------------------------------------------
def language_picker(parent, bg, on_change, fg="#2B3A31", accent="#2F7A4A"):
    """A small row of buttons: English | Filipino | Kapampangan | Bisaya. on_change() rebuilds the screen."""
    box = tk.Frame(parent, bg=bg)
    tk.Label(box, text="Language", bg=bg, fg=fg, font=("Segoe UI", 9, "bold")).pack(anchor="w")
    row = tk.Frame(box, bg=bg)
    row.pack(anchor="w", pady=(3, 0))

    def pick(code):
        if code != current:
            set_language(code)
            on_change()
    for code, name in LANGUAGES:
        on = code == current
        tk.Button(row, text=name, command=lambda c=code: pick(c), relief="flat", bd=0, cursor="hand2",
                  font=("Segoe UI", 8, "bold" if on else "normal"), padx=7, pady=3,
                  bg=accent if on else "#E8EFE4", fg="#FFFFFF" if on else fg,
                  activebackground=accent, activeforeground="#FFFFFF").pack(side="left", padx=(0, 4))
    return box
