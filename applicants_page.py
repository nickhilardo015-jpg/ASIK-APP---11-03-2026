"""
applicants_page.py  --  EMPLOYER PORTAL: see who applied and act on it.

For every applicant to the employer's vacancies the employer can:
    ✅ Hire              - status becomes 'Hired', one slot is used up and the
                           applicant is notified by an automatic message
    📅 Invite Interview  - pick date, time and place; a message is sent
    ❌ Reject            - status becomes 'Rejected'
    💬 Message           - open the chat with the applicant
Data: MySQL tables `job_applications`, `job_vacancies`, `companies`, `messages`.
"""

import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

import database as db
import language
import session
import theme
from theme import C


class ApplicantsPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.rows = {}
        theme.page_header(self, language.t("applicants.title"),
                          language.t("applicants.subtitle"),
                          C["blue_dark"])

        # ---------- search + status filter ----------
        top = tk.Frame(self, bg=C["bg"])
        top.pack(fill="x", padx=28, pady=(0, 8))
        self.search = theme.SearchBar(top, self.load, language.t("applicants.search_placeholder"))
        self.search.pack(side="left", fill="x", expand=True)
        self.status_var = tk.StringVar(value="All")
        cb = ttk.Combobox(top, textvariable=self.status_var, state="readonly", width=12,
                          values=["All", "Pending", "Interview", "Hired", "Rejected"])
        cb.pack(side="left", padx=8)
        cb.bind("<<ComboboxSelected>>", lambda e: self.load())

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 14))

        # ---------- table of applicants ----------
        cols = ("id", "name", "job", "farm", "phone", "status")
        self.tree = ttk.Treeview(body, columns=cols, show="headings")
        for col, title_key, w in (("id",     "applicants.col_id",      35),
                                  ("name",   "applicants.col_name",   140),
                                  ("job",    "applicants.col_job",    140),
                                  ("farm",   "applicants.col_farm",   140),
                                  ("phone",  "applicants.col_phone",  100),
                                  ("status", "applicants.col_status",  75)):
            self.tree.heading(col, text=language.t(title_key))
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_detail)

        # ---------- detail panel + action buttons ----------
        self.detail = theme.card(body)
        self.detail.pack(side="right", fill="y", padx=(12, 0))
        self.detail.configure(width=320)
        self.detail.pack_propagate(False)
        self.load()
        self.show_detail()

    def load(self):
        """Fill the table with applicants of MY companies (filters applied)."""
        sql = ("SELECT a.*, v.job_title, c.company_name FROM job_applications a "
               "JOIN job_vacancies v ON v.vacancy_id=a.vacancy_id "
               "JOIN companies c ON c.company_id=a.company_id WHERE c.owner_user_id=%s")
        params = [session.user_id()]
        if self.status_var.get() != "All":
            sql += " AND a.status=%s"
            params.append(self.status_var.get())
        text = self.search.text()
        if text:
            sql += " AND (a.full_name LIKE %s OR v.job_title LIKE %s OR a.skills LIKE %s)"
            params += [f"%{text}%"] * 3
        sql += " ORDER BY a.application_id DESC"
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        for a in db.fetch_all(sql, params):
            self.rows[str(a["application_id"])] = a
            self.tree.insert("", "end", iid=str(a["application_id"]),
                             values=(a["application_id"], a["full_name"], a["job_title"],
                                     a["company_name"], a["contact_number"], a["status"]))

    def selected(self):
        sel = self.tree.selection()
        return self.rows.get(sel[0]) if sel else None

    def show_detail(self, _e=None):
        """Right-hand panel: full applicant information + the action buttons."""
        theme.clear(self.detail)
        a = self.selected()
        if not a:
            theme.label(self.detail, language.t("applicants.select_prompt"), 10,
                        C["muted"], C["white"]).pack(pady=40)
            return
        theme.label(self.detail, a["full_name"], 14, C["dark"], C["white"], True
                    ).pack(anchor="w", padx=14, pady=(14, 0))
        theme.label(self.detail,
                    language.t("applicants.applied_for") + f": {a['job_title']}",
                    9, C["green_dark"], C["white"], True).pack(anchor="w", padx=14)
        theme.label(self.detail,
                    language.t("applicants.status") + f": {a['status']}",
                    9, C["blue_dark"], C["white"], True).pack(anchor="w", padx=14, pady=(0, 6))
        lines = [
            ("applicants.lbl_age",        a["age"] or "-"),
            ("applicants.lbl_phone",      a["contact_number"]),
            ("applicants.lbl_email",      a["email"] or "-"),
            ("applicants.lbl_address",    ", ".join(x for x in (a["address"], a["municipality"], a["province"]) if x)),
            ("applicants.lbl_skills",     a["skills"] or "-"),
            ("applicants.lbl_experience", a["experience"] or "-"),
        ]
        for cap_key, val in lines:
            theme.label(self.detail, language.t(cap_key).upper(), 7, C["muted"], C["white"], True
                        ).pack(anchor="w", padx=14, pady=(4, 0))
            theme.label(self.detail, str(val), 9, C["text"], C["white"], wraplength=285,
                        justify="left").pack(anchor="w", padx=14)
        bar = tk.Frame(self.detail, bg=C["white"])
        bar.pack(fill="x", padx=14, pady=14, side="bottom")
        theme.button(bar, language.t("applicants.hire_btn"), self.hire, size=10
                     ).pack(fill="x", pady=2)
        theme.button(bar, language.t("applicants.interview_btn"), self.interview,
                     bg=C["blue_dark"], size=9, hover_color=C["purple_dark"]
                     ).pack(fill="x", pady=2)
        theme.button(bar, language.t("applicants.message_btn"),
                     lambda: self.app.navigate("Messages", to_user=a["applicant_id"]),
                     bg=C["purple_dark"], size=9, hover_color=C["blue_dark"]
                     ).pack(fill="x", pady=2)
        theme.button(bar, language.t("applicants.reject_btn"), self.reject,
                     bg=C["red"], size=9, hover_color="#8F3030").pack(fill="x", pady=2)

    # ---------------- actions ----------------
    def send(self, receiver, text):
        """Put a message in the chat table."""
        db.execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (%s,%s,%s)",
                   (session.user_id(), receiver, text))

    def reselect(self, app_id):
        self.load()
        if str(app_id) in self.rows:
            self.tree.selection_set(str(app_id))
        self.show_detail()

    def hire(self):
        a = self.selected()
        if not a:
            return
        if a["status"] == "Hired":
            return messagebox.showinfo(language.t("applicants.already_hired_title"),
                                       language.t("applicants.already_hired_msg"))
        if not messagebox.askyesno(language.t("applicants.hire_title"),
                                   language.t("applicants.hire_confirm").format(
                                       name=a["full_name"], job=a["job_title"])):
            return
        db.execute("UPDATE job_applications SET status='Hired' WHERE application_id=%s",
                   (a["application_id"],))
        # one slot is filled; close the vacancy when no slots are left
        db.execute("UPDATE job_vacancies SET slots = GREATEST(slots-1,0), "
                   "status = IF(slots<=0,'Closed',status) WHERE vacancy_id=%s",
                   (a["vacancy_id"],))
        # (MySQL applies assignments left to right, so `slots` here is already the new value)
        self.send(a["applicant_id"],
                  language.t("applicants.hire_message").format(
                      name=a["full_name"], job=a["job_title"], farm=a["company_name"]))
        messagebox.showinfo(language.t("applicants.hired_title"),
                            language.t("applicants.hired_msg").format(name=a["full_name"]))
        self.reselect(a["application_id"])

    def reject(self):
        a = self.selected()
        if a and messagebox.askyesno(language.t("applicants.reject_title"),
                                     language.t("applicants.reject_confirm").format(
                                         name=a["full_name"])):
            db.execute("UPDATE job_applications SET status='Rejected' WHERE application_id=%s",
                       (a["application_id"],))
            self.send(a["applicant_id"],
                      language.t("applicants.reject_message").format(
                          name=a["full_name"], job=a["job_title"]))
            self.reselect(a["application_id"])

    def interview(self):
        """Pop-up asking for date/time/place, then message the applicant."""
        a = self.selected()
        if not a:
            return
        win = tk.Toplevel(self)
        win.title(language.t("applicants.interview_title"))
        win.geometry("380x380")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()
        theme.label(win, language.t("applicants.interview_header"), 14,
                    C["blue_dark"], C["white"], True).pack(anchor="w", padx=22, pady=(18, 0))
        form = tk.Frame(win, bg=C["white"])
        form.pack(fill="x", padx=22)
        d = tk.StringVar(value=date.today().isoformat())
        t = tk.StringVar(value="09:00 AM")
        place = tk.StringVar(value=a["company_name"])
        theme.field(form, language.t("applicants.interview_date"))
        theme.entry(form, d).pack(fill="x", ipady=5)
        theme.field(form, language.t("applicants.interview_time"))
        ttk.Combobox(form, textvariable=t, state="readonly",
                     values=[f"{h:02d}:00 {s}" for s in ("AM", "PM")
                             for h in (8, 9, 10, 11, 1, 2, 3, 4)]).pack(fill="x")
        theme.field(form, language.t("applicants.interview_place"))
        theme.entry(form, place).pack(fill="x", ipady=5)

        def send():
            try:
                datetime.strptime(d.get().strip(), "%Y-%m-%d")
            except ValueError:
                return messagebox.showerror(language.t("applicants.interview_date_title"),
                                            language.t("applicants.interview_date_msg"),
                                            parent=win)
            db.execute("UPDATE job_applications SET status='Interview' WHERE application_id=%s",
                       (a["application_id"],))
            self.send(a["applicant_id"],
                      language.t("applicants.interview_message").format(
                          name=a["full_name"], job=a["job_title"],
                          date=d.get().strip(), time=t.get(), place=place.get()))
            win.destroy()
            self.reselect(a["application_id"])
            messagebox.showinfo(language.t("applicants.interview_sent_title"),
                                language.t("applicants.interview_sent_msg"))

        theme.button(win, language.t("applicants.interview_send"), send
                     ).pack(fill="x", padx=22, pady=18)