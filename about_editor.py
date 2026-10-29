"""
about_editor.py  --  the ADMIN-ONLY window that edits the whole About page.

Opened from the About page with the "✏ Edit this page" button (only shown to
administrators). It has six tabs:
    Page text      the headline, section titles, intro texts and the rules notice
    Info cards     add / edit / delete / re-order the cards (Mission, Rental...)
    Guidelines     add / edit / delete / re-order the community guidelines
    Developers     the team: name, role, wording about them and their PHOTO
    Announcement   publish a message at the top of the page (or remove it)
    Suggestions    read what users suggested (improvements and new features), mark read / done
Every change is saved to MySQL (see about_data.py) and the About page behind
this window redraws at once, so everybody sees the new version.
"""

import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import database as db
import emoji_picker
import theme
from about_data import get_settings, remove_photo_file, round_photo, set_setting, store_photo
from theme import C


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def make_input(parent, caption, tall=False):
    """A labelled one-line Entry (or a taller Text). Returns a (get, set) pair."""
    theme.field(parent, caption)
    icon = "icon" in caption.lower()              # an "Icon" field holds ONE emoji: picking replaces it
    if tall:
        box = tk.Text(parent, height=tall if isinstance(tall, int) else 5, font=(theme.FONT, 10),
                      relief="solid", bd=1, wrap="word")
        box.pack(fill="x")
        row = tk.Frame(parent, bg=C["white"])
        row.pack(fill="x")
        emoji_picker.attach(row, box).pack(side="left")
        theme.label(row, "add an emoji", 8, C["muted"], C["white"]).pack(side="left")
        return (lambda: box.get("1.0", "end").strip(),
                lambda v: (box.delete("1.0", "end"), box.insert("1.0", v or "")))
    var = tk.StringVar()
    row = tk.Frame(parent, bg=C["white"])
    row.pack(fill="x")
    entry = theme.entry(row, var)
    entry.pack(side="left", fill="x", expand=True, ipady=5)
    emoji_picker.attach(row, entry, replace=icon).pack(side="left", padx=(4, 0))
    return (lambda: var.get().strip(), lambda v: var.set(v or ""))


# ------------------------------------------------------------------
# Tab 1 + 5: simple text settings
# ------------------------------------------------------------------
class TextTab(tk.Frame):
    """A list of texts (stored in about_settings). `fields` = [(key, caption, tall)]."""

    def __init__(self, parent, fields, on_change, note=""):
        super().__init__(parent, bg=C["white"])
        self.on_change = on_change
        self.inputs = {}
        if note:
            theme.label(self, note, 9, C["muted"], C["white"], wraplength=740, justify="left"
                        ).pack(anchor="w", padx=18, pady=(12, 0))
        body = tk.Frame(self, bg=C["white"])
        body.pack(fill="both", expand=True, padx=18, pady=6)
        for key, caption, tall in fields:
            self.inputs[key] = make_input(body, caption, tall)
        data = get_settings()
        for key, (_get, put) in self.inputs.items():
            put(data.get(key, ""))
        theme.button(self, "💾 Save", self.save, size=10).pack(anchor="w", padx=18, pady=12)

    def save(self):
        for key, (get, _put) in self.inputs.items():
            set_setting(key, get())
        self.on_change()
        messagebox.showinfo("Saved", "The About page was updated.", parent=self)


class AnnouncementTab(tk.Frame):
    """Publish (or remove) an announcement shown at the very top of the About page."""

    def __init__(self, parent, on_change):
        super().__init__(parent, bg=C["white"])
        self.on_change = on_change
        theme.label(self, "Post an announcement to the About page. Everybody sees it at the top of the page "
                          "until you remove it.", 9, C["muted"], C["white"], wraplength=740, justify="left"
                    ).pack(anchor="w", padx=18, pady=(12, 0))
        body = tk.Frame(self, bg=C["white"])
        body.pack(fill="x", padx=18, pady=6)
        self.title_in = make_input(body, "Title")
        self.body_in = make_input(body, "Message", tall=8)
        data = get_settings()
        self.title_in[1](data["announcement_title"])
        self.body_in[1](data["announcement_body"])
        bar = tk.Frame(self, bg=C["white"])
        bar.pack(anchor="w", padx=18, pady=12)
        theme.button(bar, "📢 Publish", self.publish, size=10).pack(side="left")
        theme.button(bar, "Remove announcement", self.remove, bg=C["red"], size=10,
                     hover_color="#9E2F2F").pack(side="left", padx=8)

    def publish(self):
        title, text = self.title_in[0](), self.body_in[0]()
        if not title or not text:
            return messagebox.showwarning("Missing", "Please write a title and a message.", parent=self)
        set_setting("announcement_title", title)
        set_setting("announcement_body", text)
        set_setting("announcement_at", datetime.now().strftime("%b %d, %Y %I:%M %p"))
        self.on_change()
        messagebox.showinfo("Published", "The announcement is now on the About page.", parent=self)

    def remove(self):
        for key in ("announcement_title", "announcement_body", "announcement_at"):
            set_setting(key, "")
        self.title_in[1]("")
        self.body_in[1]("")
        self.on_change()


# ------------------------------------------------------------------
# Tab 2, 3, 4: lists you can add to / edit / delete / re-order
# ------------------------------------------------------------------
class ListTab(tk.Frame):
    """
    A generic editor for rows of one table.
    cfg = {
      "table": "about_items", "id": "item_id", "kind": "card" (or None),
      "fields": [(column, caption, tall)],     # first field is required
      "label": lambda row: text shown in the list,
      "photo": True/False                      # developers have a photo
    }
    """

    def __init__(self, parent, cfg, on_change):
        super().__init__(parent, bg=C["white"])
        self.cfg = cfg
        self.on_change = on_change
        self.rows = []
        self.sel_id = None
        self.pending_photo = None            # newly chosen file (not copied yet)
        self.drop_photo = False
        self.current_photo = None

        # ---------- left: the list ----------
        left = tk.Frame(self, bg=C["white"])
        left.pack(side="left", fill="y", padx=(14, 8), pady=12)
        self.listbox = tk.Listbox(left, width=34, height=18, font=(theme.FONT, 10), activestyle="none",
                                  selectbackground=C["green"], selectforeground="white", exportselection=False)
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_pick)
        order = tk.Frame(left, bg=C["white"])
        order.pack(fill="x", pady=(6, 0))
        theme.button(order, "▲ Up", lambda: self.move(-1), bg=C["blue_dark"], size=9, pady=4,
                     hover_color=C["purple_dark"]).pack(side="left")
        theme.button(order, "▼ Down", lambda: self.move(1), bg=C["blue_dark"], size=9, pady=4,
                     hover_color=C["purple_dark"]).pack(side="left", padx=6)

        # ---------- right: the form ----------
        right = tk.Frame(self, bg=C["white"])
        right.pack(side="left", fill="both", expand=True, padx=(8, 14), pady=12)
        self.form_title = theme.label(right, "➕ New item", 12, C["green_dark"], C["white"], True)
        self.form_title.pack(anchor="w")
        self.inputs = {}
        for col, caption, tall in cfg["fields"]:
            self.inputs[col] = make_input(right, caption, tall)
        if cfg.get("photo"):
            theme.field(right, "Photo")
            row = tk.Frame(right, bg=C["white"])
            row.pack(fill="x")
            self.photo_holder = tk.Frame(row, bg=C["white"])
            self.photo_holder.pack(side="left")
            col = tk.Frame(row, bg=C["white"])
            col.pack(side="left", padx=10)
            theme.button(col, "📷 Upload photo", self.choose_photo, bg=C["purple_dark"], size=9, pady=5,
                         hover_color=C["blue_dark"]).pack(anchor="w")
            theme.button(col, "Remove photo", self.remove_photo, bg=C["muted"], size=9, pady=5,
                         hover_color=C["dark"]).pack(anchor="w", pady=(4, 0))
            self.photo_note = theme.label(col, "", 8, C["muted"], C["white"])
            self.photo_note.pack(anchor="w")
        bar = tk.Frame(right, bg=C["white"])
        bar.pack(fill="x", pady=14)
        theme.button(bar, "💾 Save", self.save, size=10).pack(side="left")
        theme.button(bar, "➕ New", self.new, bg=C["blue_dark"], size=10,
                     hover_color=C["purple_dark"]).pack(side="left", padx=6)
        theme.button(bar, "🗑 Delete", self.delete, bg=C["red"], size=10, hover_color="#9E2F2F").pack(side="right")
        self.load()
        self.new()

    # ---------- data ----------
    def query(self):
        cfg = self.cfg
        sql = f"SELECT * FROM {cfg['table']}"
        params = []
        if cfg.get("kind"):
            sql += " WHERE kind=%s"
            params.append(cfg["kind"])
        return db.fetch_all(sql + f" ORDER BY sort_order, {cfg['id']}", params)

    def load(self):
        self.rows = self.query()
        self.listbox.delete(0, "end")
        for r in self.rows:
            self.listbox.insert("end", self.cfg["label"](r))
        for i, r in enumerate(self.rows):                      # keep the selection
            if r[self.cfg["id"]] == self.sel_id:
                self.listbox.selection_set(i)

    def on_pick(self, _e=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        row = self.rows[sel[0]]
        self.sel_id = row[self.cfg["id"]]
        self.form_title.configure(text=f"✏ Editing: {self.cfg['label'](row)}")
        for col, (_get, put) in self.inputs.items():
            put(row[col])
        if self.cfg.get("photo"):
            self.current_photo, self.pending_photo, self.drop_photo = row["photo_path"], None, False
            self.draw_photo()

    def new(self):
        self.sel_id = None
        self.listbox.selection_clear(0, "end")
        self.form_title.configure(text="➕ New item")
        for _col, (_get, put) in self.inputs.items():
            put("")
        if self.cfg.get("photo"):
            self.current_photo, self.pending_photo, self.drop_photo = None, None, False
            self.draw_photo()

    # ---------- photo (developers) ----------
    def draw_photo(self):
        theme.clear(self.photo_holder)
        shown = None if self.drop_photo else (self.pending_photo or self.current_photo)
        round_photo(self.photo_holder, shown, 72, C["white"]).pack()
        self.photo_note.configure(text="New photo (saved when you press Save)" if self.pending_photo else "")

    def choose_photo(self):
        path = filedialog.askopenfilename(
            parent=self, title="Choose a photo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif"), ("All files", "*.*")])
        if path:
            self.pending_photo, self.drop_photo = path, False
            self.draw_photo()

    def remove_photo(self):
        self.pending_photo, self.drop_photo = None, True
        self.draw_photo()

    # ---------- save / delete / move ----------
    def save(self):
        cfg = self.cfg
        values = {col: get() for col, (get, _put) in self.inputs.items()}
        first = cfg["fields"][0][0]
        if not values[first]:
            return messagebox.showwarning("Missing", f"Please fill in: {cfg['fields'][0][1]}.", parent=self)
        if cfg.get("photo"):
            photo = self.current_photo
            if self.pending_photo:
                photo = store_photo(self.pending_photo)
            elif self.drop_photo:
                photo = None
            if photo != self.current_photo:
                remove_photo_file(self.current_photo)
            values["photo_path"] = photo
        cols = list(values)
        if self.sel_id:
            db.execute(f"UPDATE {cfg['table']} SET " + ", ".join(f"{c}=%s" for c in cols) +
                       f" WHERE {cfg['id']}=%s", [values[c] for c in cols] + [self.sel_id])
        else:
            nxt = db.fetch_one(f"SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM {cfg['table']}")["n"]
            if cfg.get("kind"):
                cols += ["kind"]
                values["kind"] = cfg["kind"]
            cols += ["sort_order"]
            values["sort_order"] = nxt
            self.sel_id = db.execute(
                f"INSERT INTO {cfg['table']} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                [values[c] for c in cols])
        self.load()
        row = next((r for r in self.rows if r[cfg["id"]] == self.sel_id), None)
        if row:
            self.on_pick()
            if cfg.get("photo"):
                self.current_photo, self.pending_photo, self.drop_photo = row["photo_path"], None, False
                self.draw_photo()
        self.on_change()

    def delete(self):
        if not self.sel_id:
            return messagebox.showwarning("Select", "Pick an item in the list first.", parent=self)
        if not messagebox.askyesno("Delete", "Delete this item from the About page?", parent=self):
            return
        cfg = self.cfg
        if cfg.get("photo"):
            remove_photo_file(self.current_photo)
        db.execute(f"DELETE FROM {cfg['table']} WHERE {cfg['id']}=%s", (self.sel_id,))
        self.sel_id = None
        self.load()
        self.new()
        self.on_change()

    def move(self, step):
        """Swap the selected item with its neighbour (changes the order on the page)."""
        sel = self.listbox.curselection()
        if not sel:
            return
        i, j = sel[0], sel[0] + step
        if not 0 <= j < len(self.rows):
            return
        ids = [r[self.cfg["id"]] for r in self.rows]
        ids[i], ids[j] = ids[j], ids[i]
        for n, item_id in enumerate(ids):                      # renumber 0, 1, 2, ...
            db.execute(f"UPDATE {self.cfg['table']} SET sort_order=%s WHERE {self.cfg['id']}=%s", (n, item_id))
        self.sel_id = ids[j]
        self.load()
        self.listbox.see(j)
        self.on_change()


# ------------------------------------------------------------------
# the window
# ------------------------------------------------------------------
class SuggestionsTab(tk.Frame):
    """Read what users suggested: mark it read / done, or delete it. (The page itself does not change.)"""

    def __init__(self, parent, on_change):
        super().__init__(parent, bg=C["white"])
        self.on_change = on_change
        self.rows = []
        theme.label(self, "Suggestions sent from the About page. New ones are listed first.", 9, C["muted"],
                    C["white"]).pack(anchor="w", padx=18, pady=(12, 6))
        body = tk.Frame(self, bg=C["white"])
        body.pack(fill="both", expand=True, padx=18)
        self.box = tk.Listbox(body, width=38, font=(theme.FONT, 10), relief="solid", bd=1, exportselection=False,
                              activestyle="none")
        self.box.pack(side="left", fill="y")
        self.box.bind("<<ListboxSelect>>", self.show)
        self.detail = tk.Text(body, font=(theme.FONT, 10), relief="solid", bd=1, wrap="word", state="disabled")
        self.detail.pack(side="left", fill="both", expand=True, padx=(10, 0))
        bar = tk.Frame(self, bg=C["white"])
        bar.pack(anchor="w", padx=18, pady=12)
        theme.button(bar, "Mark as read", lambda: self.mark("Read"), bg=C["blue_dark"], size=9,
                     hover_color=C["purple_dark"]).pack(side="left")
        theme.button(bar, "✔ Mark as done", lambda: self.mark("Done"), size=9).pack(side="left", padx=6)
        theme.button(bar, "🗑 Delete", self.delete, bg=C["red"], size=9, hover_color="#9E2F2F").pack(side="left")
        self.load()

    def load(self):
        self.rows = db.fetch_all(
            "SELECT s.*, u.full_name FROM about_suggestions s JOIN user_profiles u ON u.user_id=s.user_id "
            "ORDER BY FIELD(s.status,'New','Read','Done'), s.created_at DESC LIMIT 200")
        self.box.delete(0, "end")
        for r in self.rows:
            self.box.insert("end", f"[{r['status']}]  {r['full_name']}  -  {r['created_at']:%b %d}")
        self.write("Pick a suggestion on the left." if self.rows else "No suggestions yet.")

    def write(self, text):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")

    def current(self):
        pick = self.box.curselection()
        return self.rows[pick[0]] if pick else None

    def show(self, _e=None):
        r = self.current()
        if r:
            self.write(f"From: {r['full_name']}    {r['created_at']:%b %d, %Y %I:%M %p}\nStatus: {r['status']}\n\n"
                       f"WHAT TO IMPROVE\n{r['improve'] or '-'}\n\nFEATURES TO ADD\n{r['feature'] or '-'}")

    def mark(self, status):
        r = self.current()
        if r:
            db.execute("UPDATE about_suggestions SET status=%s WHERE suggestion_id=%s", (status, r["suggestion_id"]))
            self.load()
            self.on_change()

    def delete(self):
        r = self.current()
        if r and messagebox.askyesno("Delete", "Delete this suggestion?", parent=self):
            db.execute("DELETE FROM about_suggestions WHERE suggestion_id=%s", (r["suggestion_id"],))
            self.load()
            self.on_change()


class AboutEditor(tk.Toplevel):
    TABS = ["Page text", "Info cards", "Guidelines", "Developers", "Announcement", "Suggestions"]

    def __init__(self, page, start_tab=0):
        super().__init__(page)
        self.title("Edit the About page (administrator)")
        self.configure(bg=C["white"])
        self.geometry("900x640")
        self.transient(page.winfo_toplevel())
        theme.label(self, "✏ Edit the About page", 15, C["green_dark"], C["white"], True
                    ).pack(anchor="w", padx=18, pady=(14, 0))
        theme.label(self, "Changes are saved to the database and appear on the page for everyone straight away.",
                    9, C["muted"], C["white"]).pack(anchor="w", padx=18, pady=(0, 6))
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        change = page.build

        nb.add(TextTab(nb, [
            ("hero_title", "Main headline (top banner)", 0),
            ("hero_text", "Text under the headline", 3),
            ("guidelines_title", "Guidelines section title", 0),
            ("guidelines_intro", "Guidelines intro", 3),
            ("rules_title", "Title of the 'rules broken' notice", 0),
            ("rules_text", "Text of the 'rules broken' notice (one point per line)", 6),
            ("dev_title", "Developers section title", 0),
            ("dev_intro", "Developers intro text", 3),
        ], change), text=self.TABS[0])
        nb.add(ListTab(nb, {
            "table": "about_items", "id": "item_id", "kind": "card",
            "fields": [("title", "Title", 0), ("icon", "Icon (one emoji)", 0), ("body", "Text", 5)],
            "label": lambda r: f"{r['icon'] or ''}  {r['title']}"}, change), text=self.TABS[1])
        nb.add(ListTab(nb, {
            "table": "about_items", "id": "item_id", "kind": "guideline",
            "fields": [("title", "Rule title", 0), ("icon", "Icon (one emoji)", 0), ("body", "Rule text", 6)],
            "label": lambda r: f"{r['icon'] or ''}  {r['title']}"}, change), text=self.TABS[2])
        nb.add(ListTab(nb, {
            "table": "about_team", "id": "member_id", "kind": None, "photo": True,
            "fields": [("name", "Name", 0), ("role", "Role (e.g. Lead Developer)", 0),
                       ("bio", "Wording about this person", 5)],
            "label": lambda r: f"{r['name']}  -  {r['role'] or ''}"}, change), text=self.TABS[3])
        nb.add(AnnouncementTab(nb, change), text=self.TABS[4])
        nb.add(SuggestionsTab(nb, change), text=self.TABS[5])
        nb.select(start_tab)
