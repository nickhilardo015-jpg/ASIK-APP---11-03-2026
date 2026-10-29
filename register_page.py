"""
register_page.py  --  Create-account page.

The new user ticks what they are:
    * Job Seeker  - looking for a farm job
    * Employer    - hiring farm workers (also gives company details)
    * Lender      - rents out their equipment to other farmers
    * Renter      - a farmer who wants to rent equipment
An employer can ALSO be a lender (tick both boxes).
Data is saved to: account_credentials, user_roles, user_profiles,
and (for employers) companies + employer_details.
Administrator accounts cannot be created here - only the admin makes those.
"""

import tkinter as tk
from tkinter import messagebox

import database as db
import language
import theme
from theme import C


class RegisterPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["dark"])
        self.app = app
        outer = tk.Frame(self, bg=C["white"])
        outer.pack(fill="both", expand=True, padx=28, pady=22)

        # ---------- title bar with logo ----------
        top = tk.Frame(outer, bg=C["white"])
        top.pack(fill="x", padx=24, pady=(14, 0))
        theme.logo_widget(top, 60, C["white"], 28).pack(side="left")
        tk.Frame(top, bg=C["white"], width=14).pack(side="left")
        box = tk.Frame(top, bg=C["white"])
        box.pack(side="left")
        theme.label(box, language.t("register.title"), 20, C["dark"], C["white"], True).pack(anchor="w")
        theme.label(box, language.t("register.subtitle"),
                    9, C["muted"], C["white"]).pack(anchor="w")
        theme.button(top, language.t("register.back_to_login"), app.show_login, bg=C["muted"], size=9,
                     hover_color=C["dark"]).pack(side="right")

        scroll = theme.Scrollable(outer, C["white"])
        scroll.pack(fill="both", expand=True, padx=24, pady=8)
        body = scroll.inner

        # ---------- role check boxes ----------
        theme.label(body, language.t("register.i_am_a"), 9, C["dark"], C["white"], True
                    ).pack(anchor="w", pady=(6, 4))
        self.role_vars = {}
        roles_row = tk.Frame(body, bg=C["white"])
        roles_row.pack(fill="x")
        for i, (key, icon, title_key, desc_key, tint) in enumerate([
            ("job_seeker", "🧑‍🌾", "register.role_job_seeker",  "register.role_job_seeker_desc",  C["mint"]),
            ("employer",   "🏢",     "register.role_employer",    "register.role_employer_desc",    C["blue"]),
            ("lender",     "🚜",     "register.role_lender",      "register.role_lender_desc",      C["yellow"]),
            ("renter",     "🌾",     "register.role_renter",      "register.role_renter_desc",      C["purple"]),
        ]):
            c = tk.Frame(roles_row, bg=tint, highlightbackground=C["border"], highlightthickness=1)
            c.grid(row=0, column=i, padx=5, sticky="nsew")
            roles_row.columnconfigure(i, weight=1, uniform="roles")
            var = tk.BooleanVar(value=(key == "job_seeker"))
            self.role_vars[key] = var
            theme.label(c, icon, 22, C["dark"], tint).pack(pady=(10, 0))
            tk.Checkbutton(c, text=language.t(title_key), variable=var, bg=tint, activebackground=tint,
                           font=(theme.FONT, 10, "bold"), fg=C["dark"], selectcolor=C["white"],
                           command=self.toggle_employer_box).pack()
            theme.label(c, language.t(desc_key), 8, C["muted"], tint).pack(pady=(0, 10))

        # ---------- account + personal details ----------
        two = tk.Frame(body, bg=C["white"])
        two.pack(fill="x", pady=(10, 0))
        colA = tk.Frame(two, bg=C["white"])
        colA.pack(side="left", fill="both", expand=True, padx=(0, 14))
        colB = tk.Frame(two, bg=C["white"])
        colB.pack(side="left", fill="both", expand=True)

        self.v = {k: tk.StringVar() for k in
                  ("full_name", "username", "password", "confirm", "email", "phone", "address")}
        for caption_key, key, hide in [
            ("register.full_name",          "full_name", False),
            ("register.username",           "username",  False),
            ("register.password_hint",      "password",  True),
            ("register.confirm_password",   "confirm",   True),
        ]:
            theme.field(colA, language.t(caption_key))
            theme.entry(colA, self.v[key], show="●" if hide else None).pack(fill="x", ipady=6)
        for caption_key, key in [("register.email",   "email"),
                                 ("register.phone",   "phone"),
                                 ("register.address", "address")]:
            theme.field(colB, language.t(caption_key))
            theme.entry(colB, self.v[key]).pack(fill="x", ipady=6)

        theme.label(body, language.t("register.where_location"), 9, C["dark"], C["white"], True
                    ).pack(anchor="w", pady=(14, 2))
        self.location = theme.LocationPicker(body, all_option=False, horizontal=True)
        self.location.pack(fill="x")

        # ---------- employer-only section (shown when Employer is ticked) ----------
        self.employer_box = tk.Frame(body, bg=C["blue"], highlightbackground=C["border"],
                                     highlightthickness=1)
        theme.label(self.employer_box, language.t("register.employer_header"),
                    10, C["blue_dark"], C["blue"], True).pack(anchor="w", padx=14, pady=(10, 0))
        self.ev = {k: tk.StringVar() for k in ("company", "street", "position", "permit")}
        inner = tk.Frame(self.employer_box, bg=C["blue"])
        inner.pack(fill="x", padx=14, pady=8)
        for i, (caption_key, key) in enumerate([
            ("register.company_name",  "company"),
            ("register.company_street","street"),
            ("register.position",      "position"),
            ("register.permit",        "permit"),
        ]):
            col = tk.Frame(inner, bg=C["blue"])
            col.grid(row=0, column=i, padx=5, sticky="ew")
            inner.columnconfigure(i, weight=1, uniform="emp")
            theme.field(col, language.t(caption_key), C["blue"])
            theme.entry(col, self.ev[key]).pack(fill="x", ipady=5)
        theme.label(self.employer_box, language.t("register.employer_note"),
                    8, C["muted"], C["blue"]).pack(anchor="w", padx=14, pady=(0, 10))

        theme.button(body, language.t("register.create_btn"), self.register, size=11
                     ).pack(fill="x", pady=18, ipady=3)

    def toggle_employer_box(self):
        """Show the employer form only when 'Employer' is ticked."""
        if self.role_vars["employer"].get():
            self.employer_box.pack(fill="x", pady=(12, 0))
        else:
            self.employer_box.pack_forget()

    def register(self):
        """Validate the form, then save everything in MySQL."""
        v = {k: x.get().strip() for k, x in self.v.items()}
        roles = [r for r, var in self.role_vars.items() if var.get()]
        region, province, muni, barangay = self.location.get()

        # ----- validation -----
        if not roles:
            return messagebox.showwarning(language.t("register.err_role_title"),
                                          language.t("register.err_role_msg"))
        if not v["full_name"] or not v["username"] or not v["phone"]:
            return messagebox.showwarning(language.t("register.err_missing_title"),
                                          language.t("register.err_missing_msg"))
        if len(v["password"]) < 6:
            return messagebox.showwarning(language.t("register.err_password_title"),
                                          language.t("register.err_password_short"))
        if v["password"] != v["confirm"]:
            return messagebox.showwarning(language.t("register.err_password_title"),
                                          language.t("register.err_password_mismatch"))
        if not (region and province and muni):
            return messagebox.showwarning(language.t("register.err_location_title"),
                                          language.t("register.err_location_msg"))
        if "employer" in roles and not self.ev["company"].get().strip():
            return messagebox.showwarning(language.t("register.err_employer_title"),
                                          language.t("register.err_employer_msg"))
        if db.fetch_one("SELECT 1 FROM account_credentials WHERE username=%s", (v["username"],)):
            return messagebox.showerror(language.t("register.err_taken_title"),
                                        language.t("register.err_taken_msg"))

        # ----- save -----
        address = ", ".join(x for x in (v["address"], barangay) if x)
        user_id = db.create_account(v["username"], v["password"], v["full_name"], roles,
                                    v["email"], v["phone"], region, province, muni, address)
        if "employer" in roles:
            company = self.ev["company"].get().strip()
            street = self.ev["street"].get().strip()
            full = ", ".join(x for x in (street, barangay, muni, province, region, "Philippines") if x)
            company_id = db.execute(
                "INSERT INTO companies (company_name, owner_user_id, street, municipality, "
                "province, region, full_address) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (company, user_id, street, muni, province, region, full))
            db.execute("INSERT INTO employer_details (user_id, company_id, position_title, "
                       "business_permit, contact_number) VALUES (%s,%s,%s,%s,%s)",
                       (user_id, company_id, self.ev["position"].get().strip(),
                        self.ev["permit"].get().strip(), v["phone"]))
        messagebox.showinfo(language.t("register.welcome_title"),
                            language.t("register.welcome_msg"))
        self.app.show_login()