"""
main.py  --  START THE PROGRAM HERE:   python main.py

This file is the "controller" of Asik. It:
  * creates the main window
  * shows the Login page / Create-account page
  * builds the sidebar menu (the menu items depend on the user's role)
  * switches between pages when a sidebar button is clicked

Each page lives in its own file:
    login_page.py ........ Login
    register_page.py ..... Create account (job seeker / employer / lender / renter)
    dashboard_page.py .... Home dashboard
    rental_page.py ....... Equipment Rental (filter by region/province/municipality)
    lender_page.py ....... "Lend My Equipment" for rental owners
    jobs_page.py ......... "Hiring Now!" job board
    apply_page.py ........ Job-seeker application form (CRUD, auto-clears)
    post_vacancy_page.py . Employer: list a vacancy
    applicants_page.py ... Employer: applicant portal (Hire / Interview / Contact)
    community_page.py .... Community: tips, techniques, fun, marketplace
    messages_page.py ..... Chat between all users
    profile_page.py ...... Profile information + photo upload
    schedule_page.py ..... Farm schedule
    about_page.py ........ About Asik
    admin_page.py ........ Administrator dashboard and system management
"""

import gc
import importlib
import tkinter as tk
import traceback
from tkinter import messagebox

import config
import database as db
import languages
import session
import theme
from theme import C

languages.install()        # English / Filipino / Kapampangan / Bisaya (chosen on the Login page)

# Page registry:  menu name -> (python module, class name)
PAGES = {
    "Dashboard": ("dashboard_page", "DashboardPage"),
    "Equipment Rental": ("rental_page", "RentalPage"),
    "Lend My Equipment": ("lender_page", "LenderPage"),
    "Hiring Now!": ("jobs_page", "JobsPage"),
    "Apply for a Job": ("apply_page", "ApplyPage"),
    "Post a Vacancy": ("post_vacancy_page", "PostVacancyPage"),
    "Applicants Portal": ("applicants_page", "ApplicantsPage"),
    "Community": ("community_page", "CommunityPage"),
    "Messages": ("messages_page", "MessagesPage"),
    "Farm Schedule": ("schedule_page", "SchedulePage"),
    "My Profile": ("profile_page", "ProfilePage"),
    "About Us": ("about_page", "AboutPage"),
    "Admin Panel": ("admin_page", "AdminPage"),
}

ICONS = {
    "Dashboard": "⌂", "Equipment Rental": "🚜", "Lend My Equipment": "🤝",
    "Hiring Now!": "📢", "Apply for a Job": "📝", "Post a Vacancy": "➕",
    "Applicants Portal": "👥", "Community": "🌾", "Messages": "💬", "Farm Schedule": "📅",
    "My Profile": "👤", "About Us": "✨", "Admin Panel": "🛠",
}


class AsikApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{config.APP_NAME} | {config.APP_TAGLINE}")
        # Size the window to the screen. A fixed 1320x820 window is taller than many
        # laptop screens (especially with Windows display scaling), which squeezes the
        # scrolling areas to nothing and makes pages look blank.
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{min(1320, sw - 40)}x{min(820, sh - 90)}+10+10")
        self.root.minsize(900, 560)
        try:
            self.root.state("zoomed")                  # maximise on Windows
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)  # maximise on Linux
            except tk.TclError:
                pass
        self.root.report_callback_exception = self.show_error   # show button/click errors
        self.root.configure(bg=C["bg"])
        theme.setup_styles()
        self.page = None          # the page currently displayed
        self.nav = {}             # sidebar buttons
        self.show_login()

    # ------------------------------------------------------------------
    # Before login
    # ------------------------------------------------------------------
    def show_login(self):
        """Display the login screen (wipes the window and cached images first)."""
        from login_page import LoginPage
        for child in self.root.winfo_children():
            child.destroy()
        theme.clear_image_caches()
        gc.collect()
        self.root.configure(bg=C["dark"])
        LoginPage(self.root, self).pack(fill="both", expand=True)

    def show_register(self):
        """Display the create-account screen."""
        from register_page import RegisterPage
        for child in self.root.winfo_children():
            child.destroy()
        theme.clear_image_caches()
        gc.collect()
        self.root.configure(bg=C["dark"])
        RegisterPage(self.root, self).pack(fill="both", expand=True)

    def login_success(self, user_id):
        """Called by the login page after the password is verified."""
        profile = db.fetch_one(
            "SELECT u.user_id, u.username, p.full_name FROM account_credentials u "
            "JOIN user_profiles p ON p.user_id=u.user_id WHERE u.user_id=%s", (user_id,))
        profile["roles"] = db.get_roles(user_id)
        session.login(profile)
        self.show_app()

    # ------------------------------------------------------------------
    # After login: sidebar + page area
    # ------------------------------------------------------------------
    def menu_for_user(self):
        """Decide which sidebar items this user sees."""
        roles = session.user["roles"]
        if "admin" in roles:
            return ["Admin Panel", "Dashboard", "Equipment Rental", "Hiring Now!",
                    "Community", "Messages", "My Profile", "About Us"]
        items = ["Dashboard", "Equipment Rental"]
        if "lender" in roles:
            items.append("Lend My Equipment")
        items.append("Hiring Now!")
        if "job_seeker" in roles:
            items.append("Apply for a Job")
        if "employer" in roles:
            items += ["Post a Vacancy", "Applicants Portal"]
        items += ["Community", "Messages", "Farm Schedule", "My Profile", "About Us"]
        return items

    def show_app(self):
        """Build the sidebar (left), the top banner and the page area."""
        for child in self.root.winfo_children():
            child.destroy()
        theme.clear_image_caches()
        gc.collect()
        self.root.configure(bg=C["bg"])

        side = tk.Frame(self.root, bg=C["sidebar"], width=235)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        # ----- logo + name (transparent logo sits directly on the sidebar) -----
        plate = tk.Frame(side, bg=C["sidebar"])
        plate.pack(pady=(12, 2))
        theme.logo_widget(plate, 70, C["sidebar"], 30).pack(padx=10, pady=4)
        theme.label(side, config.APP_NAME, 20, C["sidebar_ink"], C["sidebar"], True).pack()
        theme.label(side, "SMART AGRICULTURE", 8, C["sidebar_muted"], C["sidebar"], True).pack(pady=(0, 8))

        # ----- menu buttons: the active page is a dark-green pill -----
        self.nav = {}
        for name in self.menu_for_user():
            label = languages.tr(f"  {ICONS[name]}   {name}")
            size = 10 if len(label) <= 24 else 9 if len(label) <= 27 else 8 if len(label) <= 31 else 7   # long translations: smaller text
            b = tk.Button(side, text=label, anchor="w",
                          font=(theme.FONT, size, "bold"), bg=C["sidebar"], fg=C["sidebar_text"],
                          activebackground=C["sidebar_hover"], activeforeground=C["sidebar_ink"],
                          relief="flat", bd=0, padx=10, pady=7, cursor="hand2",
                          command=lambda n=name: self.navigate(n))
            b.pack(fill="x", padx=12, pady=2)
            self.nav[name] = b

        tk.Frame(side, bg=C["sidebar"]).pack(fill="both", expand=True)

        # ----- little farm scene (barn, hills and a cow) -----
        scene = tk.Canvas(side, width=235, height=100, bg=C["sidebar"], highlightthickness=0)
        scene.pack(fill="x")
        scene.create_oval(-40, 62, 130, 160, fill="#A9D08E", outline="")
        scene.create_oval(70, 70, 280, 170, fill="#8FC27A", outline="")
        scene.create_rectangle(28, 38, 78, 78, fill="#C0392B", outline="")           # barn walls
        scene.create_polygon(22, 40, 53, 16, 84, 40, fill="#8E2B22", outline="")      # barn roof
        scene.create_rectangle(44, 52, 62, 78, fill="#F7E7D0", outline="#8E2B22")     # door
        scene.create_line(44, 52, 62, 78, fill="#8E2B22")
        scene.create_line(62, 52, 44, 78, fill="#8E2B22")
        scene.create_text(150, 66, text="🐄", font=(theme.FONT, 26))
        scene.create_text(205, 22, text="☀️", font=(theme.FONT, 16))

        # ----- who is signed in -----
        box = tk.Frame(side, bg=C["sidebar_hover"])
        box.pack(fill="x", padx=12, pady=6)
        theme.label(box, "●  SIGNED IN", 8, C["green"], C["sidebar_hover"], True
                    ).pack(anchor="w", padx=10, pady=(8, 2))
        theme.label(box, session.user["full_name"], 11, C["sidebar_ink"], C["sidebar_hover"], True
                    ).pack(anchor="w", padx=10)
        roles = ", ".join(r.replace("_", " ").title() for r in session.user["roles"])
        theme.label(box, roles, 8, C["sidebar_muted"], C["sidebar_hover"]).pack(anchor="w", padx=10, pady=(0, 8))
        # (the Logout button now lives on the My Profile page)
        tk.Frame(side, bg=C["sidebar"], height=10).pack()

        # ----- right side: banner on top, pages underneath -----
        self.main = tk.Frame(self.root, bg=C["bg"])
        self.main.pack(side="left", fill="both", expand=True)
        self.build_banner(self.main)
        self.content = tk.Frame(self.main, bg=C["bg"])
        self.content.pack(fill="both", expand=True)
        self.navigate(self.menu_for_user()[0])

    # ------------------------------------------------------------------
    # Top banner (sky, hills, sun, greeting pill)
    # ------------------------------------------------------------------
    def build_banner(self, parent):
        """Painted banner with a 'Hello, <name>!' pill that opens the profile page."""
        banner = tk.Canvas(parent, height=78, bg=C["bg"], highlightthickness=0)
        banner.pack(fill="x", padx=14, pady=(10, 0))
        first = session.user["full_name"].split()[0]
        holder = {"avatar": None}

        def blend(c1, c2, t):
            a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
            b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
            return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

        def round_rect(x1, y1, x2, y2, r, **kw):
            pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
                   x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
            return banner.create_polygon(pts, smooth=True, **kw)

        def draw(_e=None):
            w, h = max(banner.winfo_width(), 400), 78
            # read the photo each time so a new / removed profile photo shows up at once
            photo = db.fetch_one("SELECT photo_path FROM user_profiles WHERE user_id=%s", (session.user_id(),))
            photo_path = photo["photo_path"] if photo else None
            banner.delete("all")
            for y in range(h):                                   # sky gradient
                banner.create_line(0, y, w, y, fill=blend("#D6ECF0", "#EEF6D6", y / h))
            sun_x = int(w * 0.56)
            banner.create_oval(sun_x - 34, -6, sun_x + 34, 62, fill="#FBEFB8", outline="")   # glow
            banner.create_oval(sun_x - 22, 6, sun_x + 22, 50, fill="#F6D875", outline="")    # sun
            for cx, cy, rx, ry, col in ((0.10, 84, 240, 56, "#BFDDA6"), (0.32, 92, 260, 50, "#A9D08E"),
                                        (0.62, 90, 300, 46, "#BFDDA6"), (0.90, 88, 250, 54, "#A9D08E")):
                banner.create_oval(w * cx - rx, cy - ry, w * cx + rx, cy + ry, fill=col, outline="")
            for tx in (0.16, 0.19, 0.29):                                                    # round trees
                x = w * tx
                banner.create_rectangle(x - 2, 46, x + 2, 62, fill="#7A5C3B", outline="")
                banner.create_oval(x - 11, 28, x + 11, 52, fill="#5E9E5A", outline="")
            # greeting pill
            x2, x1 = w - 12, w - 250
            round_rect(x1, 14, x2, 62, 24, fill="#FFFFFF", outline="#E3EED0", tags="pill")
            banner.create_text(x1 + 24, 38, text="🔔", font=(theme.FONT, 14), tags="pill")
            banner.create_oval(x1 + 36, 31, x1 + 43, 38, fill="#E5534B", outline="", tags="pill")
            if holder["avatar"] is not None:
                holder["avatar"].destroy()
            holder["avatar"] = theme.avatar(banner, photo_path, 34, "#FFFFFF", 18)
            banner.create_window(x1 + 66, 38, window=holder["avatar"], tags="pill")
            banner.create_text(x1 + 90, 38, text=f"Hello, {first}!", anchor="w",
                               font=(theme.FONT, 12, "bold"), fill=C["sidebar_ink"], tags="pill")
            banner.create_text(x2 - 20, 38, text="⌄", font=(theme.FONT, 12), fill=C["muted"], tags="pill")
            banner.tag_bind("pill", "<Button-1>", lambda e: self.navigate("My Profile"))
            holder["avatar"].bind("<Button-1>", lambda e: self.navigate("My Profile"))
            banner.configure(cursor="arrow")

        banner.bind("<Configure>", draw)
        self.refresh_banner = draw           # the Profile page calls this after a photo change

    def navigate(self, name, **kwargs):
        """Show a page. Extra keyword arguments are passed on to the page."""
        if self.page is not None:
            self.page.destroy()                    # remove the old page
        for n, btn in self.nav.items():            # highlight the active menu item
            btn.configure(bg=C["sidebar_active"] if n == name else C["sidebar"],
                          fg=C["white"] if n == name else C["sidebar_text"],
                          activeforeground=C["white"] if n == name else C["sidebar_ink"])
        module_name, class_name = PAGES[name]
        try:
            page_class = getattr(importlib.import_module(module_name), class_name)
            self.page = page_class(self.content, self, **kwargs)
        except Exception:
            # Something went wrong while building the page. Instead of leaving a
            # BLANK screen, show the error text so it can be read and fixed.
            err = traceback.format_exc()
            print(err)
            self.page = tk.Frame(self.content, bg=C["bg"])
            theme.label(self.page, f"⚠ The '{name}' page could not load", 16, C["red"], C["bg"], True
                        ).pack(anchor="w", padx=28, pady=(24, 4))
            theme.label(self.page, "Please send this message to your developer:", 10, C["muted"], C["bg"]
                        ).pack(anchor="w", padx=28)
            box = tk.Text(self.page, font=("Consolas", 9), wrap="word", bg=C["white"], relief="solid", bd=1)
            box.pack(fill="both", expand=True, padx=28, pady=12)
            box.insert("1.0", err)
        self.page.pack(fill="both", expand=True)

    def show_error(self, exc_type, exc, tb):
        """Called by tkinter when a button/click handler crashes."""
        err = "".join(traceback.format_exception(exc_type, exc, tb))
        print(err)
        messagebox.showerror("Something went wrong", err[-1200:])

    def logout(self, confirm=True):
        """Log out, wipe caches, and return to the login screen."""
        if not confirm or messagebox.askyesno("Log Out", "Are you sure you want to log out?"):
            session.logout()
            self.page = None
            self.nav = {}
            theme.clear_image_caches()
            gc.collect()
            self.show_login()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        AsikApp(root)
    except Exception as err:            # most common cause: MySQL is not set up yet
        messagebox.showerror(
            "Asik could not start",
            f"{err}\n\nCheck config.py and run:  python setup_database.py")
        raise
    root.mainloop()