"""
profile_page.py  --  "My Profile": information that identifies the user,
plus profile PHOTO upload.

* Remove Photo : deletes the photo (clears photo_path and deletes the copied file).
* Upload Photo : choose a JPG/PNG/GIF. The file is copied into the
                 `profile_photos` folder and its path saved in
                 user_profiles.photo_path.
* Edit the name, email, phone, address, bio and press "Save Profile".
* Change password (the new password is stored as a hash).
Data: MySQL tables user_profiles, account_credentials, user_roles,
      employer_details / companies (for employers).
"""

import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

import config
import database as db
import languages
import session
import theme
from theme import C


class ProfilePage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.uid = session.user_id()
        theme.page_header(self, "My Profile 👤", "Your information helps other farmers and employers know who you are.",
                          C["purple_dark"])
        self.me = db.fetch_one("SELECT * FROM user_profiles WHERE user_id=%s", (self.uid,))
        account = db.fetch_one("SELECT username, created_at FROM account_credentials WHERE user_id=%s", (self.uid,))

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 14))

        # ============ LEFT: photo + identity card ============
        left = theme.card(body)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.configure(width=290)
        left.pack_propagate(False)
        self.photo_holder = tk.Frame(left, bg=C["white"])
        self.photo_holder.pack(pady=(22, 6))
        self.upload_btn = theme.button(left, "📷 Upload Photo", self.upload_photo, bg=C["purple_dark"], size=9,
                                       hover_color=C["blue_dark"])
        self.upload_btn.pack()
        # Remove Photo is only useful when a photo exists (draw_photo shows/hides it)
        self.remove_btn = theme.button(left, "🗑 Remove Photo", self.remove_photo, bg=C["red"], size=9,
                                       hover_color="#9E2F2F")
        self.draw_photo(first_time=True)           # photo + (if there is one) the Remove button
        theme.label(left, self.me["full_name"], 15, C["dark"], C["white"], True, wraplength=250
                    ).pack(pady=(14, 0))
        theme.label(left, f"@{account['username']}", 9, C["muted"], C["white"]).pack()
        for role in session.user["roles"]:
            tint = {"admin": C["pink"], "employer": C["blue"], "lender": C["yellow"],
                    "job_seeker": C["mint"]}.get(role, C["purple"])
            theme.label(left, f"  {role.replace('_', ' ').upper()}  ", 8, C["dark"], tint, True).pack(pady=3)
        theme.label(left, f"Member since {account['created_at'].strftime('%b %d, %Y')}", 8, C["muted"],
                    C["white"]).pack(pady=(10, 0))

        # employer details (if any)
        emp = db.fetch_one("SELECT d.*, c.company_name, c.full_address FROM employer_details d "
                           "LEFT JOIN companies c ON c.company_id=d.company_id WHERE d.user_id=%s", (self.uid,))
        if emp:
            tk.Frame(left, bg=C["border"], height=1).pack(fill="x", padx=16, pady=12)
            theme.label(left, "🏢 " + (emp["company_name"] or "-"), 10, C["green_dark"], C["white"], True,
                        wraplength=250).pack()
            theme.label(left, f"{emp['position_title'] or ''}", 9, C["muted"], C["white"]).pack()
            theme.label(left, emp["full_address"] or "", 8, C["muted"], C["white"], wraplength=250,
                        justify="center").pack(pady=3)

        # Log out lives here (moved from the sidebar)
        theme.button(left, "↪  Log Out", self.app.logout, bg="#245C3A", size=10,
                     hover_color="#1B4A2F").pack(side="bottom", fill="x", padx=16, pady=16)
        # language: English, Filipino, Kapampangan or Bisaya (the whole system is rebuilt in that language)
        languages.language_picker(left, C["white"], lambda: (self.app.show_app(), self.app.navigate("My Profile"))
                             ).pack(side="bottom", anchor="w", padx=16)

        # ============ RIGHT: edit form ============
        right = theme.card(body)
        right.pack(side="left", fill="both", expand=True)
        scroll = theme.Scrollable(right, C["white"])
        scroll.pack(fill="both", expand=True)
        f = tk.Frame(scroll.inner, bg=C["white"])
        f.pack(fill="x", padx=20, pady=10)
        theme.label(f, "Profile information", 13, C["purple_dark"], C["white"], True).pack(anchor="w")
        self.v = {k: tk.StringVar(value=self.me[k] or "") for k in ("full_name", "email", "phone", "address")}
        for cap, key in (("Full name", "full_name"), ("Email", "email"), ("Phone", "phone"),
                         ("Street / Barangay", "address")):
            theme.field(f, cap)
            theme.entry(f, self.v[key]).pack(fill="x", ipady=5)
        theme.label(f, "LOCATION", 8, C["dark"], C["white"], True).pack(anchor="w", pady=(12, 0))
        self.location = theme.LocationPicker(f, all_option=False)
        self.location.pack(fill="x")
        if self.me["region"]:
            self.location.set(self.me["region"], self.me["province"], self.me["municipality"])
            # the barangay is saved together with the street: "street, barangay"
            street, brgy = theme.split_address(self.me["address"], self.location.barangay_cb["values"])
            self.v["address"].set(street)
            if brgy:
                self.location.barangay_var.set(brgy)
        theme.field(f, "About me")
        self.bio = tk.Text(f, height=4, font=(theme.FONT, 10), relief="solid", bd=1, wrap="word")
        self.bio.pack(fill="x")
        self.bio.insert("1.0", self.me["bio"] or "")
        theme.button(f, "Save Profile ✓", self.save).pack(anchor="w", pady=14)

        tk.Frame(f, bg=C["border"], height=1).pack(fill="x", pady=4)
        theme.label(f, "Change password", 13, C["purple_dark"], C["white"], True).pack(anchor="w", pady=(8, 0))
        self.pw_old, self.pw_new, self.pw_confirm = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for cap, var in (("Current password", self.pw_old), ("New password (min. 6)", self.pw_new),
                         ("Confirm new password", self.pw_confirm)):
            theme.field(f, cap)
            theme.entry(f, var, show="●").pack(fill="x", ipady=5)
        theme.button(f, "Change Password", self.change_password, bg=C["blue_dark"],
                     hover_color=C["purple_dark"]).pack(anchor="w", pady=14)

        # ---- posts I shared from the Community page ----
        tk.Frame(f, bg=C["border"], height=1).pack(fill="x", pady=4)
        theme.label(f, "Shared on my profile 🔗", 13, C["purple_dark"], C["white"], True).pack(anchor="w", pady=(8, 4))
        self.draw_shared(f)

        # ---- account: deactivate or delete (both ask for the password) ----
        tk.Frame(f, bg=C["border"], height=1).pack(fill="x", pady=(14, 4))
        theme.label(f, "Account", 13, C["red"], C["white"], True).pack(anchor="w", pady=(8, 2))
        theme.label(f, "Deactivate: your account is switched off and you are logged out. Nobody can find you "
                       "and you cannot log in until an administrator reactivates it. Your data is kept.\n"
                       "Delete: your account and everything that belongs to it is erased for good.",
                    9, C["muted"], C["white"], wraplength=520, justify="left").pack(anchor="w")
        danger = tk.Frame(f, bg=C["white"])
        danger.pack(anchor="w", pady=12)
        theme.button(danger, "⏸ Deactivate my account", lambda: self.account_dialog("deactivate"),
                     bg=C["orange_dark"], size=9, hover_color="#8F4F22").pack(side="left")
        theme.button(danger, "🗑 Delete my account", lambda: self.account_dialog("delete"),
                     bg=C["red"], size=9, hover_color="#8F3030").pack(side="left", padx=8)

    def draw_shared(self, parent):
        """List the Community posts this user shared on their profile (click one to open it)."""
        try:
            rows = db.fetch_all(
                "SELECT p.post_id, p.title, p.category, u.full_name FROM community_shares s "
                "JOIN community_posts p ON p.post_id=s.post_id JOIN user_profiles u ON u.user_id=p.user_id "
                "WHERE s.user_id=%s AND p.is_removed=0 ORDER BY s.shared_at DESC LIMIT 10", (self.uid,))
        except Exception:                      # the Community tables do not exist yet
            rows = []
        if not rows:
            theme.label(parent, "Nothing shared yet. Press 🔗 Share to profile on a post in the Community page.",
                        9, C["muted"], C["white"], wraplength=420, justify="left").pack(anchor="w")
            return
        for r in rows:
            lbl = theme.label(parent, f"🔗 {r['title']}  ·  {r['category']}  ·  by {r['full_name']}", 10,
                              C["blue_dark"], C["white"], wraplength=420, justify="left")
            lbl.pack(anchor="w", pady=2)
            lbl.configure(cursor="hand2")
            lbl.bind("<Button-1>", lambda e, pid=r["post_id"]: self.app.navigate("Community", post_id=pid))

    # ---------------- deactivate / delete the account ----------------
    def account_dialog(self, mode):
        """Pop-up that asks for the PASSWORD before the account is deactivated or deleted."""
        delete = mode == "delete"
        if "admin" in session.user["roles"]:           # never remove the last working administrator
            n = db.fetch_one("SELECT COUNT(*) AS n FROM user_roles r JOIN account_credentials a "
                             "ON a.user_id=r.user_id WHERE r.role='admin' AND a.is_active=1")["n"]
            if n <= 1:
                return messagebox.showwarning("Last administrator",
                                              "You are the only active administrator, so this account cannot be "
                                              "deactivated or deleted. Create another admin first.")
        win = tk.Toplevel(self)
        win.title("Delete account" if delete else "Deactivate account")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("440x360")
        theme.label(win, "🗑 Delete my account" if delete else "⏸ Deactivate my account", 14, C["red"],
                    C["white"], True).pack(anchor="w", padx=22, pady=(16, 4))
        theme.label(win, ("This permanently erases your account, profile, messages, applications, posts and "
                          "listings. It CANNOT be undone." if delete else
                          "Your account will be switched off and you will be logged out. An administrator can "
                          "reactivate it later."), 10, C["text"], C["white"], wraplength=390, justify="left"
                    ).pack(anchor="w", padx=22)
        form = tk.Frame(win, bg=C["white"])
        form.pack(fill="x", padx=22)
        pw = tk.StringVar()
        theme.field(form, "Type your password to confirm")
        entry = theme.entry(form, pw, show="●")
        entry.pack(fill="x", ipady=5)
        entry.focus_set()
        sure = tk.IntVar()
        if delete:
            tk.Checkbutton(form, text="I understand this cannot be undone", variable=sure, bg=C["white"],
                           activebackground=C["white"], font=(theme.FONT, 9)).pack(anchor="w", pady=(10, 0))

        def confirm():
            acc = db.fetch_one("SELECT * FROM account_credentials WHERE user_id=%s", (self.uid,))
            if not pw.get() or not db.verify_password(pw.get(), acc["password_salt"], acc["password_hash"]):
                return messagebox.showerror("Password", "That password is wrong.", parent=win)
            if delete and not sure.get():
                return messagebox.showwarning("Confirm", "Please tick the box to confirm.", parent=win)
            win.destroy()
            if delete:
                self.erase_files()
                db.execute("DELETE FROM account_credentials WHERE user_id=%s", (self.uid,))
                messagebox.showinfo("Account deleted", "Your account was deleted. Goodbye!")
            else:
                db.execute("UPDATE account_credentials SET is_active=0 WHERE user_id=%s", (self.uid,))
                messagebox.showinfo("Account deactivated", "Your account was deactivated. You will now be logged out.")
            self.app.logout(confirm=False)
        entry.bind("<Return>", lambda e: confirm())
        btns = tk.Frame(win, bg=C["white"])
        btns.pack(fill="x", padx=22, pady=16)
        theme.button(btns, "Delete forever" if delete else "Deactivate", confirm, bg=C["red"], size=10,
                     hover_color="#8F3030").pack(side="right")
        theme.button(btns, "Cancel", win.destroy, bg=C["muted"], size=10, hover_color=C["dark"]).pack(side="right", padx=6)

    def erase_files(self):
        """Delete this user's own picture files (profile photo and Community post photos)."""
        paths = []
        if self.me["photo_path"]:
            paths.append(self.me["photo_path"])
        try:
            paths += [r["photo_path"] for r in db.fetch_all(
                "SELECT photo_path FROM community_posts WHERE user_id=%s AND photo_path IS NOT NULL", (self.uid,))]
        except Exception:                              # Community tables do not exist yet
            pass
        for path in paths:
            try:                                       # only files inside our own photo folders
                folder = os.path.abspath(os.path.dirname(path))
                allowed = (os.path.abspath(config.PHOTO_DIR),
                           os.path.abspath(os.path.join(os.path.dirname(config.PHOTO_DIR), "community_photos")))
                if folder in allowed and os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

    # ---------------- photo ----------------
    def draw_photo(self, first_time=False):
        theme.clear(self.photo_holder)
        theme.avatar(self.photo_holder, self.me["photo_path"], 150, C["white"], 70).pack()
        # show the Remove button only when the user has a photo
        if self.me["photo_path"]:
            self.remove_btn.pack(after=self.upload_btn, pady=(6, 0))
        else:
            self.remove_btn.pack_forget()
        if not first_time:
            self.app.refresh_banner()              # update the small photo in the top banner

    def upload_photo(self):
        """Pick an image, copy it into profile_photos/ and save its path."""
        path = filedialog.askopenfilename(title="Choose a profile photo",
                                          filetypes=[("Images", "*.png *.jpg *.jpeg *.gif"), ("All files", "*.*")])
        if not path:
            return
        os.makedirs(config.PHOTO_DIR, exist_ok=True)
        ext = os.path.splitext(path)[1].lower()
        dest = os.path.join(config.PHOTO_DIR, f"user_{self.uid}{ext}")
        shutil.copyfile(path, dest)
        db.execute("UPDATE user_profiles SET photo_path=%s WHERE user_id=%s", (dest, self.uid))
        self.me["photo_path"] = dest
        self.draw_photo()
        try:                                   # warn if the picture type is not readable without Pillow
            import PIL  # noqa: F401
        except ImportError:
            if ext in (".jpg", ".jpeg"):
                messagebox.showinfo("Install Pillow", "To display JPG photos run:  pip install pillow")

    def remove_photo(self):
        """Delete the profile photo: clear the path in MySQL and delete the copied file."""
        if not self.me["photo_path"]:
            return
        if not messagebox.askyesno("Remove photo", "Remove your profile photo?"):
            return
        old = self.me["photo_path"]
        db.execute("UPDATE user_profiles SET photo_path=NULL WHERE user_id=%s", (self.uid,))
        # delete the file only if it is our own copy inside profile_photos/ (never a file elsewhere)
        try:
            if os.path.abspath(os.path.dirname(old)) == os.path.abspath(config.PHOTO_DIR) and os.path.exists(old):
                os.remove(old)
        except OSError:
            pass
        self.me["photo_path"] = None
        self.draw_photo()

    # ---------------- save ----------------
    def save(self):
        name = self.v["full_name"].get().strip()
        region, province, muni, barangay = self.location.get()
        if not name:
            return messagebox.showwarning("Missing", "Your name is required.")
        db.execute("UPDATE user_profiles SET full_name=%s, email=%s, phone=%s, region=%s, province=%s, "
                   "municipality=%s, address=%s, bio=%s WHERE user_id=%s",
                   (name, self.v["email"].get().strip(), self.v["phone"].get().strip(), region, province, muni,
                    theme.join_address(self.v["address"].get(), barangay),
                    self.bio.get("1.0", "end").strip(), self.uid))
        session.user["full_name"] = name
        messagebox.showinfo("Saved", "Your profile was updated.")

    def change_password(self):
        acc = db.fetch_one("SELECT * FROM account_credentials WHERE user_id=%s", (self.uid,))
        if not db.verify_password(self.pw_old.get(), acc["password_salt"], acc["password_hash"]):
            return messagebox.showerror("Password", "Current password is wrong.")
        if len(self.pw_new.get()) < 6 or self.pw_new.get() != self.pw_confirm.get():
            return messagebox.showwarning("Password", "New password must be 6+ characters and match the confirmation.")
        salt = db.make_salt()
        db.execute("UPDATE account_credentials SET password_salt=%s, password_hash=%s WHERE user_id=%s",
                   (salt, db.hash_password(self.pw_new.get(), salt), self.uid))
        for v in (self.pw_old, self.pw_new, self.pw_confirm):
            v.set("")
        messagebox.showinfo("Password", "Password changed.")
