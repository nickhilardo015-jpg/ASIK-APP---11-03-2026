"""
dashboard_page.py  --  Home page after login.

Shows live numbers from MySQL (equipment, vacancies, companies, and
numbers about the user's own activity) and quick-access buttons.
"""

import tkinter as tk

import database as db
import language
import session
import theme
from theme import C


class DashboardPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        uid = session.user_id()
        name = session.user["full_name"].split()[0]
        theme.page_header(self, f"{language.t('dash.good_day')} {name}! ☀️",
                          language.t("dash.subtitle"))

        hero = tk.Frame(self, bg="#4A8A5E")           # lighter green
        hero.pack(fill="x", padx=28, pady=(0, 16))
        left = tk.Frame(hero, bg="#4A8A5E")           # match
        left.pack(side="left", fill="both", expand=True, padx=22, pady=16)
        theme.label(left, language.t("dash.hero_tagline"), 9, "#F6D875", "#4A8A5E", True).pack(anchor="w")
        theme.label(left, language.t("dash.hero_title"), 20, C["white"], "#4A8A5E", True
                    ).pack(anchor="w", pady=(6, 2))
        theme.label(left, language.t("dash.hero_desc"),
                    10, "#E0F0E3", "#4A8A5E").pack(anchor="w", pady=(0, 10))
        theme.button(left, language.t("dash.btn_explore"), lambda: app.navigate("Equipment Rental"),
                bg=C["yellow"], fg=C["dark"], size=9, hover_color="#F5D98A").pack(side="left")
        theme.button(left, language.t("dash.btn_jobs"), lambda: app.navigate("Hiring Now!"),
                    bg=C["white"], fg=C["dark"], size=9, hover_color=C["mint"]
                    ).pack(side="left", padx=8)

        plate = tk.Frame(hero, bg="#4A8A5E")
        plate.pack(side="right", padx=22, pady=12)
        theme.logo_widget(plate, 90, "#4A8A5E", 40).pack(padx=10, pady=6)

        # ---------- statistic cards (numbers come from MySQL) ----------
        n_equip = db.fetch_one("SELECT COUNT(*) n FROM equipment WHERE is_available=1")["n"]
        n_jobs = db.fetch_one("SELECT COUNT(*) n FROM job_vacancies WHERE status='Open'")["n"]
        n_comp = db.fetch_one("SELECT COUNT(*) n FROM companies")["n"]
        n_unread = db.fetch_one("SELECT COUNT(*) n FROM messages WHERE receiver_id=%s AND is_read=0",
                                (uid,))["n"]
        stats = tk.Frame(self, bg=C["bg"])
        stats.pack(fill="x", padx=23)
        for i, (icon, title_key, value, accent) in enumerate([
            ("🚜", "dash.stat_equip",  n_equip,  C["green"]),
            ("📢", "dash.stat_jobs",   n_jobs,   C["blue_dark"]),
            ("🏢", "dash.stat_farms",  n_comp,   C["yellow_dark"]),
            ("💬", "dash.stat_unread", n_unread, C["purple_dark"]),
        ]):
            box = theme.card(stats)
            box.grid(row=0, column=i, sticky="nsew", padx=5)
            stats.columnconfigure(i, weight=1, uniform="stats")
            tk.Frame(box, bg=accent, height=4).pack(fill="x")
            theme.label(box, icon, 22, accent, C["white"]).pack(anchor="w", padx=14, pady=(10, 2))
            theme.label(box, language.t(title_key), 9, C["muted"], C["white"]).pack(anchor="w", padx=14)
            theme.label(box, f"{value:,}", 22, accent, C["white"], True).pack(anchor="w", padx=14, pady=(0, 10))

        # ---------- quick access (depends on role) ----------
        quick = [
            ("🚜", "dash.qa_rent",  "dash.qa_rent_desc",  C["mint"],   "Equipment Rental"),
            ("📢", "dash.qa_jobs",  "dash.qa_jobs_desc",  C["blue"],   "Hiring Now!"),
            ("💬", "dash.qa_msg",   "dash.qa_msg_desc",   C["purple"], "Messages"),
        ]
        if session.has_role("job_seeker"):
            quick.append(("📝", "dash.qa_apply", "dash.qa_apply_desc", C["yellow"], "Apply for a Job"))
        if session.has_role("employer"):
            quick.append(("👥", "dash.qa_applicants", "dash.qa_applicants_desc",
                          C["yellow"], "Applicants Portal"))
        if session.has_role("lender"):
            quick.append(("🤝", "dash.qa_lend", "dash.qa_lend_desc",
                          C["yellow"], "Lend My Equipment"))

        panel = theme.card(self)
        panel.pack(fill="both", expand=True, padx=28, pady=16)
        theme.label(panel, language.t("dash.quick_access"), 14, C["dark"], C["white"], True
                    ).pack(anchor="w", padx=16, pady=(12, 6))
        for icon, title_key, desc_key, tint, target in quick:
            row = tk.Frame(panel, bg=tint)
            row.pack(fill="x", padx=14, pady=4)
            theme.label(row, icon, 20, C["dark"], tint).pack(side="left", padx=12, pady=8)
            info = tk.Frame(row, bg=tint)
            info.pack(side="left", fill="x", expand=True)
            theme.label(info, language.t(title_key), 10, C["dark"], tint, True).pack(anchor="w")
            theme.label(info, language.t(desc_key), 9, C["muted"], tint).pack(anchor="w")
            theme.button(row, language.t("dash.btn_open"), lambda t=target: app.navigate(t),
                         bg=C["white"], fg=C["dark"], size=8, hover_color=C["mint"]
                         ).pack(side="right", padx=9)