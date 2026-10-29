"""
jobs_page.py  --  "Hiring Now!" job board.

Shows farm jobs from EXPERTS (agronomist, veterinarian...) down to
LABORERS (farm laborer, harvester...). Each card has:
    job description, salary per day in Philippine peso, days per week,
    hours per week, estimated weekly pay, the farm/company name and its
    FULL ADDRESS.
Filters: search text, job level, and Region -> Province -> Municipality.
"Apply Now" opens the application form (apply_page.py) with this job
already selected. Data: MySQL tables `job_vacancies` and `companies`.
"""

import tkinter as tk

import database as db
import language
import session
import theme
from theme import C

LEVEL_COLORS = {"Expert": (C["purple"], C["purple_dark"]),
                "Skilled": (C["blue"], C["blue_dark"]),
                "Laborer": (C["mint"], C["green_dark"])}


class JobsPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.level = "All Jobs"
        theme.page_header(self, language.t("jobs.title"),
                          language.t("jobs.subtitle"),
                          C["blue_dark"])

        # ---------- search + filters ----------
        self.search = theme.SearchBar(self, self.refresh, language.t("jobs.search_placeholder"))
        self.search.pack(fill="x", padx=28, pady=(0, 8))

        panel = theme.card(self)
        panel.pack(fill="x", padx=28, pady=(0, 8))
        theme.label(panel, language.t("jobs.filter_by_address"), 9, C["blue_dark"], C["white"], True
                    ).pack(anchor="w", padx=12, pady=(8, 0))
        self.location = theme.LocationPicker(panel, all_option=True, horizontal=True)
        self.location.pack(fill="x", padx=12, pady=(2, 4))
        bar = tk.Frame(panel, bg=C["white"])
        bar.pack(fill="x", padx=12, pady=(0, 10))
        self.level_buttons = {}
        for lvl_value, lvl_key in (("All Jobs", "jobs.lvl_all"),
                                   ("Expert",   "jobs.lvl_expert"),
                                   ("Skilled",  "jobs.lvl_skilled"),
                                   ("Laborer",  "jobs.lvl_laborer")):
            b = theme.button(bar, language.t(lvl_key), lambda x=lvl_value: self.set_level(x),
                             bg=C["white"], fg=C["text"], size=9, hover_color=C["mint"])
            b.pack(side="left", padx=(0, 6))
            self.level_buttons[lvl_value] = b
        theme.button(bar, language.t("common.search"), self.refresh, size=9).pack(side="right")
        theme.button(bar, language.t("jobs.reset_filters"), self.reset, bg=C["muted"], size=9,
                     hover_color=C["dark"]).pack(side="right", padx=6)
        self.count_lbl = theme.label(bar, "", 9, C["muted"], C["white"])
        self.count_lbl.pack(side="right", padx=12)

        self.area = theme.Scrollable(self)
        self.area.pack(fill="both", expand=True, padx=22, pady=(0, 10))
        self.set_level("All Jobs")

    def set_level(self, lvl):
        self.level = lvl
        for name, b in self.level_buttons.items():
            b.configure(bg=C["blue_dark"] if name == lvl else C["white"],
                        fg=C["white"] if name == lvl else C["text"])
        self.refresh()

    def reset(self):
        self.location.reset()
        self.search.entry.delete(0, "end")
        self.search._show_placeholder()
        self.set_level("All Jobs")

    def refresh(self):
        """Query MySQL using all the filters and redraw the job cards."""
        sql = ("SELECT v.*, c.company_name, c.full_address, c.owner_user_id AS owner_id "
               "FROM job_vacancies v JOIN companies c ON c.company_id=v.company_id "
               "WHERE v.status='Open'")
        params = []
        if self.level != "All Jobs":
            sql += " AND v.job_level=%s"
            params.append(self.level)
        region, province, muni, _barangay = self.location.get()
        for col, val in (("region", region), ("province", province), ("municipality", muni)):
            if val:
                sql += f" AND c.{col}=%s"
                params.append(val)
        text = self.search.text()
        if text:
            sql += " AND (v.job_title LIKE %s OR v.description LIKE %s OR c.company_name LIKE %s)"
            params += [f"%{text}%"] * 3
        sql += (" ORDER BY FIELD(v.job_level,'Expert','Skilled','Laborer'), "
                "v.salary_per_day DESC")
        jobs = db.fetch_all(sql, params)
        self.count_lbl.configure(text=f"{len(jobs)} {language.t('jobs.job_count')}")

        inner = self.area.inner
        theme.clear(inner)
        if not jobs:
            theme.label(inner, language.t("jobs.no_results"), 12, C["muted"]).pack(pady=40)
            return
        for col in range(2):
            inner.columnconfigure(col, weight=1, uniform="jobs")
        for i, job in enumerate(jobs):
            r, c = divmod(i, 2)
            self.draw_card(inner, job).grid(row=r, column=c, sticky="nsew", padx=5, pady=6)

    def draw_card(self, parent, job):
        tint, accent = LEVEL_COLORS[job["job_level"]]
        # level badge text (translated)
        level_key = {"Expert": "jobs.lvl_expert",
                     "Skilled": "jobs.lvl_skilled",
                     "Laborer": "jobs.lvl_laborer"}.get(job["job_level"], job["job_level"])
        level_text = language.t(level_key).upper()

        box = theme.card(parent)
        tk.Frame(box, bg=accent, height=4).pack(fill="x")
        top = tk.Frame(box, bg=C["white"])
        top.pack(fill="x", padx=14, pady=(10, 0))
        theme.label(top, job["job_title"], 13, C["dark"], C["white"], True).pack(side="left")
        theme.label(top, f" {level_text} ", 8, accent, tint, True).pack(side="right")

        theme.label(box, f"🏢 {job['company_name']}", 10, C["green_dark"], C["white"], True
                    ).pack(anchor="w", padx=14, pady=(4, 0))
        theme.label(box, f"📍 {job['full_address']}", 8, C["muted"], C["white"], wraplength=420,
                    justify="left").pack(anchor="w", padx=14)
        theme.label(box, job["description"], 9, C["text"], C["white"], wraplength=420, justify="left"
                    ).pack(anchor="w", padx=14, pady=(6, 4))

        # salary + schedule row
        weekly = float(job["salary_per_day"]) * job["days_per_week"]
        info = tk.Frame(box, bg=tint)
        info.pack(fill="x", padx=14, pady=4)
        for text in (
            f"💰 {theme.peso(job['salary_per_day'])} {language.t('jobs.per_day')}",
            f"📅 {job['days_per_week']} {language.t('jobs.days_per_week')}",
            f"⏱ {job['hours_per_week']} {language.t('jobs.hrs_per_week')}",
            f"≈ {theme.peso(weekly)}{language.t('jobs.per_week')}",
        ):
            theme.label(info, text, 9, C["dark"], tint, True).pack(side="left", padx=8, pady=6)
        theme.label(box, f"{language.t('jobs.open_positions')}: {job['slots']}",
                    8, C["muted"], C["white"]).pack(anchor="w", padx=14)

        row = tk.Frame(box, bg=C["white"])
        row.pack(fill="x", padx=12, pady=(6, 12))
        if session.has_role("job_seeker"):
            theme.button(row, language.t("jobs.apply_now"),
                         lambda j=job: self.app.navigate(
                             "Apply for a Job", vacancy_id=j["vacancy_id"]),
                         bg=accent, size=9, hover_color=C["dark"]).pack(side="left")
        if job["owner_id"] and job["owner_id"] != session.user_id():
            theme.button(row, language.t("jobs.message_employer"),
                         lambda j=job: self.app.navigate(
                             "Messages", to_user=j["owner_id"]),
                         bg=C["purple_dark"], size=9,
                         hover_color=C["blue_dark"]).pack(side="left", padx=6)
        return box