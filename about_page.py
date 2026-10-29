"""
about_page.py  --  About Asik: mission, services, community guidelines and the
developer team.

Everything on this page comes from MySQL (see about_data.py), so:
  * EVERYONE can read it (view only: no reactions, no comments)
  * an ADMINISTRATOR sees an "✏ Edit this page" button and can change the
    whole page: headline, cards, guidelines, developer team (names, roles,
    wording and PHOTOS) and post an announcement (see about_editor.py)
"""

import tkinter as tk
from tkinter import messagebox, ttk

import session
import theme
import emoji_picker
from about_data import ensure_tables, get_settings, round_photo
from about_editor import AboutEditor
from theme import C
import database as db

BLUE_PANEL = "#365DA0"
# card accent colours, used in turn
ACCENTS = [C["green"], C["yellow_dark"], C["blue_dark"], C["green_dark"], C["purple_dark"],
           C["pink_dark"], C["orange_dark"]]


class AboutPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        ensure_tables()
        self.is_admin = "admin" in session.user["roles"]
        theme.page_header(self, "About Asik ✦", "Modern farming meets smart technology.", C["purple_dark"])

        if self.is_admin:                                       # administrator tools
            tools = tk.Frame(self, bg=C["yellow"])
            tools.pack(fill="x", padx=28, pady=(0, 8))
            theme.label(tools, "🛠 Administrator: you can change everything on this page.", 9, C["dark"],
                        C["yellow"], True).pack(side="left", padx=12, pady=8)
            theme.button(tools, "✏ Edit this page", lambda: AboutEditor(self), size=9, pady=4
                         ).pack(side="right", padx=10, pady=6)

        # ---- a scrolling area (own canvas so the mouse wheel always works) ----
        holder = tk.Frame(self, bg=C["bg"])
        holder.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(holder, bg=C["bg"], highlightthickness=0, height=260)
        bar = ttk.Scrollbar(holder, orient="vertical", command=self.canvas.yview)
        self.body = tk.Frame(self.canvas, bg=C["bg"])
        win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(win, width=e.width))
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bind_all("<MouseWheel>", self.on_wheel)
        theme.bind_scroll_keys(self, self.canvas)
        self.build()

    # ================================================================
    def build(self):
        """(Re)draw the whole page from the database. The editor calls this after every change."""
        try:
            top = self.canvas.yview()[0]
            theme.clear(self.body)
            s = get_settings()
            body = self.body

            # ---- announcement posted by an administrator ----
            if s["announcement_body"]:
                note = theme.card(body, C["yellow"])
                note.pack(fill="x", padx=28, pady=(0, 14))
                tk.Frame(note, bg=C["yellow_dark"], height=4).pack(fill="x")
                theme.label(note, "📢 " + (s["announcement_title"] or "Announcement"), 13, C["dark"], C["yellow"],
                            True, wraplength=780, justify="left").pack(anchor="w", padx=16, pady=(10, 2))
                theme.label(note, s["announcement_body"], 10, C["text"], C["yellow"], wraplength=780,
                            justify="left").pack(anchor="w", padx=16)
                if s["announcement_at"]:
                    theme.label(note, "Posted by the administrator • " + s["announcement_at"], 8, C["muted"],
                                C["yellow"]).pack(anchor="w", padx=16, pady=(4, 10))

            # ---- hero ----
            hero = tk.Frame(body, bg=BLUE_PANEL)
            hero.pack(fill="x", padx=28, pady=(0, 16))
            plate = tk.Frame(hero, bg=BLUE_PANEL)       # same colour as the panel = transparent logo
            plate.pack(pady=(16, 6))
            theme.logo_widget(plate, 90, BLUE_PANEL, 40).pack(padx=12, pady=6)     # the Asik logo
            theme.label(hero, s["hero_title"], 20, C["white"], BLUE_PANEL, True, wraplength=760,
                        justify="center").pack()
            theme.label(hero, s["hero_text"], 10, "#E5EDFF", BLUE_PANEL, wraplength=650,
                        justify="center").pack(pady=(6, 18))

            # ---- info cards ----
            cards = db.fetch_all("SELECT * FROM about_items WHERE kind='card' ORDER BY sort_order, item_id")
            self.card_grid(body, cards, big_icon=True)

            # ---- community guidelines ----
            head = tk.Frame(body, bg=C["sidebar_active"])
            head.pack(fill="x", padx=28, pady=(14, 8))
            theme.label(head, s["guidelines_title"], 16, C["white"], C["sidebar_active"], True
                        ).pack(anchor="w", padx=18, pady=(14, 0))
            theme.label(head, s["guidelines_intro"], 10, "#E0F0E3", C["sidebar_active"], wraplength=760,
                        justify="left").pack(anchor="w", padx=18, pady=(2, 14))
            rules = db.fetch_all("SELECT * FROM about_items WHERE kind='guideline' ORDER BY sort_order, item_id")
            numbered = [dict(r, title=f"{n}. {r['title']}") for n, r in enumerate(rules, 1)]
            self.card_grid(body, numbered, big_icon=False)

            if s["rules_text"]:
                notice = theme.card(body, "#FFF6F0")
                notice.pack(fill="x", padx=28, pady=(8, 6))
                tk.Frame(notice, bg=C["red"], height=4).pack(fill="x")
                theme.label(notice, s["rules_title"], 12, C["red"], "#FFF6F0", True
                            ).pack(anchor="w", padx=16, pady=(10, 2))
                theme.label(notice, s["rules_text"], 10, C["text"], "#FFF6F0", wraplength=760, justify="left"
                            ).pack(anchor="w", padx=16, pady=(0, 12))
            theme.button(body, "Go to the Community →", lambda: self.app.navigate("Community"), size=10
                         ).pack(anchor="w", padx=28, pady=(6, 4))

            # ---- developers ----
            self.build_team(body, s)

            # ---- suggestions from every user ----
            self.build_suggestions(body)

            theme.label(body, "Asik • Smart Agriculture, Equipment Rental & Farm Jobs", 9, C["muted"], C["bg"]
                        ).pack(pady=(10, 14))
            self.update_idletasks()
            self.canvas.yview_moveto(top)
        except tk.TclError:                                     # page closed while redrawing
            pass

    def build_team(self, body, s):
        """The developer section: round photo, name, role and wording. View only for everyone."""
        head = tk.Frame(body, bg=C["purple_dark"])
        head.pack(fill="x", padx=28, pady=(18, 8))
        theme.label(head, s["dev_title"], 16, C["white"], C["purple_dark"], True
                    ).pack(anchor="w", padx=18, pady=(14, 0))
        theme.label(head, s["dev_intro"], 10, "#EDE3FF", C["purple_dark"], wraplength=760, justify="left"
                    ).pack(anchor="w", padx=18, pady=(2, 14))
        if self.is_admin:
            theme.button(head, "✏ Edit developers", lambda: AboutEditor(self, 3), bg=C["white"], fg=C["purple_dark"],
                         size=9, pady=4, hover_color=C["purple"]).place(relx=1.0, x=-14, y=12, anchor="ne")

        team = db.fetch_all("SELECT * FROM about_team ORDER BY sort_order, member_id")
        if not team:
            theme.label(body, "The team will be introduced here soon.", 10, C["muted"], C["bg"]).pack(pady=14)
            return
        grid = tk.Frame(body, bg=C["bg"])
        grid.pack(fill="x", padx=24, pady=(0, 4))
        columns = 3
        for col in range(columns):
            grid.columnconfigure(col, weight=1, uniform="team")
        for i, m in enumerate(team):
            r, c = divmod(i, columns)
            box = theme.card(grid)
            box.grid(row=r, column=c, sticky="nsew", padx=5, pady=5)
            tk.Frame(box, bg=C["purple_dark"], height=4).pack(fill="x")
            round_photo(box, m["photo_path"], 110, C["white"]).pack(pady=(14, 6))
            theme.label(box, m["name"], 13, C["dark"], C["white"], True, wraplength=230, justify="center"
                        ).pack(padx=12)
            if m["role"]:
                tk.Label(box, text=f"  {m['role']}  ", bg=C["purple"], fg=C["purple_dark"],
                         font=(theme.FONT, 9, "bold")).pack(pady=(4, 0))
            if m["bio"]:
                theme.label(box, m["bio"], 9, C["muted"], C["white"], wraplength=230, justify="center"
                            ).pack(padx=12, pady=(8, 16))
            else:
                tk.Frame(box, bg=C["white"], height=14).pack()

    # ================================================================
    # "Suggestions? Help us make this application better."
    # ================================================================
    def build_suggestions(self, body):
        """Every user can say what to improve and which features to add. Admins read them in the editor."""
        head = tk.Frame(body, bg=C["green_dark"])
        head.pack(fill="x", padx=28, pady=(18, 0))
        theme.label(head, "Suggestions? Help us make this application better.", 16, C["white"], C["green_dark"],
                    True, wraplength=700, justify="left").pack(anchor="w", padx=18, pady=(14, 0))
        theme.label(head, "Tell us what we should improve and which features you would like to see. "
                          "Every suggestion is read by the Asik administrators.", 10, "#E0F0E3", C["green_dark"],
                    wraplength=760, justify="left").pack(anchor="w", padx=18, pady=(2, 14))
        if self.is_admin:
            waiting = db.fetch_one("SELECT COUNT(*) AS n FROM about_suggestions WHERE status='New'")["n"]
            theme.button(head, f"💡 Read suggestions ({waiting} new)", lambda: AboutEditor(self, 5), bg=C["white"],
                         fg=C["green_dark"], size=9, pady=4, hover_color=C["mint"]
                         ).place(relx=1.0, x=-14, y=12, anchor="ne")

        card = theme.card(body)
        card.pack(fill="x", padx=28, pady=(0, 6))
        form = tk.Frame(card, bg=C["white"])
        form.pack(fill="x", padx=18, pady=12)
        boxes = {}
        for key, caption in (("improve", "💬 What should we improve in the application?"),
                             ("feature", "✨ What features can we add?")):
            theme.field(form, caption)
            box = tk.Text(form, height=4, font=(theme.FONT, 10), relief="solid", bd=1, wrap="word")
            box.pack(fill="x")
            row = tk.Frame(form, bg=C["white"])
            row.pack(fill="x")
            emoji_picker.attach(row, box).pack(side="left")
            boxes[key] = box

        def send():
            improve = boxes["improve"].get("1.0", "end").strip()
            feature = boxes["feature"].get("1.0", "end").strip()
            if len(improve) < 5 and len(feature) < 5:
                return messagebox.showwarning("Suggestion", "Please write at least one idea: what to improve "
                                              "or a feature to add.")
            db.execute("INSERT INTO about_suggestions (user_id, improve, feature) VALUES (%s,%s,%s)",
                       (session.user_id(), improve or None, feature or None))
            messagebox.showinfo("Thank you!", "Your suggestion was sent to the Asik administrators. "
                                              "Thank you for helping us make Asik better.")
            self.build()
        theme.button(form, "Send my suggestion", send, size=10).pack(anchor="w", pady=(10, 0))

        mine = db.fetch_all("SELECT * FROM about_suggestions WHERE user_id=%s ORDER BY created_at DESC LIMIT 3",
                            (session.user_id(),))
        if mine:
            theme.label(card, "Your latest suggestions", 10, C["dark"], C["white"], True
                        ).pack(anchor="w", padx=18, pady=(2, 2))
            state = {"New": "sent", "Read": "read by an administrator", "Done": "done - thank you!"}
            for m in mine:
                text = (m["improve"] or m["feature"] or "")
                text = text if len(text) < 90 else text[:87] + "..."
                theme.label(card, f"•  {text}   ({state.get(m['status'], m['status'])})", 9, C["muted"], C["white"],
                            wraplength=740, justify="left").pack(anchor="w", padx=18)
            tk.Frame(card, bg=C["white"], height=10).pack()

    @staticmethod
    def card_grid(parent, rows, big_icon):
        """Draw database rows (icon, title, body) as cards in two columns."""
        grid = tk.Frame(parent, bg=C["bg"])
        grid.pack(fill="x", padx=24, pady=(0, 4))
        for col in range(2):
            grid.columnconfigure(col, weight=1, uniform="cards")
        for i, row in enumerate(rows):
            r, c = divmod(i, 2)
            accent = ACCENTS[i % len(ACCENTS)]
            box = theme.card(grid)
            box.grid(row=r, column=c, sticky="nsew", padx=5, pady=5)
            tk.Frame(box, bg=accent, height=4).pack(fill="x")
            icon = row["icon"] or ""
            if big_icon:
                theme.label(box, icon, 26, accent, C["white"]).pack(anchor="w", padx=15, pady=(12, 4))
                theme.label(box, row["title"], 13, C["dark"], C["white"], True).pack(anchor="w", padx=15)
            else:                                           # guideline: icon and title on one line
                line = tk.Frame(box, bg=C["white"])
                line.pack(fill="x", padx=15, pady=(12, 0))
                theme.label(line, icon, 18, accent, C["white"]).pack(side="left")
                theme.label(line, "  " + row["title"], 12, C["dark"], C["white"], True).pack(side="left")
            theme.label(box, row["body"], 9, C["muted"], C["white"], wraplength=380, justify="left"
                        ).pack(anchor="w", padx=15, pady=(6, 16))

    def on_wheel(self, event):
        try:
            if isinstance(event.widget, tk.Misc) and event.widget.winfo_toplevel() is self.winfo_toplevel():
                self.canvas.yview_scroll(theme.wheel_step(event), "units")
        except tk.TclError:
            pass

    def destroy(self):
        try:
            self.unbind_all("<MouseWheel>")
            theme.unbind_scroll_keys(self)
        except tk.TclError:
            pass
        super().destroy()
