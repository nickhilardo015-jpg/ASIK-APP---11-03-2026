"""
login_page.py  --  The Login page of Asik.

Checks the typed username/password against the MySQL table
`account_credentials` (passwords are compared as hashes, never as plain text).
Has a "Create Account" button for new users.
"""

import tkinter as tk
from tkinter import messagebox

import database as db
import languages
import theme
from theme import C

GREEN_PANEL = "#1B3A2A"


class LoginPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["dark"])
        self.app = app
        outer = tk.Frame(self, bg=C["dark"])
        outer.pack(fill="both", expand=True, padx=28, pady=28)

        # ---------------- Left: welcome panel with the Asik logo ----------------
        left = tk.Frame(outer, bg=GREEN_PANEL, width=480)
        left.pack(side="left", fill="both", expand=True)
        left.pack_propagate(False)

        # no white plate: the logo is transparent and sits directly on the panel
        plate = tk.Frame(left, bg=GREEN_PANEL)
        plate.pack(anchor="w", padx=44, pady=(40, 6))
        theme.logo_widget(plate, 120, GREEN_PANEL, 50).pack(padx=14, pady=8)

        theme.label(left, "GROW SMARTER. HARVEST BETTER.", 10, "#D7F2A9",
                    GREEN_PANEL, True).pack(anchor="w", padx=47, pady=(10, 14))
        theme.label(left, "Your partner in modern agriculture.\n"
                          "Rent farm equipment, find farm jobs,\n"
                          "hire farm workers and connect with\n"
                          "farmers across the Philippines.",
                    14, C["white"], GREEN_PANEL, justify="left").pack(anchor="w", padx=44)

        for icon, text, tint in [("🚜", "Equipment rental in every region", C["yellow"]),
                                 ("📢", "Hiring Now! farm jobs", C["blue"]),
                                 ("💬", "Message farmers & employers", C["purple"])]:
            row = tk.Frame(left, bg=tint)
            row.pack(fill="x", padx=35, pady=(12, 0))
            theme.label(row, icon, 20, C["dark"], tint).pack(side="left", padx=14, pady=8)
            theme.label(row, text, 11, C["dark"], tint, True).pack(side="left")

        # ---------------- Right: the form ----------------
        right = tk.Frame(outer, bg=C["white"], width=430)
        right.pack(side="right", fill="both")
        right.pack_propagate(False)
        form = tk.Frame(right, bg=C["white"])
        form.place(relx=.5, rely=.5, anchor="center", width=320)

        languages.language_picker(form, C["white"], app.show_login).pack(anchor="w", pady=(0, 14))   # English is the default
        theme.label(form, "Welcome to Asik!", 24, C["dark"], C["white"], True, wraplength=320, justify="left"
                    ).pack(anchor="w")
        theme.label(form, "Sign in to continue.", 10, C["muted"], C["white"]
                    ).pack(anchor="w", pady=(4, 18))

        theme.field(form, "Username")
        self.user_entry = tk.Entry(form, font=(theme.FONT, 11), relief="solid", bd=1)
        self.user_entry.pack(fill="x", ipady=9)

        theme.field(form, "Password")
        row = tk.Frame(form, bg=C["white"])
        row.pack(fill="x")
        self.pass_entry = tk.Entry(row, font=(theme.FONT, 11), show="●", relief="solid", bd=1)
        self.pass_entry.pack(side="left", fill="x", expand=True, ipady=9)
        self.pass_entry.bind("<Return>", lambda e: self.login())
        self.visible = False
        self.eye = tk.Button(row, text="👁", font=("Segoe UI Emoji", 11), bg=C["purple"],
                             fg=C["purple_dark"], relief="flat", bd=0, cursor="hand2",
                             width=4, command=self.toggle_password)
        self.eye.pack(side="right", padx=(6, 0), ipady=4)

        theme.button(form, "SIGN IN  →", self.login, size=11).pack(fill="x", pady=(20, 8), ipady=3)

        # divider + create account button
        theme.label(form, "— New to Asik? —", 9, C["muted"], C["white"]).pack(pady=(8, 4))
        theme.button(form, "✚  CREATE AN ACCOUNT", app.show_register, bg=C["purple_dark"],
                     size=10, hover_color=C["blue_dark"]).pack(fill="x", ipady=2)

        theme.label(form, "Demo: seeker / seeker123  •  employer / employer123\n"
                          "lender / lender123  •  both / both123  •  admin / admin123",
                    8, C["muted"], C["white"], justify="center").pack(pady=(16, 0))
        self.user_entry.focus_set()

    def toggle_password(self):
        """Show / hide the password (eye button)."""
        self.visible = not self.visible
        self.pass_entry.configure(show="" if self.visible else "●")
        self.eye.configure(text="🙈" if self.visible else "👁")

    def login(self):
        """Verify credentials and open the app."""
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        if not username or not password:
            messagebox.showwarning("Missing Information", "Enter both username and password.")
            return
        try:
            user = db.fetch_one("SELECT * FROM account_credentials WHERE username=%s", (username,))
        except Exception as err:
            messagebox.showerror("Database error",
                                 f"Cannot reach MySQL:\n{err}\n\nRun setup_database.py first.")
            return
        if not user or not db.verify_password(password, user["password_salt"], user["password_hash"]):
            messagebox.showerror("Login failed", "Wrong username or password.")
            return
        if not user["is_active"]:
            messagebox.showerror("Account disabled", "This account was disabled by the administrator.")
            return
        self.app.login_success(user["user_id"])