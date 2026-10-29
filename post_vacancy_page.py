"""
post_vacancy_page.py  --  EMPLOYERS: list a vacancy for your farm / company.

The employer fills in a form (job title, level, description, salary per day
in Philippine peso, days and hours per week, number of open slots).
Picking a ready-made job template auto-fills the form so it is quick.
Below the form the employer sees all of their listings and can
Close / Re-open / Delete them. The employer can also register an extra
farm (company) with a full address.
Data: MySQL tables `job_vacancies` and `companies`.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import database as db
import language
import session
import theme
from setup_database import JOBS          # ready-made job templates
from theme import C


class PostVacancyPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.my_companies = []
        theme.page_header(self, language.t("postvac.title"), language.t("postvac.subtitle"),
                          C["blue_dark"])
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 14))

        # ================= LEFT: vacancy form =================
        left = theme.card(body)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.configure(width=420)
        scroll = theme.Scrollable(left, C["white"])
        scroll.pack(fill="both", expand=True)
        f = tk.Frame(scroll.inner, bg=C["white"])
        f.pack(fill="x", padx=16, pady=8)

        theme.label(f, language.t("postvac.new_vacancy"), 13, C["blue_dark"], C["white"], True
                    ).pack(anchor="w")
        theme.field(f, language.t("postvac.farm_company"))
        self.company_var = tk.StringVar()
        self.company_cb = ttk.Combobox(f, textvariable=self.company_var, state="readonly")
        self.company_cb.pack(fill="x")
        self.company_cb.bind("<<ComboboxSelected>>", self.show_address)
        self.address_lbl = theme.label(f, "", 8, C["muted"], C["white"], wraplength=370, justify="left")
        self.address_lbl.pack(anchor="w", pady=(2, 0))
        theme.button(f, language.t("postvac.register_another"), self.add_company_dialog,
                     bg=C["purple_dark"], size=8, hover_color=C["blue_dark"]
                     ).pack(anchor="w", pady=(4, 0))

        theme.field(f, language.t("postvac.template_label"))
        self.template_var = tk.StringVar()
        tcb = ttk.Combobox(f, textvariable=self.template_var, state="readonly",
                           values=[f"{j[1]}: {j[0]}" for j in JOBS])
        tcb.pack(fill="x")
        tcb.bind("<<ComboboxSelected>>", self.apply_template)

        self.v = {k: tk.StringVar() for k in ("title", "salary", "days", "hours", "slots")}
        self.level = tk.StringVar(value="Laborer")
        theme.field(f, language.t("postvac.job_title"))
        theme.entry(f, self.v["title"]).pack(fill="x", ipady=5)
        theme.field(f, language.t("postvac.job_level"))
        ttk.Combobox(f, textvariable=self.level, state="readonly",
                     values=["Expert", "Skilled", "Laborer"]).pack(fill="x")
        theme.field(f, language.t("postvac.job_description"))
        self.desc = tk.Text(f, height=4, font=(theme.FONT, 10), relief="solid", bd=1, wrap="word")
        self.desc.pack(fill="x")

        grid = tk.Frame(f, bg=C["white"])
        grid.pack(fill="x")
        for i, (cap_key, key) in enumerate([("postvac.salary_per_day", "salary"),
                                            ("postvac.days_per_week",  "days"),
                                            ("postvac.hours_per_week", "hours"),
                                            ("postvac.open_slots",     "slots")]):
            col = tk.Frame(grid, bg=C["white"])
            col.grid(row=0, column=i, sticky="ew", padx=(0, 6))
            grid.columnconfigure(i, weight=1)
            theme.field(col, language.t(cap_key))
            theme.entry(col, self.v[key], width=7).pack(fill="x", ipady=5)
        theme.label(f, language.t("postvac.wage_tip"), 8, C["yellow_dark"], C["white"],
                    wraplength=370, justify="left").pack(anchor="w", pady=(8, 0))
        theme.button(f, language.t("postvac.publish_btn"), self.publish).pack(fill="x", pady=14)

        # ================= RIGHT: my vacancies =================
        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        theme.label(right, language.t("postvac.my_vacancies"), 13, C["dark"], C["bg"], True
                    ).pack(anchor="w")
        cols = ("id", "job", "farm", "salary", "week", "slots", "status")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=16)
        for col, title_key, w in (("id",     "postvac.col_id",      35),
                                  ("job",    "postvac.col_job",    140),
                                  ("farm",   "postvac.col_farm",   150),
                                  ("salary", "postvac.col_salary",  70),
                                  ("week",   "postvac.col_week",    70),
                                  ("slots",  "postvac.col_slots",   45),
                                  ("status", "postvac.col_status",  60)):
            self.tree.heading(col, text=language.t(title_key))
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=(4, 8))
        bar = tk.Frame(right, bg=C["bg"])
        bar.pack(fill="x")
        theme.button(bar, language.t("postvac.toggle_btn"), self.toggle, bg=C["blue_dark"], size=9,
                     hover_color=C["purple_dark"]).pack(side="left")
        theme.button(bar, language.t("postvac.delete_btn"), self.delete, bg=C["red"], size=9,
                     hover_color="#8F3030").pack(side="left", padx=8)
        self.load_companies()
        self.load()

    # ---------------- helpers ----------------
    def load_companies(self):
        self.my_companies = db.fetch_all(
            "SELECT * FROM companies WHERE owner_user_id=%s ORDER BY company_name",
            (session.user_id(),))
        self.company_cb["values"] = [c["company_name"] for c in self.my_companies]
        if self.my_companies:
            self.company_cb.current(0)
            self.show_address()

    def show_address(self, _e=None):
        """Show the chosen company's full address under the drop-down (auto-fill)."""
        idx = self.company_cb.current()
        self.address_lbl.configure(
            text=f"📍 {self.my_companies[idx]['full_address']}" if idx >= 0 else "")

    def apply_template(self, _e=None):
        """Fill the form from the chosen job template."""
        labels = [f"{x[1]}: {x[0]}" for x in JOBS]
        if self.template_var.get() not in labels:
            return
        title, level, desc, salary, days, hours = JOBS[labels.index(self.template_var.get())]
        self.v["title"].set(title)
        self.level.set(level)
        self.desc.delete("1.0", "end")
        self.desc.insert("1.0", desc)
        self.v["salary"].set(str(salary))
        self.v["days"].set(str(days))
        self.v["hours"].set(str(hours))
        self.v["slots"].set("1")

    def load(self):
        self.tree.delete(*self.tree.get_children())
        for v in db.fetch_all(
                "SELECT v.*, c.company_name FROM job_vacancies v "
                "JOIN companies c ON c.company_id=v.company_id "
                "WHERE c.owner_user_id=%s ORDER BY v.vacancy_id DESC", (session.user_id(),)):
            self.tree.insert("", "end", iid=str(v["vacancy_id"]), values=(
                v["vacancy_id"], v["job_title"], v["company_name"],
                theme.peso(v["salary_per_day"]),
                f"{v['days_per_week']}d/{v['hours_per_week']}h",
                v["slots"], v["status"]))

    # ---------------- actions ----------------
    def publish(self):
        """Validate the form and INSERT the vacancy."""
        idx = self.company_cb.current()
        if idx < 0:
            return messagebox.showwarning(language.t("postvac.err_farm_title"),
                                          language.t("postvac.err_farm_msg"))
        try:
            salary = float(self.v["salary"].get().replace(",", ""))
            days = int(self.v["days"].get())
            hours = int(self.v["hours"].get())
            slots = int(self.v["slots"].get() or 1)
            assert salary > 0 and 1 <= days <= 7 and 1 <= hours <= 84 and slots >= 1
        except (ValueError, AssertionError):
            return messagebox.showwarning(language.t("postvac.err_numbers_title"),
                                          language.t("postvac.err_numbers_msg"))
        title = self.v["title"].get().strip()
        desc = self.desc.get("1.0", "end").strip()
        if not title or not desc:
            return messagebox.showwarning(language.t("postvac.err_missing_title"),
                                          language.t("postvac.err_missing_msg"))
        db.execute(
            "INSERT INTO job_vacancies (company_id, posted_by, job_title, job_level, description, "
            "salary_per_day, days_per_week, hours_per_week, slots) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (self.my_companies[idx]["company_id"], session.user_id(), title, self.level.get(),
             desc, salary, days, hours, slots))
        for var in self.v.values():
            var.set("")
        self.desc.delete("1.0", "end")
        self.template_var.set("")
        self.load()
        messagebox.showinfo(language.t("postvac.published_title"),
                            language.t("postvac.published_msg"))

    def toggle(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning(language.t("postvac.select_title"),
                                          language.t("postvac.select_msg"))
        db.execute("UPDATE job_vacancies SET status = IF(status='Open','Closed','Open') "
                   "WHERE vacancy_id=%s", (int(sel[0]),))
        self.load()

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning(language.t("postvac.select_title"),
                                          language.t("postvac.select_msg"))
        if messagebox.askyesno(language.t("postvac.delete_title"),
                               language.t("postvac.delete_msg")):
            db.execute("DELETE FROM job_vacancies WHERE vacancy_id=%s", (int(sel[0]),))
            self.load()

    def add_company_dialog(self):
        """Pop-up to register another farm; the full address is built from the pickers."""
        win = tk.Toplevel(self)
        win.title(language.t("postvac.regfarm_title"))
        win.geometry("400x520")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()
        theme.label(win, "🏢 " + language.t("postvac.regfarm_title"), 14, C["blue_dark"],
                    C["white"], True).pack(anchor="w", padx=22, pady=(18, 4))
        form = tk.Frame(win, bg=C["white"])
        form.pack(fill="x", padx=22)
        name, street = tk.StringVar(), tk.StringVar()
        theme.field(form, language.t("postvac.regfarm_name"))
        theme.entry(form, name).pack(fill="x", ipady=5)
        theme.field(form, language.t("postvac.regfarm_street"))
        theme.entry(form, street).pack(fill="x", ipady=5)
        theme.label(form, language.t("postvac.regfarm_location"), 8, C["dark"], C["white"], True
                    ).pack(anchor="w", pady=(10, 2))
        picker = theme.LocationPicker(form, all_option=False)
        picker.pack(fill="x")

        def save():
            region, province, muni = picker.get()[:3]
            if not name.get().strip() or not (region and province and muni):
                return messagebox.showwarning(language.t("postvac.err_missing_title"),
                                              language.t("postvac.regfarm_missing_msg"),
                                              parent=win)
            full = ", ".join(x for x in (street.get().strip(), muni, province, region,
                                          "Philippines") if x)
            db.execute(
                "INSERT INTO companies (company_name, owner_user_id, street, municipality, "
                "province, region, full_address) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (name.get().strip(), session.user_id(), street.get().strip(),
                 muni, province, region, full))
            win.destroy()
            self.load_companies()

        theme.button(win, language.t("postvac.regfarm_save"), save
                     ).pack(fill="x", padx=22, pady=16)