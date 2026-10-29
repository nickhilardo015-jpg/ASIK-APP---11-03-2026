"""
admin_page.py  --  ADMINISTRATOR panel (the owner of the program).

Overview : how many users are on the app (total / active / disabled and per
           role) plus counts of farms, vacancies, equipment, applications,
           rentals and messages.
Users    : search, enable/disable, reset password, change roles, delete,
           and create new administrator accounts.
Content  : delete companies, vacancies and equipment listings (moderation).
All numbers come live from MySQL. Only accounts with the 'admin' role can
open this page.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import database as db
import session
import theme
from theme import C

ROLES = ["job_seeker", "employer", "lender", "renter", "admin"]


class AdminPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        if not session.has_role("admin"):                    # safety check
            theme.label(self, "Administrators only.", 14, C["red"]).pack(pady=60)
            return
        theme.page_header(self, "Administrator Panel 🛠", "Monitor Asik and manage users and content.", C["pink_dark"])
        self.stats_frame = tk.Frame(self, bg=C["bg"])
        self.stats_frame.pack(fill="x", padx=23)

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=28, pady=12)
        self.users_tab = tk.Frame(self.tabs, bg=C["bg"])
        self.tabs.add(self.users_tab, text="  👥 Users  ")
        self.table_trees = {}
        for key, title in (("companies", "  🏢 Farms / Companies  "), ("vacancies", "  📢 Vacancies  "),
                           ("equipment", "  🚜 Equipment  ")):
            tab = tk.Frame(self.tabs, bg=C["bg"])
            self.tabs.add(tab, text=title)
            self.build_content_tab(tab, key)
        self.build_users_tab()
        self.refresh_all()

    # ---------------- overview cards ----------------
    def draw_stats(self):
        theme.clear(self.stats_frame)
        one = lambda sql: db.fetch_one(sql)["n"]               # noqa: E731
        by_role = {r["role"]: r["n"] for r in db.fetch_all(
            "SELECT role, COUNT(*) n FROM user_roles GROUP BY role")}
        cards = [("👥", "Total users", one("SELECT COUNT(*) n FROM account_credentials"), C["purple_dark"]),
                 ("✅", "Active", one("SELECT COUNT(*) n FROM account_credentials WHERE is_active=1"), C["green"]),
                 ("🚫", "Disabled", one("SELECT COUNT(*) n FROM account_credentials WHERE is_active=0"), C["red"]),
                 ("🧑‍🌾", "Job seekers", by_role.get("job_seeker", 0), C["green_dark"]),
                 ("🏢", "Employers", by_role.get("employer", 0), C["blue_dark"]),
                 ("🚜", "Lenders", by_role.get("lender", 0), C["yellow_dark"]),
                 ("🌾", "Renters", by_role.get("renter", 0), C["orange_dark"]),
                 ("📢", "Open vacancies", one("SELECT COUNT(*) n FROM job_vacancies WHERE status='Open'"), C["blue_dark"]),
                 ("📝", "Applications", one("SELECT COUNT(*) n FROM job_applications"), C["green"]),
                 ("📋", "Rentals", one("SELECT COUNT(*) n FROM equipment_rentals"), C["pink_dark"]),
                 ("💬", "Messages", one("SELECT COUNT(*) n FROM messages"), C["purple_dark"]),
                 ("🏭", "Equipment", one("SELECT COUNT(*) n FROM equipment"), C["yellow_dark"])]
        for i, (icon, title, value, accent) in enumerate(cards):
            r, c = divmod(i, 6)
            box = theme.card(self.stats_frame)
            box.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
            self.stats_frame.columnconfigure(c, weight=1, uniform="adm")
            tk.Frame(box, bg=accent, height=3).pack(fill="x")
            row = tk.Frame(box, bg=C["white"])
            row.pack(fill="x", padx=10, pady=8)
            theme.label(row, icon, 16, accent, C["white"]).pack(side="left")
            col = tk.Frame(row, bg=C["white"])
            col.pack(side="left", padx=6)
            theme.label(col, f"{value:,}", 15, accent, C["white"], True).pack(anchor="w")
            theme.label(col, title, 8, C["muted"], C["white"]).pack(anchor="w")

    def refresh_all(self):
        self.draw_stats()
        self.load_users()
        for key in self.table_trees:
            self.load_content(key)

    # ---------------- users tab ----------------
    def build_users_tab(self):
        self.search = theme.SearchBar(self.users_tab, self.load_users, "Search username, name or role...")
        self.search.pack(fill="x", pady=(8, 8))
        cols = ("id", "username", "name", "roles", "email", "active", "joined")
        self.user_tree = ttk.Treeview(self.users_tab, columns=cols, show="headings", height=10)
        for col, title, w in (("id", "#", 40), ("username", "Username", 110), ("name", "Name", 170),
                              ("roles", "Roles", 190), ("email", "Email", 170), ("active", "Active", 60),
                              ("joined", "Joined", 100)):
            self.user_tree.heading(col, text=title)
            self.user_tree.column(col, width=w, anchor="w")
        self.user_tree.pack(fill="both", expand=True)
        bar = tk.Frame(self.users_tab, bg=C["bg"])
        bar.pack(fill="x", pady=8)
        for text, cmd, bg, hov in (("Enable / Disable", self.toggle_user, C["blue_dark"], C["purple_dark"]),
                                   ("Reset Password", self.reset_password, C["purple_dark"], C["blue_dark"]),
                                   ("Change Roles", self.change_roles, C["green"], C["green_dark"]),
                                   ("＋ New Admin", self.new_admin, C["dark"], C["sidebar_hover"]),
                                   ("Delete User", self.delete_user, C["red"], "#8F3030")):
            theme.button(bar, text, cmd, bg=bg, size=9, hover_color=hov).pack(side="left", padx=(0, 6))

    def load_users(self):
        sql = ("SELECT u.user_id, u.username, u.is_active, u.created_at, p.full_name, p.email, "
               "GROUP_CONCAT(r.role) AS roles FROM account_credentials u "
               "LEFT JOIN user_profiles p ON p.user_id=u.user_id LEFT JOIN user_roles r ON r.user_id=u.user_id")
        params = []
        text = self.search.text()
        if text:
            sql += " WHERE u.username LIKE %s OR p.full_name LIKE %s OR r.role LIKE %s"
            params = [f"%{text}%", f"%{text}%", f"%{text.replace(' ', '_')}%"]
        sql += " GROUP BY u.user_id, u.username, u.is_active, u.created_at, p.full_name, p.email ORDER BY u.user_id"
        self.user_tree.delete(*self.user_tree.get_children())
        for u in db.fetch_all(sql, params):
            self.user_tree.insert("", "end", iid=str(u["user_id"]), values=(
                u["user_id"], u["username"], u["full_name"], (u["roles"] or "").replace("_", " "),
                u["email"] or "", "Yes" if u["is_active"] else "No", u["created_at"].strftime("%Y-%m-%d")))

    def selected_user(self):
        sel = self.user_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Click a user in the table first.")
            return None
        return int(sel[0])

    def toggle_user(self):
        uid = self.selected_user()
        if uid is None:
            return
        if uid == session.user_id():
            return messagebox.showwarning("Not allowed", "You cannot disable your own account.")
        db.execute("UPDATE account_credentials SET is_active = 1 - is_active WHERE user_id=%s", (uid,))
        self.refresh_all()

    def reset_password(self):
        uid = self.selected_user()
        if uid is None:
            return
        new = simpledialog.askstring("Reset password", "Type a new password (min. 6 characters):", show="●", parent=self)
        if not new or len(new) < 6:
            return
        salt = db.make_salt()
        db.execute("UPDATE account_credentials SET password_salt=%s, password_hash=%s WHERE user_id=%s",
                   (salt, db.hash_password(new, salt), uid))
        messagebox.showinfo("Done", "Password was reset.")

    def delete_user(self):
        uid = self.selected_user()
        if uid is None:
            return
        if uid == session.user_id():
            return messagebox.showwarning("Not allowed", "You cannot delete your own account.")
        if messagebox.askyesno("Delete", "Delete this user and all their data permanently?"):
            db.execute("DELETE FROM account_credentials WHERE user_id=%s", (uid,))
            self.refresh_all()

    def change_roles(self):
        uid = self.selected_user()
        if uid is None:
            return
        current = set(db.get_roles(uid))
        win = tk.Toplevel(self)
        win.title("Change roles")
        win.geometry("300x300")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()
        theme.label(win, "Roles of this user", 13, C["dark"], C["white"], True).pack(pady=14)
        vars_ = {}
        for role in ROLES:
            vars_[role] = tk.BooleanVar(value=role in current)
            tk.Checkbutton(win, text=role.replace("_", " ").title(), variable=vars_[role], bg=C["white"],
                           font=(theme.FONT, 10)).pack(anchor="w", padx=40)

        def save():
            chosen = [r for r, v in vars_.items() if v.get()]
            if not chosen:
                return messagebox.showwarning("Roles", "Pick at least one role.", parent=win)
            if uid == session.user_id() and "admin" not in chosen:
                return messagebox.showwarning("Not allowed", "You cannot remove your own admin role.", parent=win)
            db.execute("DELETE FROM user_roles WHERE user_id=%s", (uid,))
            for r in chosen:
                db.execute("INSERT INTO user_roles (user_id, role) VALUES (%s,%s)", (uid, r))
            win.destroy()
            self.refresh_all()
        theme.button(win, "Save", save).pack(pady=16)

    def new_admin(self):
        username = simpledialog.askstring("New admin", "Username for the new administrator:", parent=self)
        if not username:
            return
        if db.fetch_one("SELECT 1 FROM account_credentials WHERE username=%s", (username.strip(),)):
            return messagebox.showerror("Taken", "That username already exists.")
        pw = simpledialog.askstring("New admin", "Password (min. 6 characters):", show="●", parent=self)
        if not pw or len(pw) < 6:
            return messagebox.showwarning("Password", "Password too short.")
        db.create_account(username.strip(), pw, username.strip().title(), ["admin"])
        self.refresh_all()
        messagebox.showinfo("Created", "Administrator account created.")

    # ---------------- content tabs (companies / vacancies / equipment) ----------------
    QUERIES = {
        "companies": ("SELECT company_id AS id, company_name AS c1, full_address AS c2, "
                      "(SELECT COUNT(*) FROM job_vacancies v WHERE v.company_id=companies.company_id) AS c3 "
                      "FROM companies ORDER BY company_id",
                      ("ID", "Company", "Full address", "Vacancies"), "DELETE FROM companies WHERE company_id=%s"),
        "vacancies": ("SELECT v.vacancy_id AS id, v.job_title AS c1, c.company_name AS c2, "
                      "CONCAT('₱', FORMAT(v.salary_per_day,0), ' / day  -  ', v.status) AS c3 "
                      "FROM job_vacancies v JOIN companies c ON c.company_id=v.company_id ORDER BY v.vacancy_id DESC",
                      ("ID", "Job", "Company", "Salary / status"), "DELETE FROM job_vacancies WHERE vacancy_id=%s"),
        "equipment": ("SELECT equipment_id AS id, name AS c1, CONCAT(municipality, ', ', province) AS c2, "
                      "CONCAT('₱', FORMAT(price_per_day,0), ' / day') AS c3 FROM equipment ORDER BY equipment_id DESC",
                      ("ID", "Equipment", "Location", "Price"), "DELETE FROM equipment WHERE equipment_id=%s"),
    }

    def build_content_tab(self, tab, key):
        _sql, heads, _del = self.QUERIES[key]
        tree = ttk.Treeview(tab, columns=("id", "c1", "c2", "c3"), show="headings", height=10)
        for col, head, w in zip(("id", "c1", "c2", "c3"), heads, (50, 220, 420, 160)):
            tree.heading(col, text=head)
            tree.column(col, width=w, anchor="w")
        tree.pack(fill="both", expand=True, pady=(8, 8))
        theme.button(tab, "Delete Selected", lambda k=key: self.delete_content(k), bg=C["red"], size=9,
                     hover_color="#8F3030").pack(anchor="w")
        self.table_trees[key] = tree

    def load_content(self, key):
        tree = self.table_trees[key]
        tree.delete(*tree.get_children())
        for r in db.fetch_all(self.QUERIES[key][0]):
            tree.insert("", "end", iid=str(r["id"]), values=(r["id"], r["c1"], r["c2"], r["c3"]))

    def delete_content(self, key):
        sel = self.table_trees[key].selection()
        if not sel:
            return messagebox.showwarning("Select", "Click a row first.")
        if messagebox.askyesno("Delete", "Delete this item permanently?"):
            db.execute(self.QUERIES[key][2], (int(sel[0]),))
            self.refresh_all()
