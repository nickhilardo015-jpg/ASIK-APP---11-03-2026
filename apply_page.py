"""
apply_page.py  --  Job application form for JOB SEEKERS (full CRUD).

    C = Create  : fill in the form and press "Submit Application"
    R = Read    : the table on the right lists your own applications
    U = Update  : click a row, change the form, press "Update Application"
    D = Delete  : click a row and press "Withdraw (Delete)"

The form CLEARS ITSELF automatically after a successful submit.

Choosing the farm (auto-fill):
    1. pick a Region      -> the Province list shows that region's provinces
    2. pick a Province    -> the Municipality list shows its towns/cities
    3. the Farm list shows only farms with open jobs in that area
    4. pick a Farm        -> its FULL ADDRESS is filled in automatically
                             and its open jobs appear in the Job list
Data: MySQL tables `job_applications`, `companies`, `job_vacancies`.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import database as db
import session
import theme
from theme import C


class ApplyPage(tk.Frame):
    def __init__(self, parent, app, vacancy_id=None):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.editing_id = None            # application being edited (None = new)
        self.companies = []               # companies shown in the Farm drop-down
        self.vacancies = []               # jobs shown in the Job drop-down

        theme.page_header(self, "Apply for a Job 📝",
                          "Pick a farm, choose a job and send your application. Employers will contact you.",
                          C["green_dark"])
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 14))

        # =============== LEFT: the form (scrolls if the window is small) ===============
        left = theme.card(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        scroll = theme.Scrollable(left, C["white"])
        scroll.pack(fill="both", expand=True)
        f = tk.Frame(scroll.inner, bg=C["white"])
        f.pack(fill="x", padx=16, pady=8)

        # ----- 1. the farm -----
        self.mode_title = theme.label(f, "1  Choose the farm you want to join", 12, C["green"], C["white"], True)
        self.mode_title.pack(anchor="w")
        self.farm_location = theme.LocationPicker(f, all_option=True, on_change=self.load_companies)
        self.farm_location.pack(fill="x", pady=(4, 0))

        theme.field(f, "Farm / company name")
        self.company_var = tk.StringVar()
        self.company_cb = ttk.Combobox(f, textvariable=self.company_var, state="readonly")
        self.company_cb.pack(fill="x")
        self.company_cb.bind("<<ComboboxSelected>>", self.company_picked)

        theme.field(f, "Farm address (filled in automatically)")
        self.address_var = tk.StringVar()
        tk.Entry(f, textvariable=self.address_var, state="readonly", font=(theme.FONT, 9),
                 readonlybackground=C["mint"], relief="solid", bd=1).pack(fill="x", ipady=6)

        theme.field(f, "Job you are applying for")
        self.job_var = tk.StringVar()
        self.job_cb = ttk.Combobox(f, textvariable=self.job_var, state="readonly")
        self.job_cb.pack(fill="x")

        # ----- 2. about you -----
        theme.label(f, "2  About you", 12, C["green"], C["white"], True).pack(anchor="w", pady=(16, 0))
        self.v = {k: tk.StringVar() for k in ("full_name", "age", "contact", "email", "address")}
        row = tk.Frame(f, bg=C["white"])
        row.pack(fill="x")
        for i, (cap, key) in enumerate([("Full name", "full_name"), ("Age", "age")]):
            col = tk.Frame(row, bg=C["white"])
            col.grid(row=0, column=i, sticky="ew", padx=(0, 8))
            row.columnconfigure(0, weight=3)
            row.columnconfigure(1, weight=1)
            theme.field(col, cap)
            theme.entry(col, self.v[key]).pack(fill="x", ipady=5)
        row2 = tk.Frame(f, bg=C["white"])
        row2.pack(fill="x")
        for i, (cap, key) in enumerate([("Contact number", "contact"), ("Email", "email")]):
            col = tk.Frame(row2, bg=C["white"])
            col.grid(row=0, column=i, sticky="ew", padx=(0, 8))
            row2.columnconfigure(i, weight=1)
            theme.field(col, cap)
            theme.entry(col, self.v[key]).pack(fill="x", ipady=5)

        theme.label(f, "YOUR HOME ADDRESS", 8, C["dark"], C["white"], True).pack(anchor="w", pady=(10, 0))
        self.home_location = theme.LocationPicker(f, all_option=False)
        self.home_location.pack(fill="x")
        theme.field(f, "Street / Barangay")
        theme.entry(f, self.v["address"]).pack(fill="x", ipady=5)
        theme.field(f, "Skills (e.g. planting, tractor driving)")
        self.skills = tk.StringVar()
        theme.entry(f, self.skills).pack(fill="x", ipady=5)
        theme.field(f, "Work experience")
        self.experience = tk.Text(f, height=4, font=(theme.FONT, 10), relief="solid", bd=1, wrap="word")
        self.experience.pack(fill="x")

        bar = tk.Frame(f, bg=C["white"])
        bar.pack(fill="x", pady=14)
        self.submit_btn = theme.button(bar, "Submit Application ✓", self.submit, size=10)
        self.submit_btn.pack(side="left")
        theme.button(bar, "Clear Form", self.clear_form, bg=C["muted"], size=10, hover_color=C["dark"]
                     ).pack(side="left", padx=8)

        # =============== RIGHT: my applications table ===============
        right = tk.Frame(body, bg=C["bg"], width=430)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        theme.label(right, "My Applications", 13, C["dark"], C["bg"], True).pack(anchor="w")
        theme.label(right, "Click a row to edit it.", 9, C["muted"], C["bg"]).pack(anchor="w")
        cols = ("id", "job", "farm", "status")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=14)
        for col, title, w in (("id", "#", 35), ("job", "Job", 120), ("farm", "Farm", 150), ("status", "Status", 80)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="x", pady=(6, 8))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        theme.button(right, "🗑 Withdraw (Delete)", self.delete, bg=C["red"], size=9, hover_color="#8F3030"
                     ).pack(anchor="w")
        self.load_applications()

        # ----- start-up: pre-fill my details from my profile -----
        me = db.fetch_one("SELECT * FROM user_profiles WHERE user_id=%s", (session.user_id(),))
        self.prefill(me)
        self.load_companies()
        if vacancy_id:                    # came from "Apply Now" on the Hiring page
            self.preselect(vacancy_id)

    # ---------------- helpers ----------------
    def prefill(self, me):
        """Copy name/phone/email/home address from the user's profile."""
        if not me:
            return
        self.v["full_name"].set(me["full_name"] or "")
        self.v["contact"].set(me["phone"] or "")
        self.v["email"].set(me["email"] or "")
        self.v["address"].set(me["address"] or "")
        if me["region"]:
            self.home_location.set(me["region"], me["province"], me["municipality"])
            self._split_home_address()

    def _split_home_address(self):
        """Show the saved 'street, barangay' as a street box plus a selected barangay."""
        street, brgy = theme.split_address(self.v["address"].get(),
                                           self.home_location.barangay_cb["values"])
        self.v["address"].set(street)
        if brgy:
            self.home_location.barangay_var.set(brgy)

    def load_companies(self, *_):
        """Refill the Farm list using the Region/Province/Municipality filter."""
        region, province, muni, _barangay = self.farm_location.get()      # ← FIXED (4 values)
        sql = ("SELECT DISTINCT c.* FROM companies c JOIN job_vacancies v "
               "ON v.company_id=c.company_id AND v.status='Open' WHERE 1=1")
        params = []
        for col, val in (("region", region), ("province", province), ("municipality", muni)):
            if val:
                sql += f" AND c.{col}=%s"
                params.append(val)
        self.companies = db.fetch_all(sql + " ORDER BY c.company_name", params)
        self.company_cb["values"] = [c["company_name"] for c in self.companies]
        self.company_var.set("")
        self.address_var.set("")
        self.job_cb["values"] = []
        self.job_var.set("")

    def company_picked(self, _e=None):
        """AUTO-FILL the address and list the open jobs of the chosen farm."""
        comp = next((c for c in self.companies if c["company_name"] == self.company_var.get()), None)
        if not comp:
            return
        self.address_var.set(comp["full_address"])
        self.vacancies = db.fetch_all("SELECT * FROM job_vacancies WHERE company_id=%s AND status='Open' "
                                      "ORDER BY job_level, job_title", (comp["company_id"],))
        self.job_cb["values"] = [f"{v['job_title']}  -  {theme.peso(v['salary_per_day'])}/day"
                                 for v in self.vacancies]
        self.job_var.set("")

    def preselect(self, vacancy_id):
        """Choose a company and job when arriving from 'Apply Now'."""
        v = db.fetch_one("SELECT v.*, c.region, c.province, c.municipality, c.company_name "
                         "FROM job_vacancies v JOIN companies c ON c.company_id=v.company_id "
                         "WHERE v.vacancy_id=%s", (vacancy_id,))
        if not v:
            return
        self.farm_location.set(v["region"], v["province"], v["municipality"])
        self.company_var.set(v["company_name"])
        self.company_picked()
        for i, vac in enumerate(self.vacancies):
            if vac["vacancy_id"] == vacancy_id:
                self.job_cb.current(i)

    # ---------------- CRUD ----------------
    def load_applications(self):
        """READ: list this user's applications."""
        self.tree.delete(*self.tree.get_children())
        for a in db.fetch_all(
                "SELECT a.*, v.job_title, c.company_name FROM job_applications a "
                "JOIN job_vacancies v ON v.vacancy_id=a.vacancy_id "
                "JOIN companies c ON c.company_id=a.company_id "
                "WHERE a.applicant_id=%s ORDER BY a.application_id DESC", (session.user_id(),)):
            self.tree.insert("", "end", iid=str(a["application_id"]),
                             values=(a["application_id"], a["job_title"], a["company_name"], a["status"]))

    def read_form(self):
        """Collect and validate the form. Returns a dict or None."""
        full_name = self.v["full_name"].get().strip()
        contact = self.v["contact"].get().strip()
        region, province, muni, barangay = self.home_location.get()      # ← FIXED (4 values)
        age = self.v["age"].get().strip()
        if not full_name or not contact:
            messagebox.showwarning("Missing", "Full name and contact number are required.")
            return None
        if age and (not age.isdigit() or not 15 <= int(age) <= 90):
            messagebox.showwarning("Age", "Enter a valid age (15 - 90).")
            return None
        if not (region and province and muni):
            messagebox.showwarning("Address", "Pick your home region, province and municipality.")
            return None
        return dict(full_name=full_name, age=int(age) if age else None, contact=contact,
                    email=self.v["email"].get().strip(), region=region, province=province,
                    municipality=muni, address=theme.join_address(self.v["address"].get(), barangay),
                    skills=self.skills.get().strip(),
                    experience=self.experience.get("1.0", "end").strip())

    def submit(self):
        """CREATE (new) or UPDATE (when a row was selected)."""
        d = self.read_form()
        if not d:
            return
        if self.editing_id:                                  # ---- UPDATE ----
            db.execute("UPDATE job_applications SET full_name=%s, age=%s, contact_number=%s, email=%s, region=%s, "
                       "province=%s, municipality=%s, address=%s, skills=%s, experience=%s "
                       "WHERE application_id=%s AND applicant_id=%s",
                       (d["full_name"], d["age"], d["contact"], d["email"], d["region"], d["province"],
                        d["municipality"], d["address"], d["skills"], d["experience"],
                        self.editing_id, session.user_id()))
            messagebox.showinfo("Updated", "Your application was updated.")
        else:                                                # ---- CREATE ----
            comp = next((c for c in self.companies if c["company_name"] == self.company_var.get()), None)
            idx = self.job_cb.current()
            if not comp or idx < 0:
                return messagebox.showwarning("Choose a job", "Pick a farm and a job first.")
            vac = self.vacancies[idx]
            if db.fetch_one("SELECT 1 FROM job_applications WHERE applicant_id=%s AND vacancy_id=%s",
                            (session.user_id(), vac["vacancy_id"])):
                return messagebox.showinfo("Already applied", "You already applied for this job.")
            db.execute("INSERT INTO job_applications (applicant_id, vacancy_id, company_id, full_name, age, "
                       "contact_number, email, region, province, municipality, address, skills, experience) "
                       "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                       (session.user_id(), vac["vacancy_id"], comp["company_id"], d["full_name"], d["age"],
                        d["contact"], d["email"], d["region"], d["province"], d["municipality"], d["address"],
                        d["skills"], d["experience"]))
            messagebox.showinfo("Application sent", f"Your application to {comp['company_name']} was submitted!")
        self.clear_form()                                    # <-- form clears automatically
        self.load_applications()

    def on_select(self, _e=None):
        """Load a selected application into the form for editing."""
        sel = self.tree.selection()
        if not sel:
            return
        a = db.fetch_one("SELECT a.*, c.company_name, c.full_address, v.job_title FROM job_applications a "
                         "JOIN companies c ON c.company_id=a.company_id "
                         "JOIN job_vacancies v ON v.vacancy_id=a.vacancy_id WHERE a.application_id=%s",
                         (int(sel[0]),))
        self.editing_id = a["application_id"]
        self.mode_title.configure(text=f"✏️ Editing application #{self.editing_id} (farm & job are locked)")
        self.company_cb.configure(state="disabled")
        self.job_cb.configure(state="disabled")
        self.company_var.set(a["company_name"])
        self.address_var.set(a["full_address"])
        self.job_var.set(a["job_title"])
        self.v["full_name"].set(a["full_name"])
        self.v["age"].set(a["age"] or "")
        self.v["contact"].set(a["contact_number"])
        self.v["email"].set(a["email"] or "")
        self.v["address"].set(a["address"] or "")
        self.home_location.set(a["region"], a["province"], a["municipality"])
        self._split_home_address()
        self.skills.set(a["skills"] or "")
        self.experience.delete("1.0", "end")
        self.experience.insert("1.0", a["experience"] or "")
        self.submit_btn.configure(text="Update Application ✓")

    def delete(self):
        """DELETE (withdraw) the selected application."""
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("Select", "Click an application in the table first.")
        if messagebox.askyesno("Withdraw", "Withdraw and delete this application?"):
            db.execute("DELETE FROM job_applications WHERE application_id=%s AND applicant_id=%s",
                       (int(sel[0]), session.user_id()))
            self.clear_form()
            self.load_applications()

    def clear_form(self):
        """Empty every field and return to 'new application' mode."""
        self.editing_id = None
        self.mode_title.configure(text="1  Choose the farm you want to join")
        self.company_cb.configure(state="readonly")
        self.job_cb.configure(state="readonly")
        for var in self.v.values():
            var.set("")
        self.skills.set("")
        self.experience.delete("1.0", "end")
        self.home_location.reset()
        self.farm_location.reset()
        self.load_companies()
        self.submit_btn.configure(text="Submit Application ✓")
        self.tree.selection_remove(self.tree.selection())