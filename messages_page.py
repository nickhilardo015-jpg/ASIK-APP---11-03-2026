"""
messages_page.py  --  Messaging between ALL users (employers, job seekers,
lenders, renters, admin).

(unchanged docstring - see original)
"""

import os
import tkinter as tk
from tkinter import colorchooser, messagebox

import database as db
import emoji_picker
import language
import session
import theme
from theme import C

# ------------------------------------------------------------------
# Role colour code:  role -> (light colour, dark colour, display-name KEY)
# ------------------------------------------------------------------
ROLE_STYLE = {
    "admin":      ("#FFD6DC", "#BD5267", "messages.role_admin"),
    "employer":   ("#DCEBFF", "#3868B7", "messages.role_employer"),
    "lender":     ("#FFF0C5", "#A87312", "messages.role_lender"),
    "renter":     ("#FFE3CC", "#B66A31", "messages.role_renter"),
    "job_seeker": ("#DDF0DA", "#2F7A4A", "messages.role_job_seeker"),
}
ROLE_ORDER = ["admin", "employer", "lender", "renter", "job_seeker"]

# ready-made chat themes: (name-key, my bubble colour, chat background)
PRESETS = [
    ("messages.preset_meadow",   "#DDF0DA", "#FFFFFF"),
    ("messages.preset_sky",      "#CFE4FF", "#F5FAFF"),
    ("messages.preset_lavender", "#E4D8FF", "#FAF7FF"),
    ("messages.preset_rose",     "#FFD9DE", "#FFF8F9"),
    ("messages.preset_sunset",   "#FFDDC2", "#FFF9F3"),
    ("messages.preset_sunshine", "#FFEFB5", "#FFFEF5"),
    ("messages.preset_night",    "#2F7A4A", "#1E2B24"),
]
DEFAULT_THEME = {"my_color": "#DDF0DA", "chat_bg": "#FFFFFF", "role_coded": 1}


# ------------------------------------------------------------------
# small colour helpers  (unchanged)
# ------------------------------------------------------------------
def _rgb(h):
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def blend(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(int(ra[i] + (rb[i] - ra[i]) * t) for i in range(3))


def ink(bg):
    r, g, b = _rgb(bg)
    return "#1F2A24" if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6 else "#FFFFFF"


def roles_of(csv):
    have = [r for r in (csv or "").split(",") if r]
    return [r for r in ROLE_ORDER if r in have] or ["job_seeker"]


def role_name(role):
    """Translated display name of a role (used in the legend, chips and preset preview)."""
    return language.t(ROLE_STYLE[role][2])


# ------------------------------------------------------------------
# ensure the two extra tables exist  (unchanged)
# ------------------------------------------------------------------
_tables_ready = False


def ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    db.execute("CREATE TABLE IF NOT EXISTS message_hidden ("
               "message_id INT NOT NULL, user_id INT NOT NULL, PRIMARY KEY (message_id, user_id), "
               "FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE, "
               "FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE"
               ") ENGINE=InnoDB")
    db.execute("CREATE TABLE IF NOT EXISTS chat_settings ("
               "user_id INT PRIMARY KEY, my_color VARCHAR(7) NOT NULL DEFAULT '#DDF0DA', "
               "chat_bg VARCHAR(7) NOT NULL DEFAULT '#FFFFFF', role_coded TINYINT(1) NOT NULL DEFAULT 1, "
               "FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE"
               ") ENGINE=InnoDB")
    _tables_ready = True


NOT_HIDDEN = ("NOT EXISTS (SELECT 1 FROM message_hidden h "
              "WHERE h.message_id=m.message_id AND h.user_id=%s)")


class MessagesPage(tk.Frame):
    def __init__(self, parent, app, to_user=None):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        ensure_tables()
        self.contacts = []
        self.current = None
        self.current_role = "job_seeker"
        self._timer = None
        self._ticks = 0
        self._last_seen = None
        self._imgs = {}
        self.msgs = {}
        self.theme = self.load_theme()

        theme.page_header(self, language.t("messages.title"), language.t("messages.subtitle"),
                          C["purple_dark"])
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 14))

        # ================= LEFT: people =================
        left = tk.Frame(body, bg=C["bg"], width=330)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)
        self.search = theme.SearchBar(left, self.load_contacts,
                                       language.t("messages.search_placeholder"))
        self.search.pack(fill="x", pady=(0, 8))
        self.build_legend(left)
        list_card = theme.card(left)
        list_card.pack(fill="both", expand=True)
        self.people = theme.Scrollable(list_card, C["white"])
        self.people.pack(fill="both", expand=True)

        # ================= RIGHT: the chat =================
        right = theme.card(body)
        right.pack(side="left", fill="both", expand=True)
        self.head = tk.Frame(right, bg=C["purple"])
        self.head.pack(fill="x")
        self.bar = tk.Frame(right, bg=self.theme["chat_bg"])
        self.bar.pack(side="bottom", fill="x", padx=0, pady=0)
        self.hint = theme.label(right, language.t("messages.hint"), 8, C["muted"],
                                self.theme["chat_bg"])
        self.hint.pack(side="bottom", fill="x")
        self.chat = tk.Text(right, font=(theme.FONT, 10), bd=0, wrap="word", state="disabled",
                            bg=self.theme["chat_bg"], padx=12, pady=8, cursor="arrow")
        self.chat.pack(fill="both", expand=True)
        self.chat.bind("<Button-3>", self.on_right_click)
        self.chat.bind("<Button-2>", self.on_right_click)

        inner_bar = tk.Frame(self.bar, bg=self.theme["chat_bg"])
        inner_bar.pack(fill="x", padx=10, pady=10)
        self.msg_var = tk.StringVar()
        self.entry = tk.Entry(inner_bar, textvariable=self.msg_var, font=(theme.FONT, 11),
                              relief="solid", bd=1)
        self.entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.entry.bind("<Return>", lambda e: self.send())
        emoji_picker.attach(inner_bar, self.entry).pack(side="left", padx=(6, 0))
        theme.button(inner_bar, language.t("messages.send_btn"), self.send, size=10
                     ).pack(side="left", padx=(8, 0))
        self._inner_bar = inner_bar

        self.apply_theme()
        self.load_contacts()
        if to_user:
            self.open_conversation(to_user)
        else:
            self.draw_header(None)
            self.draw_messages()
        self.poll()

    # ================================================================
    # theme
    # ================================================================
    def load_theme(self):
        row = db.fetch_one("SELECT my_color, chat_bg, role_coded FROM chat_settings WHERE user_id=%s",
                           (session.user_id(),))
        return dict(row) if row else dict(DEFAULT_THEME)

    def save_theme(self):
        t = self.theme
        db.execute("INSERT INTO chat_settings (user_id, my_color, chat_bg, role_coded) "
                   "VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE my_color=VALUES(my_color), "
                   "chat_bg=VALUES(chat_bg), role_coded=VALUES(role_coded)",
                   (session.user_id(), t["my_color"], t["chat_bg"], int(t["role_coded"])))

    def apply_theme(self):
        t = self.theme
        for w in (self.chat, self.bar, self._inner_bar if hasattr(self, "_inner_bar") else self.bar,
                  self.hint):
            w.configure(bg=t["chat_bg"])
        if t["chat_bg"] and ink(t["chat_bg"]) == "#FFFFFF":
            self.hint.configure(fg="#C9D8CF")
        else:
            self.hint.configure(fg=C["muted"])
        look = dict(spacing1=6, spacing3=2)
        self.chat.tag_configure("me", background=t["my_color"], foreground=ink(t["my_color"]),
                                justify="right", lmargin1=120, lmargin2=120, rmargin=8, **look)
        for role, (light, dark, _k) in ROLE_STYLE.items():
            colour = blend(light, dark, 0.22) if t["role_coded"] else C["blue"]
            self.chat.tag_configure("them_" + role, background=colour, foreground=ink(colour),
                                    justify="left", lmargin1=8, lmargin2=8, rmargin=120, **look)
        self.chat.tag_configure("time", font=(theme.FONT, 7))
        self.chat.tag_configure("empty", foreground=C["muted"], justify="center", spacing1=30)

    def set_theme(self, **changes):
        self.theme.update(changes)
        self.save_theme()
        self.apply_theme()
        self._last_seen = None
        self.draw_messages()

    def open_theme(self):
        """Small window where the user edits the chat colours."""
        win = tk.Toplevel(self)
        win.title(language.t("messages.theme_title"))
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.resizable(False, False)
        theme.label(win, "🎨 " + language.t("messages.theme_title"), 14, C["purple_dark"],
                    C["white"], True).pack(anchor="w", padx=18, pady=(14, 0))
        theme.label(win, language.t("messages.theme_hint"), 9, C["muted"], C["white"]
                    ).pack(anchor="w", padx=18, pady=(0, 8))

        theme.label(win, language.t("messages.presets_label"), 8, C["dark"], C["white"], True
                    ).pack(anchor="w", padx=18)
        grid = tk.Frame(win, bg=C["white"])
        grid.pack(padx=18, pady=6)
        for i, (name_key, mine, bg) in enumerate(PRESETS):
            b = tk.Button(grid, text=language.t(name_key), width=10, bg=mine, fg=ink(mine),
                          relief="solid", bd=1, font=(theme.FONT, 9, "bold"), cursor="hand2",
                          highlightbackground=bg,
                          command=lambda m=mine, g=bg: self.set_theme(my_color=m, chat_bg=g))
            b.grid(row=i // 4, column=i % 4, padx=3, pady=3)

        theme.label(win, language.t("messages.custom_label"), 8, C["dark"], C["white"], True
                    ).pack(anchor="w", padx=18, pady=(10, 2))
        pick = tk.Frame(win, bg=C["white"])
        pick.pack(anchor="w", padx=18)

        def choose(key, title_key):
            result = colorchooser.askcolor(color=self.theme[key], title=language.t(title_key),
                                           parent=win)
            if result and result[1]:
                self.set_theme(**{key: result[1].upper()})

        theme.button(pick, language.t("messages.pick_my_color"),
                     lambda: choose("my_color", "messages.my_bubble_title"),
                     bg=C["purple_dark"], size=9).pack(side="left")
        theme.button(pick, language.t("messages.pick_chat_bg"),
                     lambda: choose("chat_bg", "messages.chat_bg_title"),
                     bg=C["blue_dark"], size=9).pack(side="left", padx=6)

        role_var = tk.IntVar(value=int(self.theme["role_coded"]))
        tk.Checkbutton(win, text=language.t("messages.role_coded_check"), variable=role_var,
                       bg=C["white"], activebackground=C["white"], font=(theme.FONT, 9),
                       command=lambda: self.set_theme(role_coded=role_var.get())
                       ).pack(anchor="w", padx=14, pady=(10, 0))

        leg = tk.Frame(win, bg=C["white"])
        leg.pack(anchor="w", padx=18, pady=6)
        for role in ROLE_ORDER:
            light, dark, _k = ROLE_STYLE[role]
            tk.Label(leg, text=role_name(role), bg=blend(light, dark, 0.22),
                     fg=ink(blend(light, dark, 0.22)), font=(theme.FONT, 8, "bold"),
                     padx=6, pady=2).pack(side="left", padx=2)

        row = tk.Frame(win, bg=C["white"])
        row.pack(fill="x", padx=18, pady=(8, 14))
        theme.button(row, language.t("messages.reset_theme"),
                     lambda: (role_var.set(1), self.set_theme(**DEFAULT_THEME)),
                     bg=C["muted"], size=9, hover_color=C["dark"]).pack(side="left")
        theme.button(row, language.t("common.close"), win.destroy, size=9).pack(side="right")

    # ================================================================
    # left side: role legend
    # ================================================================
    def build_legend(self, parent):
        leg = tk.Frame(parent, bg=C["bg"])
        leg.pack(side="bottom", fill="x", pady=(8, 0))
        theme.label(leg, language.t("messages.colour_code"), 8, C["muted"], C["bg"], True
                    ).pack(anchor="w")
        chips = tk.Frame(leg, bg=C["bg"])
        chips.pack(anchor="w", pady=2)
        for role in ROLE_ORDER:
            light, dark, _k = ROLE_STYLE[role]
            tk.Label(chips, text=role_name(role), bg=light, fg=dark,
                     font=(theme.FONT, 8, "bold"), padx=7, pady=2,
                     highlightthickness=1, highlightbackground=dark
                     ).pack(side="left", padx=(0, 4), pady=2)

    def avatar(self, parent, photo_path, size, role, bg):
        light, dark, _k = ROLE_STYLE[role]
        path = photo_path if photo_path and os.path.exists(photo_path) else None
        try:
            stamp = os.path.getmtime(path) if path else 0
            key = (path, stamp, size, role)
            if key not in self._imgs:
                self._imgs[key] = self._round_image(path, size, light, dark)
            img = self._imgs[key]
            lbl = tk.Label(parent, image=img, bg=bg, bd=0)
            lbl.image = img
            return lbl
        except Exception:
            return theme.avatar(parent, path, size, bg)

    @staticmethod
    def _round_image(path, size, light, dark, ring=3):
        from PIL import Image, ImageDraw, ImageTk
        k = 4
        big = size * k
        out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        ImageDraw.Draw(out).ellipse((0, 0, big - 1, big - 1), fill=dark)
        inner = big - 2 * ring * k
        if path:
            pic = Image.open(path).convert("RGBA")
            side = min(pic.size)
            left, top = (pic.width - side) // 2, (pic.height - side) // 2
            face = pic.crop((left, top, left + side, top + side)).resize((inner, inner),
                                                                          Image.LANCZOS)
        else:
            face = Image.new("RGBA", (inner, inner), light)
            fd = ImageDraw.Draw(face)
            fd.ellipse((inner * .32, inner * .16, inner * .68, inner * .52), fill=dark)
            fd.ellipse((inner * .10, inner * .60, inner * .90, inner * 1.30), fill=dark)
        mask = Image.new("L", (inner, inner), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, inner - 1, inner - 1), fill=255)
        out.paste(face, (ring * k, ring * k), mask)
        return ImageTk.PhotoImage(out.resize((size, size), Image.LANCZOS))

    # ---------------- contacts ----------------
    def load_contacts(self):
        me = session.user_id()
        sql = ("SELECT u.user_id, p.full_name, p.photo_path, GROUP_CONCAT(DISTINCT r.role) AS roles, "
               "(SELECT MAX(m.sent_at) FROM messages m WHERE "
               "   ((m.sender_id=u.user_id AND m.receiver_id=%s) OR "
               "    (m.sender_id=%s AND m.receiver_id=u.user_id)) "
               "   AND " + NOT_HIDDEN + ") AS last_at, "
               "(SELECT COUNT(*) FROM messages m WHERE m.sender_id=u.user_id AND m.receiver_id=%s "
               "   AND m.is_read=0) AS unread "
               "FROM account_credentials u JOIN user_profiles p ON p.user_id=u.user_id "
               "LEFT JOIN user_roles r ON r.user_id=u.user_id WHERE u.user_id<>%s AND u.is_active=1")
        params = [me, me, me, me, me]
        text = self.search.text()
        if text:
            sql += (" AND (p.full_name LIKE %s OR u.username LIKE %s OR EXISTS (SELECT 1 FROM user_roles x "
                    "WHERE x.user_id=u.user_id AND x.role LIKE %s))")
            role_like = "%" + text.replace(" ", "_") + "%"
            params += [f"%{text}%", f"%{text}%", role_like]
        sql += " GROUP BY u.user_id, p.full_name, p.photo_path"
        if not text:
            sql += " HAVING last_at IS NOT NULL OR u.user_id=%s"
            params.append(self.current or 0)
        sql += " ORDER BY (last_at IS NULL), last_at DESC, p.full_name LIMIT 100"
        self.contacts = db.fetch_all(sql, params)

        top = self.people.canvas.yview()[0]
        theme.clear(self.people.inner)
        if not self.contacts:
            note = (language.t("messages.no_one_found") if self.search.text() else
                    language.t("messages.no_conversations"))
            theme.label(self.people.inner, note, 10, C["muted"], C["white"], justify="center",
                        wraplength=260).pack(pady=20, padx=10)
        for c in self.contacts:
            self.make_row(c)
        self.people.update_idletasks()
        self.people.canvas.yview_moveto(top)

    def make_row(self, c):
        roles = roles_of(c["roles"])
        main = roles[0]
        light, dark, _k = ROLE_STYLE[main]
        active = c["user_id"] == self.current
        rest_bg = light if active else C["white"]
        rest_border = dark if active else C["white"]

        row = tk.Frame(self.people.inner, bg=rest_bg, highlightthickness=3,
                       highlightbackground=rest_border, cursor="hand2")
        row.pack(fill="x", padx=6, pady=3)
        tk.Frame(row, bg=dark, width=5).pack(side="left", fill="y")
        recolor = [row]

        pic = self.avatar(row, c["photo_path"], 46, main, rest_bg)
        pic.pack(side="left", padx=8, pady=6)
        recolor.append(pic)

        col = tk.Frame(row, bg=rest_bg)
        col.pack(side="left", fill="x", expand=True, pady=4)
        recolor.append(col)
        name = theme.label(col, c["full_name"], 10, C["dark"], rest_bg, True)
        name.pack(anchor="w")
        recolor.append(name)
        chips = tk.Frame(col, bg=rest_bg)
        chips.pack(anchor="w", pady=(2, 0))
        recolor.append(chips)
        for role in roles:
            lt, dk, _k2 = ROLE_STYLE[role]
            tk.Label(chips, text=role_name(role), bg=blend(lt, dk, 0.22),
                     fg=ink(blend(lt, dk, 0.22)),
                     font=(theme.FONT, 7, "bold"), padx=5).pack(side="left", padx=(0, 3))
        if c["unread"]:
            tk.Label(row, text=f" {c['unread']} ", bg=C["red"], fg="white",
                     font=(theme.FONT, 8, "bold")).pack(side="right", padx=8)

        def bind_all(w):
            w.bind("<Button-1>", lambda e, uid=c["user_id"]: self.open_conversation(uid))
            w.bind("<MouseWheel>", self._wheel)
            w.bind("<Enter>", lambda e: self.glow_on(row, recolor, light, dark))
            w.bind("<Leave>", lambda e: self.glow_off(row, recolor, rest_bg, rest_border))
            for child in w.winfo_children():
                bind_all(child)
        bind_all(row)

    def _wheel(self, event):
        self.people.canvas.yview_scroll(int(-event.delta / 120), "units")

    def glow_on(self, row, recolor, light, dark):
        try:
            self._cancel_fade(row)
            for w in recolor:
                w.configure(bg=light)
            self._fade(row, row.cget("highlightbackground"), dark)
        except tk.TclError:
            pass

    def glow_off(self, row, recolor, rest_bg, rest_border):
        try:
            under = row.winfo_containing(*row.winfo_pointerxy())
            while under is not None:
                if under is row:
                    return
                under = under.master
            self._cancel_fade(row)
            for w in recolor:
                w.configure(bg=rest_bg)
            self._fade(row, row.cget("highlightbackground"), rest_border)
        except (tk.TclError, KeyError):
            pass

    def _fade(self, row, start, end, i=0, steps=4):
        try:
            row.configure(highlightbackground=blend(start, end, (i + 1) / steps))
            if i + 1 < steps:
                row._job = row.after(28, lambda: self._fade(row, start, end, i + 1, steps))
        except tk.TclError:
            pass

    @staticmethod
    def _cancel_fade(row):
        job = getattr(row, "_job", None)
        if job:
            try:
                row.after_cancel(job)
            except tk.TclError:
                pass
            row._job = None

    # ================================================================
    # conversation
    # ================================================================
    def open_conversation(self, user_id):
        self.current = user_id
        self._last_seen = None
        db.execute("UPDATE messages SET is_read=1 WHERE sender_id=%s AND receiver_id=%s",
                   (user_id, session.user_id()))
        info = db.fetch_one(
            "SELECT p.*, (SELECT GROUP_CONCAT(role) FROM user_roles WHERE user_id=p.user_id) AS roles "
            "FROM user_profiles p WHERE p.user_id=%s", (user_id,))
        self.current_role = roles_of(info["roles"])[0] if info else "job_seeker"
        self.draw_header(info)
        self.draw_messages()
        self.load_contacts()
        self.entry.focus_set()

    def draw_header(self, info):
        theme.clear(self.head)
        role = roles_of(info["roles"])[0] if info else "job_seeker"
        light, dark, _k = ROLE_STYLE[role]
        tint = blend(light, dark, 0.12) if info else C["purple"]
        self.head.configure(bg=tint)

        buttons = tk.Frame(self.head, bg=tint)
        buttons.pack(side="right", padx=10)
        theme.button(buttons, language.t("messages.theme_btn"), self.open_theme,
                     bg=C["purple_dark"], size=9, hover_color=C["blue_dark"]
                     ).pack(side="left", padx=3, pady=10)
        if not info:
            theme.label(self.head, language.t("messages.select_person"), 10, C["purple_dark"],
                        tint, True).pack(side="left", padx=14, pady=16)
            return
        theme.button(buttons, language.t("messages.delete_chat_btn"), self.delete_conversation,
                     bg=C["red"], size=9, hover_color="#9E2F2F").pack(side="left", padx=3, pady=10)

        self.avatar(self.head, info["photo_path"], 54, role, tint).pack(side="left", padx=12, pady=8)
        col = tk.Frame(self.head, bg=tint)
        col.pack(side="left")
        theme.label(col, info["full_name"], 12, C["dark"], tint, True).pack(anchor="w")
        chips = tk.Frame(col, bg=tint)
        chips.pack(anchor="w", pady=2)
        for r in roles_of(info["roles"]):
            lt, dk, _k2 = ROLE_STYLE[r]
            tk.Label(chips, text=role_name(r), bg=blend(lt, dk, 0.22),
                     fg=ink(blend(lt, dk, 0.22)),
                     font=(theme.FONT, 7, "bold"), padx=5).pack(side="left", padx=(0, 3))
        where = ", ".join(x for x in (info["municipality"], info["province"]) if x)
        if where:
            theme.label(col, "📍 " + where, 8, C["muted"], tint).pack(anchor="w")

    def draw_messages(self):
        self.chat.configure(state="normal")
        if not self.current:
            self.chat.delete("1.0", "end")
            self.chat.insert("end", language.t("messages.empty_conversations"), "empty")
            self.chat.configure(state="disabled")
            return
        me = session.user_id()
        rows = db.fetch_all(
            "SELECT m.* FROM messages m WHERE ((m.sender_id=%s AND m.receiver_id=%s) OR "
            "(m.sender_id=%s AND m.receiver_id=%s)) AND " + NOT_HIDDEN +
            " ORDER BY m.sent_at, m.message_id",
            (me, self.current, self.current, me, me))
        signature = (len(rows), rows[-1]["message_id"] if rows else 0)
        if signature == self._last_seen:
            self.chat.configure(state="disabled")
            return
        self._last_seen = signature
        self.msgs = {m["message_id"]: m for m in rows}
        self.chat.delete("1.0", "end")
        if not rows:
            self.chat.insert("end", language.t("messages.empty_first_hello"), "empty")
        them_tag = "them_" + self.current_role
        for m in rows:
            tag = "me" if m["sender_id"] == me else them_tag
            mark = "msg_%d" % m["message_id"]
            self.chat.insert("end", f" {m['body']} \n", (tag, mark))
            self.chat.insert("end", m["sent_at"].strftime("%b %d, %I:%M %p") + "\n",
                             (tag, "time", mark))
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def send(self):
        text = self.msg_var.get().strip()
        if not text:
            return
        if not self.current:
            return messagebox.showinfo(language.t("messages.pick_person_title"),
                                       language.t("messages.pick_person_msg"))
        db.execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (%s,%s,%s)",
                   (session.user_id(), self.current, text))
        self.msg_var.set("")
        self.draw_messages()
        self.load_contacts()

    # ================================================================
    # deleting
    # ================================================================
    def on_right_click(self, event):
        index = self.chat.index("@%d,%d" % (event.x, event.y))
        mid = None
        for tag in self.chat.tag_names(index):
            if tag.startswith("msg_"):
                mid = int(tag[4:])
        if mid is None or mid not in self.msgs:
            return
        mine = self.msgs[mid]["sender_id"] == session.user_id()
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=language.t("messages.menu_delete_me"),
                         command=lambda: self.delete_for_me(mid))
        menu.add_command(label=language.t("messages.menu_delete_everyone"),
                         state="normal" if mine else "disabled",
                         command=lambda: self.delete_for_everyone(mid))
        menu.add_separator()
        menu.add_command(label=language.t("messages.menu_copy"),
                         command=lambda: self.copy_text(mid))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def copy_text(self, mid):
        self.clipboard_clear()
        self.clipboard_append(self.msgs[mid]["body"])

    def delete_for_me(self, mid):
        db.execute("INSERT IGNORE INTO message_hidden (message_id, user_id) VALUES (%s,%s)",
                   (mid, session.user_id()))
        self._last_seen = None
        self.draw_messages()
        self.load_contacts()

    def delete_for_everyone(self, mid):
        if not messagebox.askyesno(language.t("messages.delete_everyone_title"),
                                   language.t("messages.delete_everyone_msg")):
            return
        db.execute("DELETE FROM messages WHERE message_id=%s AND sender_id=%s",
                   (mid, session.user_id()))
        self._last_seen = None
        self.draw_messages()
        self.load_contacts()

    def delete_conversation(self):
        if not self.current:
            return
        if not messagebox.askyesno(language.t("messages.delete_chat_title"),
                                   language.t("messages.delete_chat_msg")):
            return
        me = session.user_id()
        db.execute("INSERT IGNORE INTO message_hidden (message_id, user_id) "
                   "SELECT message_id, %s FROM messages "
                   "WHERE (sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s)",
                   (me, me, self.current, self.current, me))
        self._last_seen = None
        self.draw_messages()
        self.load_contacts()

    # ================================================================
    # auto refresh  (unchanged)
    # ================================================================
    def poll(self):
        try:
            self._ticks += 1
            if self.current:
                db.execute("UPDATE messages SET is_read=1 WHERE sender_id=%s AND receiver_id=%s",
                           (self.current, session.user_id()))
                self.draw_messages()
            if self._ticks % 5 == 0:
                self.load_contacts()
            self._timer = self.after(4000, self.poll)
        except tk.TclError:
            pass

    def destroy(self):
        if self._timer:
            self.after_cancel(self._timer)
        super().destroy()