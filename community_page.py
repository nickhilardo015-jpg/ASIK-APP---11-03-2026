"""
community_page.py  --  "Community": learn, share, have fun and trade, all on ONE page.

WHAT YOU CAN DO
  * LEARN        read farming tips, techniques and step-by-step procedures from
                 other farmers (tab "Learn") and share your own
  * ENTERTAIN    jokes, riddles and farm photos (tab "Fun")
  * MARKETPLACE  advertise products, rentals, job vacancies, or ask for supplies
                 and anything the farm needs (tab "Marketplace"), then press
                 "Message" to talk to the seller
  * POST         title + description + (optional) photo + category.
                 You can EDIT the description / photo / title and DELETE your post.
  * REACT        👍 or 👎 only. Press the same button again to remove your
                 reaction, or press the other one to change it.
  * COMMENT      add a comment, EDIT it or REMOVE it later.
  * SAVE         bookmark a post (tab "Saved").
  * SHARE        put a post on YOUR profile (tab "My Profile"; also shown on
                 the My Profile page).
  * NOTIFICATIONS  the yellow bar at the top tells you who reacted to or
                 commented on your posts.
  * REPORT       anyone can report a post that is spam, false, inappropriate or a scam.
  * MODERATION   only the OWNER of a post can delete it. For a reported post the
                 ADMINISTRATOR decides: TAKE DOWN or KEEP it. Both decisions have an
                 OPTIONAL explanation, which is sent as a chat message and saved in
                 the moderation log. A taken-down post is only HIDDEN (not deleted).
  * APPEAL       the owner of a taken-down post sees it in "My Profile" with an
                 "Appeal this decision" button: supporting details + optional
                 evidence files. The administrator reviews the appeal and either
                 keeps the post removed or presses "Put back": the post returns
                 at once and the owner gets an apology and a thank-you message.

DATA  (MySQL tables, created automatically the first time this page opens)
  community_posts      the posts (+ optional photo path)
  community_reactions  one 👍/👎 per user per post
  community_comments   comments
  community_saves      bookmarks
  community_shares     posts shared on a profile
  community_seen       when a user last opened the notifications
  community_reports    reports made by users about a post
  community_mod_log    record of every admin decision (take down, keep, uphold, put back)
  community_appeals    an owner's appeal against a take-down (+ the admin's decision)
  community_appeal_files  the evidence files attached to an appeal
  community_meta       remembers that the starter posts were added
Photos are copied into the `community_photos` folder, appeal evidence into `community_appeals`.
"""

import os
import shutil
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import config
import database as db
import emoji_picker
import session
import theme
from messages_page import MessagesPage, ROLE_STYLE, blend, ink, roles_of
from theme import C

COMMUNITY_DIR = getattr(config, "COMMUNITY_DIR",
                        os.path.join(os.path.dirname(config.PHOTO_DIR), "community_photos"))
APPEAL_DIR = os.path.join(os.path.dirname(COMMUNITY_DIR), "community_appeals")      # appeal evidence files
MAX_EVIDENCE = 5                       # files per appeal
MAX_EVIDENCE_MB = 10

# ------------------------------------------------------------------
# categories:  name -> (icon, light colour, dark colour)
# ------------------------------------------------------------------
CATEGORIES = {
    "Tip":               ("💡", "#FFF0C5", "#A87312"),
    "Technique":         ("🌱", "#DDF0DA", "#2F7A4A"),
    "Procedure":         ("📋", "#DCEBFF", "#3868B7"),
    "Entertainment":     ("🎉", "#EDE3FF", "#7752B5"),
    "Product Ad":        ("🧺", "#FFE3CC", "#B66A31"),
    "Rental Ad":         ("🚜", "#FFF0C5", "#A87312"),
    "Vacancy":           ("📢", "#DCEBFF", "#3868B7"),
    "Supplies / Wanted": ("🛒", "#FFD6DC", "#BD5267"),
}
LEARN = ["Tip", "Technique", "Procedure"]
FUN = ["Entertainment"]
MARKET = ["Product Ad", "Rental Ad", "Vacancy", "Supplies / Wanted"]

TABS = [("feed", "🌾 All"), ("learn", "📚 Learn"), ("fun", "🎉 Fun"),
        ("market", "🛒 Marketplace"), ("saved", "🔖 Saved"), ("profile", "👤 My Profile")]
ADMIN_TAB = ("reports", "🚩 Reported")
ADMIN_TAB2 = ("removed", "🛑 Removed & Appeals")
REPORT_REASONS = ["Spam or advertising abuse", "False or misleading information", "Inappropriate content",
                  "Scam or fraud", "Other"]
TAKEDOWN_REASONS = {
    "Spam": "Your post was removed because it was spam.",
    "False information": "Your post was removed because it contained false or misleading information.",
    "Inappropriate": "Your post was removed because it contained inappropriate content.",
    "Scam / fraud": "Your post was removed because it looked like a scam or fraudulent offer.",
    "Community rules": "Your post was removed because it did not follow the community rules.",
}
KEEP_REASONS = {
    "No rule broken": "We checked the post and it follows the community rules.",
    "Nothing misleading": "We checked the details and found nothing false or misleading.",
    "Report not confirmed": "We could not confirm the problem that was reported.",
    "Allowed content": "This kind of post is allowed in the Community.",
}
TAB_HINT = {
    "removed": "Posts taken down by an administrator. Appeals are shown first - press Put back if it was a mistake (administrators only).",
    "reports": "Posts that users reported and nobody has dealt with yet (administrators only).",
    "feed": "Everything the community shares.",
    "learn": "Farming tips, techniques and procedures.",
    "fun": "Jokes, riddles and farm photos.",
    "market": "Advertise products, rentals and vacancies, or ask for supplies the farm needs.",
    "saved": "Posts you bookmarked.",
    "profile": "Your own posts and the posts you shared on your profile. A taken-down post stays here so you can appeal.",
}

# ------------------------------------------------------------------
# table definitions (also written in schema.sql)
# ------------------------------------------------------------------
COMMUNITY_DDL = [
    """CREATE TABLE IF NOT EXISTS community_posts (
    post_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    category    VARCHAR(30)  NOT NULL,
    title       VARCHAR(150) NOT NULL,
    body        TEXT NOT NULL,
    photo_path  VARCHAR(255) NULL,
    price       VARCHAR(60)  NULL,
    location    VARCHAR(150) NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    edited_at   TIMESTAMP NULL DEFAULT NULL,
    is_removed  TINYINT(1) NOT NULL DEFAULT 0,
    removed_at  TIMESTAMP NULL DEFAULT NULL,
    INDEX idx_post_category (category),
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_reactions (
    post_id     INT NOT NULL,
    user_id     INT NOT NULL,
    reaction    VARCHAR(4) NOT NULL,
    reacted_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_comments (
    comment_id  INT AUTO_INCREMENT PRIMARY KEY,
    post_id     INT NOT NULL,
    user_id     INT NOT NULL,
    body        TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    edited_at   TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_saves (
    post_id   INT NOT NULL,
    user_id   INT NOT NULL,
    saved_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_shares (
    post_id    INT NOT NULL,
    user_id    INT NOT NULL,
    shared_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_seen (
    user_id  INT PRIMARY KEY,
    seen_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_reports (
    report_id    INT AUTO_INCREMENT PRIMARY KEY,
    post_id      INT NOT NULL,
    reporter_id  INT NOT NULL,
    reason       VARCHAR(60)  NOT NULL,
    details      VARCHAR(255) NULL,
    status       VARCHAR(10)  NOT NULL DEFAULT 'Open',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_one_report (post_id, reporter_id),
    FOREIGN KEY (post_id)     REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (reporter_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_mod_log (
    log_id         INT AUTO_INCREMENT PRIMARY KEY,
    post_id        INT NULL,
    post_title     VARCHAR(150) NOT NULL,
    category       VARCHAR(30),
    owner_id       INT NULL,
    admin_id       INT NULL,
    action         VARCHAR(12) NOT NULL DEFAULT 'Take down',
    reason         TEXT NULL,
    taken_down_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES account_credentials(user_id) ON DELETE SET NULL,
    FOREIGN KEY (admin_id) REFERENCES account_credentials(user_id) ON DELETE SET NULL
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_appeals (
    appeal_id   INT AUTO_INCREMENT PRIMARY KEY,
    log_id      INT NULL,
    post_id     INT NOT NULL,
    user_id     INT NOT NULL,
    details     TEXT NOT NULL,
    status      VARCHAR(10) NOT NULL DEFAULT 'Pending',
    admin_id    INT NULL,
    admin_note  TEXT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at  TIMESTAMP NULL DEFAULT NULL,
    INDEX idx_appeal_status (status),
    FOREIGN KEY (post_id)  REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)  REFERENCES account_credentials(user_id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id) REFERENCES account_credentials(user_id) ON DELETE SET NULL
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_appeal_files (
    file_id    INT AUTO_INCREMENT PRIMARY KEY,
    appeal_id  INT NOT NULL,
    file_path  VARCHAR(255) NOT NULL,
    FOREIGN KEY (appeal_id) REFERENCES community_appeals(appeal_id) ON DELETE CASCADE
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS community_meta (
    k  VARCHAR(40) PRIMARY KEY,
    v  VARCHAR(255)
) ENGINE=InnoDB""",
]

# starter posts: (username, category, title, body, price, location, hours ago)
SEED_POSTS = [
    ("admin", "Procedure", "Simple seed germination test",
     "Test your seeds before planting so you do not waste land and labor.\n"
     "1. Count 100 seeds.\n2. Lay them on a damp cloth or paper towel, fold it and put it in a plastic bag.\n"
     "3. Keep it warm and shaded, and keep it moist.\n4. After 5-7 days count how many sprouted.\n"
     "80 or more sprouts = good seed. Below 70, sow more seeds per hill or buy new seed.", None, None, 30),
    ("admin", "Tip", "Mulch to save water",
     "Cover the soil around your vegetables with 5-8 cm of rice straw or dried leaves. It keeps moisture in, "
     "keeps weeds down and cools the soil in the dry season.", None, None, 26),
    ("admin", "Technique", "Compost in layers",
     "Pile dry material (rice straw, dried leaves) and green material (grass cuttings, vegetable scraps, manure) "
     "in alternating layers about 15 cm thick. Keep the pile damp like a squeezed sponge and turn it every "
     "2 weeks. It is ready in 2-3 months, when it smells like fresh earth.", None, None, 22),
    ("seeker", "Technique", "Corn and mongo intercropping",
     "I plant mongo beans between my corn rows. The beans cover the soil, give extra income and leave nitrogen "
     "for the next crop. Has anyone tried this on sandy soil?", None, None, 18),
    ("seeker", "Entertainment", "Riddle time: who am I? 🥔",
     "I grow underground, I have many eyes but cannot see, and you can fry me, boil me or mash me. "
     "What am I? Answer in the comments!", None, None, 14),
    ("admin", "Entertainment", "Share your best farm sunrise 🌅",
     "Post a photo of the sunrise over your field. Let's see the prettiest farm views in the Philippines!",
     None, None, 10),
    ("lender", "Rental Ad", "Hand tractor for rent",
     "Well-maintained hand tractor with operator, good for land preparation of 1-3 hectares. "
     "Message me to reserve a date. (sample ad)", "₱1,500 / day", "Cabanatuan City, Nueva Ecija", 6),
    ("employer", "Vacancy", "Harvest helpers needed",
     "Hiring farm laborers for the palay harvest. Daily pay, meals provided. Message me or apply on the "
     "Hiring Now! page. (sample ad)", "₱700 / day", "Tarlac City, Tarlac", 4),
    ("employer", "Supplies / Wanted", "Looking for organic fertilizer",
     "Need about 50 sacks of vermicompost or other organic fertilizer. Please message me your price per sack "
     "and delivery area. (sample request)", None, "Central Luzon", 2),
    ("lender", "Product Ad", "Fresh pechay and kangkong",
     "Harvested this morning, grown without chemical pesticides. Pick-up or delivery within the town. "
     "(sample ad)", "₱40 / bundle", "Bay, Laguna", 1),
]

_tables_ready = False


def ensure_tables():
    """Create the community tables once per run and add the starter posts the very first time."""
    global _tables_ready
    if _tables_ready:
        return
    for ddl in COMMUNITY_DDL:
        db.execute(ddl)
    migrate_old_tables()
    if not db.fetch_one("SELECT v FROM community_meta WHERE k='seeded'"):
        seed_demo()
        db.execute("INSERT INTO community_meta (k, v) VALUES ('seeded', '1')")
    _tables_ready = True


def _add_column(table, column, definition):
    """ALTER TABLE ... ADD COLUMN, but only when the column is missing (safe to run every time)."""
    if not db.fetch_one("SHOW COLUMNS FROM " + table + " LIKE %s", (column,)):
        db.execute("ALTER TABLE " + table + " ADD COLUMN " + definition)


def migrate_old_tables():
    """Databases made before appeals existed get the new columns added here."""
    _add_column("community_posts", "is_removed", "is_removed TINYINT(1) NOT NULL DEFAULT 0")
    _add_column("community_posts", "removed_at", "removed_at TIMESTAMP NULL DEFAULT NULL")
    _add_column("community_mod_log", "post_id", "post_id INT NULL")
    _add_column("community_mod_log", "action", "action VARCHAR(12) NOT NULL DEFAULT 'Take down'")
    db.execute("ALTER TABLE community_mod_log MODIFY reason TEXT NULL")      # the explanation is optional now


def seed_demo():
    """A few starter posts, reactions and comments so the page is not empty."""
    ids = {r["username"]: r["user_id"] for r in db.fetch_all("SELECT user_id, username FROM account_credentials")}
    me = session.user_id()

    def uid(name):
        return ids.get(name) or me
    post_ids = []
    for name, cat, title, body, price, loc, hours in SEED_POSTS:
        post_ids.append(db.execute(
            "INSERT INTO community_posts (user_id, category, title, body, price, location, created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s, NOW() - INTERVAL %s HOUR)",
            (uid(name), cat, title, body, price, loc, hours)))
    for pid, who, kind in ((post_ids[0], "seeker", "up"), (post_ids[0], "employer", "up"),
                           (post_ids[1], "seeker", "up"), (post_ids[2], "lender", "up")):
        if uid(who) != uid("admin"):
            db.execute("INSERT IGNORE INTO community_reactions (post_id, user_id, reaction) VALUES (%s,%s,%s)",
                       (pid, uid(who), kind))
    for pid, who, text in ((post_ids[0], "seeker", "Thank you! I will try this before the planting season."),
                           (post_ids[3], "admin", "Nice idea - mongo also sells well at the market."),
                           (post_ids[4], "lender", "Potato! 😄")):
        db.execute("INSERT INTO community_comments (post_id, user_id, body) VALUES (%s,%s,%s)",
                   (pid, uid(who), text))


# ------------------------------------------------------------------
# photo helpers
# ------------------------------------------------------------------
_img_cache = {}


def load_photo(path, max_w, max_h):
    """Return a PhotoImage of the post picture scaled to fit, or None."""
    if not path or not os.path.exists(path):
        return None
    key = (path, os.path.getmtime(path), max_w, max_h)
    if key in _img_cache:
        return _img_cache[key]
    img = None
    try:
        from PIL import Image, ImageTk
        pic = Image.open(path).convert("RGB")
        pic.thumbnail((max_w, max_h), Image.LANCZOS)
        img = ImageTk.PhotoImage(pic)
    except ImportError:                                  # no Pillow: PNG / GIF only, rough scaling
        try:
            raw = tk.PhotoImage(file=path)
            factor = max(1, -(-raw.width() // max_w), -(-raw.height() // max_h))
            img = raw.subsample(factor, factor)
        except tk.TclError:
            img = None
    except Exception:
        img = None
    if img:
        _img_cache[key] = img
    return img


def store_photo(src, post_id):
    """Copy a chosen picture into community_photos/ and return the new path."""
    os.makedirs(COMMUNITY_DIR, exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    dest = os.path.join(COMMUNITY_DIR, "post_%d_%d%s" % (post_id, int(time.time()), ext))
    shutil.copyfile(src, dest)
    return dest


def remove_photo_file(path):
    """Delete a picture, but only if it is one of OUR copies inside community_photos/."""
    try:
        if path and os.path.abspath(os.path.dirname(path)) == os.path.abspath(COMMUNITY_DIR) \
                and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def store_evidence(src, appeal_id):
    """Copy an evidence file into community_appeals/ and return the new path."""
    os.makedirs(APPEAL_DIR, exist_ok=True)
    name = os.path.basename(src).replace(" ", "_")
    dest = os.path.join(APPEAL_DIR, "appeal_%d_%d_%s" % (appeal_id, int(time.time() * 1000) % 100000000, name))
    shutil.copyfile(src, dest)
    return dest


def open_file(path):
    """Open a file with the program Windows (or the OS) uses for it."""
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)
        else:
            import subprocess
            import sys
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])
    except Exception:
        messagebox.showwarning("Cannot open", "This file cannot be opened:\n" + str(path))


def send_message(sender, receiver, body):
    """A chat message (it appears in the Messages page)."""
    if receiver:
        db.execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (%s,%s,%s)", (sender, receiver, body))


def when(dt):
    return dt.strftime("%b %d, %I:%M %p") if dt else ""


def small_button(parent, text, command, bg="#F1F5EC", fg=None, bold=False):
    """A flat little button used on the post cards."""
    fg = fg or C["text"]
    hover = blend(bg, "#000000", 0.08)
    b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, relief="flat", bd=0, padx=10, pady=4,
                  font=(theme.FONT, 9, "bold" if bold else "normal"), cursor="hand2",
                  activebackground=hover, activeforeground=fg)
    b.bind("<Enter>", lambda e: b.configure(bg=hover))
    b.bind("<Leave>", lambda e: b.configure(bg=bg))
    return b


_avatars = {}


def avatar(parent, photo_path, size, role, bg):
    """Round profile photo with a ring in the person's role colour (see messages_page)."""
    light, dark, _ = ROLE_STYLE[role]
    path = photo_path if photo_path and os.path.exists(photo_path) else None
    try:
        key = (path, os.path.getmtime(path) if path else 0, size, role)
        if key not in _avatars:
            _avatars[key] = MessagesPage._round_image(path, size, light, dark)
        lbl = tk.Label(parent, image=_avatars[key], bg=bg, bd=0)
        lbl.image = _avatars[key]
        return lbl
    except Exception:
        return theme.avatar(parent, path, size, bg)


# ==================================================================
class CommunityPage(tk.Frame):
    PAGE_SIZE = 20

    def __init__(self, parent, app, post_id=None):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        ensure_tables()
        self.me = session.user_id()
        self.is_admin = "admin" in session.user["roles"]
        self.tab = "feed"
        self.limit = self.PAGE_SIZE
        self.only_post = post_id          # show just one post (opened from a notification)
        self.open_comments = set()        # posts whose comments are expanded
        self._timer = None
        self._reload_job = None
        self._built_width = 0
        self.tab_buttons = {}
        self.tabs = TABS + ([ADMIN_TAB, ADMIN_TAB2] if self.is_admin else [])      # only admins get these tabs

        theme.page_header(self, "Community 🌾", "Learn farming techniques, share your own, have fun and trade.",
                          C["green_dark"])

        # ---------- notification bar ----------
        self.notif_bar = tk.Frame(self, bg=C["white"], highlightbackground=C["border"], highlightthickness=1)
        self.notif_bar.pack(fill="x", padx=28, pady=(0, 8))

        # ---------- search + new post ----------
        top = tk.Frame(self, bg=C["bg"])
        top.pack(fill="x", padx=28, pady=(0, 6))
        self.search = theme.SearchBar(top, self.on_search, "Search posts, topics or people...")
        self.search.pack(side="left", fill="x", expand=True)
        theme.button(top, "➕ New Post", lambda: self.open_editor(None), size=10).pack(side="left", padx=(8, 0))

        # ---------- tabs ----------
        tabs = tk.Frame(self, bg=C["bg"])
        tabs.pack(fill="x", padx=28, pady=(0, 4))
        for key, text in self.tabs:
            b = tk.Button(tabs, text=text, command=lambda k=key: self.set_tab(k), relief="flat", bd=0,
                          padx=14, pady=6, cursor="hand2", font=(theme.FONT, 10, "bold"))
            b.pack(side="left", padx=(0, 6))
            self.tab_buttons[key] = b
        self.hint = theme.label(self, "", 9, C["muted"], C["bg"])
        self.hint.pack(anchor="w", padx=30, pady=(0, 4))

        # ---------- the scrolling feed (own canvas so the mouse wheel always works) ----------
        wrap = tk.Frame(self, bg=C["bg"])
        wrap.pack(fill="both", expand=True, padx=28, pady=(0, 14))
        self.canvas = tk.Canvas(wrap, bg=C["bg"], highlightthickness=0, height=260)
        bar = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.feed = tk.Frame(self.canvas, bg=C["bg"])
        self._win = self.canvas.create_window((0, 0), window=self.feed, anchor="nw")
        self.feed.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        if theme.SHOW_SCROLLBAR:
            self.canvas.configure(yscrollcommand=bar.set)
            bar.pack(side="right", fill="y")
        else:
            theme.autohide_scrollbar(self.canvas, bar)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bind_all("<MouseWheel>", self.on_wheel)
        theme.bind_scroll_keys(self, self.canvas)

        self.paint_tabs()
        self.refresh_notifications()
        self.after(60, self.reload)               # wait until the window has its real size
        self.poll()

    # ================================================================
    # small UI helpers
    # ================================================================
    def on_wheel(self, event):
        """Mouse wheel scrolls the feed (ignored for pop-up windows)."""
        try:
            if isinstance(event.widget, tk.Misc) and event.widget.winfo_toplevel() is self.winfo_toplevel():
                self.canvas.yview_scroll(theme.wheel_step(event), "units")
        except tk.TclError:
            pass

    def on_canvas_resize(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)
        if self._built_width and abs(event.width - self._built_width) > 160:   # re-wrap the text
            if self._reload_job:
                self.after_cancel(self._reload_job)
            self._reload_job = self.after(250, self.reload)

    def wrap_width(self):
        return max(380, min(780, self.canvas.winfo_width() - 150))

    def paint_tabs(self):
        for key, b in self.tab_buttons.items():
            on = key == self.tab and not self.only_post
            b.configure(bg=C["sidebar_active"] if on else C["white"], fg=C["white"] if on else C["sidebar_ink"],
                        activebackground=C["green_dark"], activeforeground=C["white"])
        self.hint.configure(text=TAB_HINT[self.tab])

    def set_tab(self, key):
        self.tab = key
        self.only_post = None
        self.limit = self.PAGE_SIZE
        self.paint_tabs()
        self.reload()
        self.canvas.yview_moveto(0)

    def on_search(self):
        self.only_post = None
        self.limit = self.PAGE_SIZE
        self.paint_tabs()
        self.reload()

    # ================================================================
    # loading posts
    # ================================================================
    def query_posts(self):
        me = self.me
        sql = ("SELECT p.*, u.full_name, u.photo_path AS author_photo, "
               "(SELECT GROUP_CONCAT(role) FROM user_roles WHERE user_id=p.user_id) AS roles, "
               "(SELECT COUNT(*) FROM community_reactions r WHERE r.post_id=p.post_id AND r.reaction='up') AS ups, "
               "(SELECT COUNT(*) FROM community_reactions r WHERE r.post_id=p.post_id AND r.reaction='down') AS downs, "
               "(SELECT r.reaction FROM community_reactions r WHERE r.post_id=p.post_id AND r.user_id=%s) AS my_react, "
               "(SELECT COUNT(*) FROM community_comments c WHERE c.post_id=p.post_id) AS n_comments, "
               "(SELECT COUNT(*) FROM community_saves s WHERE s.post_id=p.post_id AND s.user_id=%s) AS saved, "
               "(SELECT COUNT(*) FROM community_shares h WHERE h.post_id=p.post_id AND h.user_id=%s) AS shared, "
               "(SELECT COUNT(*) FROM community_reports x WHERE x.post_id=p.post_id AND x.status='Open') AS n_reports, "
               "(SELECT COUNT(*) FROM community_reports x WHERE x.post_id=p.post_id AND x.reporter_id=%s) AS my_reported "
               "FROM community_posts p JOIN user_profiles u ON u.user_id=p.user_id")
        params = [me, me, me, me]
        where = []
        order = "p.created_at DESC, p.post_id DESC"
        if self.only_post:
            where.append("p.post_id=%s")
            params.append(self.only_post)
            if not self.is_admin:                       # a removed post is visible only to its owner (and admins)
                where.append("(p.is_removed=0 OR p.user_id=%s)")
                params.append(me)
        else:
            if self.tab == "removed" and self.is_admin:
                where.append("p.is_removed=1")
                order = ("(SELECT COUNT(*) FROM community_appeals a WHERE a.post_id=p.post_id "
                         "AND a.status='Pending') DESC, p.removed_at DESC, p.post_id DESC")
            elif self.tab != "profile":
                where.append("p.is_removed=0")
            cats = {"learn": LEARN, "fun": FUN, "market": MARKET}.get(self.tab)
            if cats:
                where.append("p.category IN (%s)" % ",".join(["%s"] * len(cats)))
                params += cats
            elif self.tab == "reports" and self.is_admin:
                where.append("EXISTS (SELECT 1 FROM community_reports x2 "
                             "WHERE x2.post_id=p.post_id AND x2.status='Open')")
            elif self.tab == "saved":
                where.append("EXISTS (SELECT 1 FROM community_saves s2 WHERE s2.post_id=p.post_id AND s2.user_id=%s)")
                params.append(me)
            elif self.tab == "profile":
                where.append("((p.is_removed=0 AND (p.user_id=%s OR EXISTS (SELECT 1 FROM community_shares h2 "
                             "WHERE h2.post_id=p.post_id AND h2.user_id=%s))) OR (p.is_removed=1 AND p.user_id=%s))")
                params += [me, me, me]
            text = self.search.text()
            if text:
                where.append("(p.title LIKE %s OR p.body LIKE %s OR u.full_name LIKE %s OR p.category LIKE %s)")
                params += [f"%{text}%"] * 4
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY " + order + " LIMIT %d" % (self.limit + 1)
        return db.fetch_all(sql, params)

    def reload(self):
        """Rebuild the feed (keeps the scroll position)."""
        self._reload_job = None
        if not self.winfo_exists():
            return
        top = self.canvas.yview()[0]
        theme.clear(self.feed)
        self._built_width = self.canvas.winfo_width()
        rows = self.query_posts()
        more = len(rows) > self.limit
        rows = rows[:self.limit]

        if self.only_post:
            bar = tk.Frame(self.feed, bg=C["yellow"])
            bar.pack(fill="x", pady=(0, 6), padx=(0, 12))
            theme.label(bar, "Showing one post from your notifications.", 10, C["dark"], C["yellow"], True
                        ).pack(side="left", padx=12, pady=8)
            theme.button(bar, "Show all posts", lambda: self.set_tab(self.tab), size=9,
                         pady=4).pack(side="right", padx=10, pady=6)
        if not rows:
            empty = "Nothing here yet."
            if self.tab == "saved":
                empty = "You have not saved any post yet. Press 🔖 Save on a post you want to keep."
            elif self.tab == "removed":
                empty = "No post is taken down right now."
            elif self.tab == "profile":
                empty = "You have not posted or shared anything yet. Press ➕ New Post to start."
            elif self.search.text():
                empty = "No posts match your search."
            theme.label(self.feed, empty, 11, C["muted"], C["bg"], wraplength=500, justify="center").pack(pady=40)
        comments = self.fetch_comments([p["post_id"] for p in rows if p["post_id"] in self.open_comments])
        for p in rows:
            self.draw_post(p, comments.get(p["post_id"], []))
        if more:
            theme.button(self.feed, "Load more posts ▾", self.load_more, bg=C["blue_dark"], size=10,
                         hover_color=C["purple_dark"]).pack(pady=12)
        self.update_idletasks()
        self.canvas.yview_moveto(top)

    def load_more(self):
        self.limit += self.PAGE_SIZE
        self.reload()

    def fetch_comments(self, post_ids):
        out = {}
        if not post_ids:
            return out
        rows = db.fetch_all(
            "SELECT c.*, u.full_name FROM community_comments c JOIN user_profiles u ON u.user_id=c.user_id "
            "WHERE c.post_id IN (%s) ORDER BY c.created_at, c.comment_id" % ",".join(["%s"] * len(post_ids)),
            post_ids)
        for r in rows:
            out.setdefault(r["post_id"], []).append(r)
        return out

    # ================================================================
    # drawing one post
    # ================================================================
    def draw_post(self, p, comments):
        wrap = self.wrap_width()
        mine = p["user_id"] == self.me
        role = roles_of(p["roles"])[0]
        icon, c_light, c_dark = CATEGORIES.get(p["category"], ("📌", "#EEEEEE", "#555555"))

        box = theme.card(self.feed)
        box.pack(fill="x", pady=6, padx=(0, 12))
        tk.Frame(box, bg=c_dark, height=4).pack(fill="x")                         # category colour strip
        removed = bool(p["is_removed"])
        if removed:
            self.draw_removed_banner(box, p, wrap)
        elif self.is_admin and p["n_reports"]:
            theme.label(box, f"🚩 This post was reported {p['n_reports']} time(s) - please review it.", 9,
                        C["red"], "#FBE3E3", True).pack(fill="x")

        # ----- author line -----
        head = tk.Frame(box, bg=C["white"])
        head.pack(fill="x", padx=14, pady=(10, 4))
        avatar(head, p["author_photo"], 44, role, C["white"]).pack(side="left")
        who = tk.Frame(head, bg=C["white"])
        who.pack(side="left", padx=10)
        theme.label(who, p["full_name"], 11, C["dark"], C["white"], True).pack(anchor="w")
        meta = when(p["created_at"]) + ("  •  edited" if p["edited_at"] else "")
        line = tk.Frame(who, bg=C["white"])
        line.pack(anchor="w")
        light, dark, role_name = ROLE_STYLE[role]
        tk.Label(line, text=role_name, bg=blend(light, dark, 0.22), fg=ink(blend(light, dark, 0.22)),
                 font=(theme.FONT, 7, "bold"), padx=5).pack(side="left")
        theme.label(line, "  " + meta, 8, C["muted"], C["white"]).pack(side="left")
        tk.Label(head, text=f" {icon} {p['category']} ", bg=c_light, fg=c_dark,
                 font=(theme.FONT, 9, "bold"), padx=6, pady=2).pack(side="right")

        # ----- content -----
        theme.label(box, p["title"], 13, C["dark"], C["white"], True, wraplength=wrap, justify="left"
                    ).pack(anchor="w", padx=14, pady=(4, 2))
        theme.label(box, p["body"], 10, C["text"], C["white"], wraplength=wrap, justify="left"
                    ).pack(anchor="w", padx=14, pady=(0, 4))
        extras = []
        if p["price"]:
            extras.append("💰 " + p["price"])
        if p["location"]:
            extras.append("📍 " + p["location"])
        if extras:
            theme.label(box, "    ".join(extras), 10, C["green_dark"], C["white"], True
                        ).pack(anchor="w", padx=14, pady=(0, 4))
        img = load_photo(p["photo_path"], wrap, 340)
        if img:
            lbl = tk.Label(box, image=img, bg=C["white"], bd=0)
            lbl.image = img
            lbl.pack(anchor="w", padx=14, pady=(2, 6))
        elif p["photo_path"]:
            theme.label(box, "🖼 (photo cannot be shown - run: pip install pillow)", 8, C["muted"], C["white"]
                        ).pack(anchor="w", padx=14)
        if self.tab == "profile" and p["shared"] and not mine:
            theme.label(box, "🔗 Shared by you", 8, C["purple_dark"], C["white"], True).pack(anchor="w", padx=14)

        # ----- action bar: react, comment, save, share, message, edit, delete -----
        tk.Frame(box, bg=C["border"], height=1).pack(fill="x", padx=14, pady=(6, 0))
        bar = tk.Frame(box, bg=C["white"])
        bar.pack(fill="x", padx=10, pady=8)
        pid = p["post_id"]
        if removed:                                 # a taken-down post: only Appeal / Put back
            self.draw_removed_bar(bar, p)
            return
        up_on, down_on = p["my_react"] == "up", p["my_react"] == "down"
        small_button(bar, f"👍 {p['ups']}", lambda: self.react(pid, "up"),
                     C["green"] if up_on else "#F1F5EC", C["white"] if up_on else C["text"], up_on
                     ).pack(side="left", padx=2)
        small_button(bar, f"👎 {p['downs']}", lambda: self.react(pid, "down"),
                     C["red"] if down_on else "#F1F5EC", C["white"] if down_on else C["text"], down_on
                     ).pack(side="left", padx=2)
        opened = pid in self.open_comments
        small_button(bar, f"💬 {p['n_comments']} Comment{'s' if p['n_comments'] != 1 else ''}",
                     lambda: self.toggle_comments(pid), C["blue"] if opened else "#F1F5EC", C["dark"]
                     ).pack(side="left", padx=2)
        small_button(bar, "🔖 Saved" if p["saved"] else "🔖 Save", lambda: self.toggle_save(pid),
                     C["yellow"] if p["saved"] else "#F1F5EC", C["dark"], bool(p["saved"])).pack(side="left", padx=2)
        small_button(bar, "🔗 Shared" if p["shared"] else "🔗 Share to profile", lambda: self.toggle_share(pid),
                     C["purple"] if p["shared"] else "#F1F5EC", C["dark"], bool(p["shared"])).pack(side="left", padx=2)
        if not mine:
            small_button(bar, "✉ Message", lambda: self.app.navigate("Messages", to_user=p["user_id"]),
                         C["mint"], C["green_dark"], True).pack(side="left", padx=2)
        if mine:                                    # only the owner can edit / delete their own post
            small_button(bar, "✏ Edit", lambda: self.open_editor(p), "#F1F5EC", C["dark"]).pack(side="right", padx=2)
            small_button(bar, "🗑 Delete", lambda: self.delete_post(p), "#FBE3E3", C["red"]).pack(side="right", padx=2)
        elif self.is_admin:                         # administrators take posts down, with a reason
            small_button(bar, "🗑 Remove post", lambda: self.decision_dialog(p, "takedown"), "#FBE3E3", C["red"], True
                         ).pack(side="right", padx=2)
            if p["n_reports"]:
                small_button(bar, f"🚩 Review reports ({p['n_reports']})", lambda: self.show_reports(p), "#FFE8D6",
                             "#B66A31", True).pack(side="right", padx=2)
        elif p["my_reported"]:
            theme.label(bar, "🚩 You reported this", 8, C["muted"], C["white"]).pack(side="right", padx=6)
        else:
            small_button(bar, "🚩 Report", lambda: self.report_post(p), "#F1F5EC", C["muted"]).pack(side="right", padx=2)

        # ----- comments -----
        if opened:
            self.draw_comments(box, pid, comments, wrap)

    def draw_comments(self, box, pid, comments, wrap):
        area = tk.Frame(box, bg="#F6FAF1")
        area.pack(fill="x", padx=14, pady=(0, 12))
        if not comments:
            theme.label(area, "No comments yet. Be the first!", 9, C["muted"], "#F6FAF1").pack(anchor="w", padx=10, pady=6)
        for c in comments:
            row = tk.Frame(area, bg="#F6FAF1")
            row.pack(fill="x", padx=10, pady=4)
            top = tk.Frame(row, bg="#F6FAF1")
            top.pack(fill="x")
            theme.label(top, c["full_name"], 9, C["dark"], "#F6FAF1", True).pack(side="left")
            note = when(c["created_at"]) + ("  (edited)" if c["edited_at"] else "")
            theme.label(top, "  " + note, 8, C["muted"], "#F6FAF1").pack(side="left")
            if c["user_id"] == self.me:
                self.link(top, "🗑 Remove", lambda cid=c["comment_id"]: self.delete_comment(cid), C["red"])
                self.link(top, "✏ Edit", lambda cc=c: self.edit_comment(cc), C["blue_dark"])
            elif self.is_admin:
                self.link(top, "🗑 Remove", lambda cid=c["comment_id"]: self.delete_comment(cid), C["red"])
            theme.label(row, c["body"], 10, C["text"], "#F6FAF1", wraplength=wrap - 40, justify="left"
                        ).pack(anchor="w")
        add = tk.Frame(area, bg="#F6FAF1")
        add.pack(fill="x", padx=10, pady=(4, 10))
        var = tk.StringVar()
        entry = tk.Entry(add, textvariable=var, font=(theme.FONT, 10), relief="solid", bd=1)
        entry.pack(side="left", fill="x", expand=True, ipady=5)
        entry.bind("<Return>", lambda e: self.add_comment(pid, var))
        emoji_picker.attach(add, entry, bg="#F6FAF1").pack(side="left", padx=(4, 0))
        theme.button(add, "Post", lambda: self.add_comment(pid, var), size=9, pady=5).pack(side="left", padx=(6, 0))

    @staticmethod
    def link(parent, text, command, colour):
        """Tiny clickable text (used for Edit / Remove on a comment)."""
        lbl = tk.Label(parent, text=text, fg=colour, bg="#F6FAF1", font=(theme.FONT, 8, "bold"), cursor="hand2")
        lbl.pack(side="right", padx=4)
        lbl.bind("<Button-1>", lambda e: command())

    # ================================================================
    # actions: reactions, comments, save, share
    # ================================================================
    def react(self, pid, kind):
        """👍/👎. Same button again = remove my reaction; other button = change it."""
        cur = db.fetch_one("SELECT reaction FROM community_reactions WHERE post_id=%s AND user_id=%s",
                           (pid, self.me))
        if cur and cur["reaction"] == kind:
            db.execute("DELETE FROM community_reactions WHERE post_id=%s AND user_id=%s", (pid, self.me))
        else:
            db.execute("INSERT INTO community_reactions (post_id, user_id, reaction) VALUES (%s,%s,%s) "
                       "ON DUPLICATE KEY UPDATE reaction=VALUES(reaction), reacted_at=NOW()", (pid, self.me, kind))
        self.reload()

    def toggle_comments(self, pid):
        self.open_comments.symmetric_difference_update({pid})
        self.reload()

    def add_comment(self, pid, var):
        text = var.get().strip()
        if not text:
            return
        db.execute("INSERT INTO community_comments (post_id, user_id, body) VALUES (%s,%s,%s)",
                   (pid, self.me, text))
        self.open_comments.add(pid)
        self.reload()

    def edit_comment(self, c):
        text = simpledialog.askstring("Edit comment", "Change your comment:", initialvalue=c["body"], parent=self)
        if text is None or not text.strip():
            return
        db.execute("UPDATE community_comments SET body=%s, edited_at=NOW() WHERE comment_id=%s AND user_id=%s",
                   (text.strip(), c["comment_id"], self.me))
        self.reload()

    def delete_comment(self, cid):
        if not messagebox.askyesno("Remove comment", "Remove this comment?"):
            return
        if self.is_admin:
            db.execute("DELETE FROM community_comments WHERE comment_id=%s", (cid,))
        else:
            db.execute("DELETE FROM community_comments WHERE comment_id=%s AND user_id=%s", (cid, self.me))
        self.reload()

    def toggle_save(self, pid):
        if db.fetch_one("SELECT 1 AS x FROM community_saves WHERE post_id=%s AND user_id=%s", (pid, self.me)):
            db.execute("DELETE FROM community_saves WHERE post_id=%s AND user_id=%s", (pid, self.me))
        else:
            db.execute("INSERT IGNORE INTO community_saves (post_id, user_id) VALUES (%s,%s)", (pid, self.me))
        self.reload()

    def toggle_share(self, pid):
        if db.fetch_one("SELECT 1 AS x FROM community_shares WHERE post_id=%s AND user_id=%s", (pid, self.me)):
            db.execute("DELETE FROM community_shares WHERE post_id=%s AND user_id=%s", (pid, self.me))
        else:
            db.execute("INSERT IGNORE INTO community_shares (post_id, user_id) VALUES (%s,%s)", (pid, self.me))
            messagebox.showinfo("Shared", "This post is now shared on your profile.\n"
                                          "Find it under the 'My Profile' tab and on the My Profile page.")
        self.reload()

    def delete_post(self, p):
        """The OWNER deletes their own post (nobody else can; admins use Take down)."""
        if p["user_id"] != self.me:
            return
        if not messagebox.askyesno("Delete post", f"Delete “{p['title']}” permanently?\n"
                                                  "Its comments and reactions are deleted too."):
            return
        db.execute("DELETE FROM community_posts WHERE post_id=%s AND user_id=%s", (p["post_id"], self.me))
        remove_photo_file(p["photo_path"])
        self.open_comments.discard(p["post_id"])
        self.reload()

    # ================================================================
    # reporting and moderation
    # ================================================================
    def report_post(self, p):
        """Any user: report a post to the administrators."""
        win = tk.Toplevel(self)
        win.title("Report post")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("420x330")
        theme.label(win, "🚩 Report this post", 14, C["red"], C["white"], True).pack(anchor="w", padx=22, pady=(16, 0))
        theme.label(win, f"“{p['title']}”", 9, C["muted"], C["white"], wraplength=370, justify="left"
                    ).pack(anchor="w", padx=22)
        form = tk.Frame(win, bg=C["white"])
        form.pack(fill="x", padx=22)
        reason = tk.StringVar(value=REPORT_REASONS[0])
        details = tk.StringVar()
        theme.field(form, "Why are you reporting it?")
        ttk.Combobox(form, textvariable=reason, state="readonly", values=REPORT_REASONS).pack(fill="x")
        theme.field(form, "More details (optional)")
        theme.entry(form, details).pack(fill="x", ipady=5)

        def send():
            db.execute("INSERT INTO community_reports (post_id, reporter_id, reason, details) VALUES (%s,%s,%s,%s) "
                       "ON DUPLICATE KEY UPDATE reason=VALUES(reason), details=VALUES(details), status='Open'",
                       (p["post_id"], self.me, reason.get(), details.get().strip()[:255] or None))
            win.destroy()
            messagebox.showinfo("Reported", "Thank you. An administrator will review this post.")
            self.reload()
        theme.button(win, "Send report", send, bg=C["red"], hover_color="#9E2F2F").pack(fill="x", padx=22, pady=18)

    def show_reports(self, p):
        """Admin: see who reported a post and why, then decide: take it down or keep it."""
        rows = db.fetch_all(
            "SELECT r.*, u.full_name FROM community_reports r JOIN user_profiles u ON u.user_id=r.reporter_id "
            "WHERE r.post_id=%s AND r.status='Open' ORDER BY r.created_at", (p["post_id"],))
        win = tk.Toplevel(self)
        win.title("Reports")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.geometry("500x460")
        bar = tk.Frame(win, bg=C["white"])
        bar.pack(side="bottom", fill="x", padx=20, pady=14)
        theme.label(win, "🚩 Reports on this post", 14, C["red"], C["white"], True).pack(anchor="w", padx=20, pady=(14, 0))
        theme.label(win, f"“{p['title']}” by {p['full_name']}", 9, C["muted"], C["white"], wraplength=450,
                    justify="left").pack(anchor="w", padx=20, pady=(0, 8))
        listing = tk.Frame(win, bg=C["white"])
        listing.pack(fill="both", expand=True, padx=20)
        if not rows:
            theme.label(listing, "No open reports.", 10, C["muted"], C["white"]).pack(pady=20)
        for r in rows[:6]:
            item = tk.Frame(listing, bg="#FFF6F0", highlightbackground=C["border"], highlightthickness=1)
            item.pack(fill="x", pady=3)
            theme.label(item, f"{r['full_name']}  -  {r['reason']}", 10, C["dark"], "#FFF6F0", True,
                        wraplength=440, justify="left").pack(anchor="w", padx=10, pady=(6, 0))
            if r["details"]:
                theme.label(item, r["details"], 9, C["text"], "#FFF6F0", wraplength=440, justify="left"
                            ).pack(anchor="w", padx=10)
            theme.label(item, when(r["created_at"]), 8, C["muted"], "#FFF6F0").pack(anchor="w", padx=10, pady=(0, 6))
        if len(rows) > 6:
            theme.label(listing, f"... and {len(rows) - 6} more report(s).", 9, C["muted"], C["white"]
                        ).pack(anchor="w")

        def decide(mode):
            win.destroy()
            self.decision_dialog(p, mode)
        theme.button(bar, "🗑 Remove post", lambda: decide("takedown"), bg=C["red"], size=9,
                     hover_color="#9E2F2F").pack(side="left")
        theme.button(bar, "✅ Keep the post", lambda: decide("keep"), bg=C["green_dark"], size=9,
                     hover_color=C["green"]).pack(side="left", padx=6)
        theme.button(bar, "Close", win.destroy, bg=C["blue_dark"], size=9,
                     hover_color=C["purple_dark"]).pack(side="right")

    def take_down_dialog(self, p):
        self.decision_dialog(p, "takedown")

    def decision_dialog(self, p, mode):
        """Admin decision about a post: mode "takedown" or "keep". The explanation is OPTIONAL for both."""
        if not self.is_admin:
            return
        if p["user_id"] == self.me:
            messagebox.showinfo("Not allowed", "Administrators cannot moderate their own posts.")
            return
        down = mode == "takedown"
        colour = C["red"] if down else C["green_dark"]
        reasons = TAKEDOWN_REASONS if down else KEEP_REASONS
        win = tk.Toplevel(self)
        win.title("Take down post" if down else "Keep post")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("500x480")
        btns = tk.Frame(win, bg=C["white"])
        btns.pack(side="bottom", fill="x", padx=22, pady=14)
        theme.label(win, "🛑 Take down this post" if down else "✅ Keep this post (it stays)", 14, colour,
                    C["white"], True).pack(anchor="w", padx=22, pady=(16, 0))
        theme.label(win, f"“{p['title']}” by {p['full_name']}", 9, C["muted"], C["white"], wraplength=450,
                    justify="left").pack(anchor="w", padx=22)
        form = tk.Frame(win, bg=C["white"])
        form.pack(fill="both", expand=True, padx=22)
        theme.field(form, "Quick explanation (optional - fills the message below)")
        pick = tk.StringVar()
        cb = ttk.Combobox(form, textvariable=pick, state="readonly", values=list(reasons))
        cb.pack(fill="x")
        theme.field(form, "Explanation (optional)")
        text = tk.Text(form, height=8, font=(theme.FONT, 10), relief="solid", bd=1, wrap="word")
        text.pack(fill="x")

        def fill(_e=None):
            text.delete("1.0", "end")
            text.insert("1.0", reasons[pick.get()])
        cb.bind("<<ComboboxSelected>>", fill)
        who = "the post owner" if down else "the post owner and the people who reported it"
        theme.label(form, f"You may leave this empty. Whatever you write is sent to {who} as a chat message "
                          "and saved in the moderation log.", 8, C["muted"], C["white"], wraplength=450,
                    justify="left").pack(anchor="w", pady=(6, 0))

        def go():
            note = text.get("1.0", "end").strip()
            question = ("Take this post down and notify the owner?" if down
                        else "Keep this post and tell the reporters?")
            if not messagebox.askyesno("Confirm", question, parent=win):
                return
            win.destroy()
            if down:
                self.take_down(p, note)
            else:
                self.keep_post(p, note)
        theme.button(btns, "Take down and notify" if down else "Keep post and notify", go, bg=colour, size=10,
                     hover_color="#9E2F2F" if down else C["green"]).pack(side="right")
        theme.button(btns, "Cancel", win.destroy, bg=C["muted"], size=10, hover_color=C["dark"]).pack(side="right", padx=6)

    # ---------------------------------------------------------------
    # the decisions (each one is logged and messaged)
    # ---------------------------------------------------------------
    def _reporters(self, post_id):
        return [r["reporter_id"] for r in db.fetch_all(
            "SELECT reporter_id FROM community_reports WHERE post_id=%s AND status='Open'", (post_id,))]

    def _log(self, p, action, note):
        return db.execute(
            "INSERT INTO community_mod_log (post_id, post_title, category, owner_id, admin_id, action, reason) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (p["post_id"], p["title"], p["category"], p["user_id"], self.me, action, (note or "").strip() or None))

    def _after_decision(self, message):
        self.open_comments.clear()
        self.only_post = None
        self.paint_tabs()
        self.reload()
        self.refresh_notifications()
        messagebox.showinfo("Done", message)

    def take_down(self, p, note):
        """TAKE DOWN: hide the post (it is NOT deleted), log it, tell the owner and the reporters."""
        reporters = self._reporters(p["post_id"])
        self._log(p, "Take down", note)
        db.execute("UPDATE community_posts SET is_removed=1, removed_at=NOW() WHERE post_id=%s", (p["post_id"],))
        db.execute("UPDATE community_reports SET status='Removed' WHERE post_id=%s AND status='Open'", (p["post_id"],))
        why = f"Explanation: {note}" if note else "No explanation was added by the administrator."
        send_message(self.me, p["user_id"],
                     f"⚠ Your Community post “{p['title']}” ({p['category']}) was taken down by an administrator.\n"
                     f"{why}\n"
                     "If you think this was a mistake, you can APPEAL: open Community → My Profile, find the post "
                     "and press “Appeal this decision”. You can add details and evidence, and an administrator "
                     "will review it.")
        for uid in reporters:
            send_message(self.me, uid, f"✅ Thank you for your report about “{p['title']}”. "
                                       "An administrator reviewed it and took the post down.")
        self._after_decision("The post was taken down and the owner was notified.")

    def keep_post(self, p, note):
        """KEEP: the post stays. The open reports are closed and the reporters (and owner) are told."""
        reporters = self._reporters(p["post_id"])
        self._log(p, "Keep", note)
        db.execute("UPDATE community_reports SET status='Kept' WHERE post_id=%s AND status='Open'", (p["post_id"],))
        why = f"\nExplanation: {note}" if note else ""
        for uid in reporters:
            send_message(self.me, uid, f"ℹ Thank you for your report about “{p['title']}”. An administrator "
                                       f"reviewed it and decided that the post stays.{why}")
        send_message(self.me, p["user_id"], f"ℹ Your Community post “{p['title']}” was reported. An administrator "
                                            f"reviewed it and decided that it stays.{why}")
        self._after_decision("The post stays. The reports were closed and the people involved were told.")

    def restore_post(self, p, note=None, appeal_id=None):
        """PUT BACK (one click): the post returns, the appeal is marked, the owner gets an apology."""
        db.execute("UPDATE community_posts SET is_removed=0, removed_at=NULL WHERE post_id=%s", (p["post_id"],))
        self._log(p, "Restore", note)
        db.execute("UPDATE community_appeals SET status='Restored', admin_id=%s, admin_note=%s, decided_at=NOW() "
                   "WHERE post_id=%s AND status='Pending'", (self.me, (note or "").strip() or None, p["post_id"]))
        extra = f"\n\nNote from the administrator: {note}" if note else ""
        send_message(self.me, p["user_id"],
                     "💚 We are sorry - and thank you.\n\n"
                     f"Your Community post “{p['title']}” was taken down by mistake and we have put it back. "
                     "We apologize for the trouble this caused you.\n\n"
                     "Thank you for your understanding and for being a valued part of the Asik community."
                     + extra)
        self._after_decision("The post is back in the Community and the owner received an apology and a thank-you message.")

    def uphold_removal(self, p, appeal_id, note):
        """After reviewing an appeal: the take-down stays."""
        db.execute("UPDATE community_appeals SET status='Upheld', admin_id=%s, admin_note=%s, decided_at=NOW() "
                   "WHERE appeal_id=%s", (self.me, (note or "").strip() or None, appeal_id))
        self._log(p, "Uphold", note)
        why = f"\nExplanation: {note}" if note else ""
        send_message(self.me, p["user_id"],
                     f"📨 We carefully reviewed your appeal about “{p['title']}”. The decision to take the post "
                     f"down stays.{why}\n\nThank you for your understanding.")
        self._after_decision("The appeal was answered: the post stays removed and the owner was told.")

    # ---------------------------------------------------------------
    # a taken-down post: banner, buttons, appeal
    # ---------------------------------------------------------------
    def removal_info(self, post_id):
        log = db.fetch_one(
            "SELECT l.*, u.full_name AS admin_name FROM community_mod_log l "
            "LEFT JOIN user_profiles u ON u.user_id=l.admin_id "
            "WHERE l.post_id=%s AND l.action='Take down' ORDER BY l.log_id DESC LIMIT 1", (post_id,))
        appeal = db.fetch_one("SELECT * FROM community_appeals WHERE post_id=%s AND log_id <=> %s "
                              "ORDER BY appeal_id DESC LIMIT 1", (post_id, log["log_id"] if log else None))
        return {"log": log, "appeal": appeal}

    def draw_removed_banner(self, box, p, wrap):
        info = self.removal_info(p["post_id"])
        log = info["log"]
        reason = (log["reason"] if log and log["reason"] else "No explanation was added.")
        when_txt = when(p["removed_at"]) if p["removed_at"] else ""
        if self.is_admin:
            who = f" by {log['admin_name']}" if log and log["admin_name"] else ""
            text = f"🛑 Taken down{who} {when_txt}.  Explanation: {reason}"
        else:
            text = (f"🛑 An administrator took this post down {when_txt}. Only you and the administrators can see it."
                    f"  Explanation: {reason}")
        theme.label(box, text, 9, C["red"], "#FBE3E3", True, wraplength=wrap, justify="left"
                    ).pack(fill="x", ipady=4)

    def draw_removed_bar(self, bar, p):
        info = self.removal_info(p["post_id"])
        appeal = info["appeal"]
        if self.is_admin:
            small_button(bar, "↩ Put back", lambda: self.restore_post(p), C["mint"], C["green_dark"], True
                         ).pack(side="left", padx=2)
            if appeal:
                label = {"Pending": "📨 Read the appeal", "Upheld": "📨 Appeal (kept removed)"}.get(
                    appeal["status"], "📨 Appeal")
                small_button(bar, label, lambda: self.review_appeal_dialog(p, appeal), "#FFE8D6", "#B66A31",
                             appeal["status"] == "Pending").pack(side="left", padx=2)
            else:
                theme.label(bar, "No appeal yet.", 8, C["muted"], C["white"]).pack(side="left", padx=6)
        elif p["user_id"] == self.me:
            if appeal is None:
                small_button(bar, "📨 Appeal this decision", lambda: self.appeal_dialog(p, info["log"]), C["yellow"],
                             C["dark"], True).pack(side="left", padx=2)
            elif appeal["status"] == "Pending":
                theme.label(bar, "📨 Your appeal was sent - an administrator will review it.", 9, C["orange_dark"],
                            C["white"], True).pack(side="left", padx=6)
            else:
                note = f" Explanation: {appeal['admin_note']}" if appeal["admin_note"] else ""
                theme.label(bar, "📨 Your appeal was reviewed: the take-down stays." + note, 9, C["muted"],
                            C["white"], wraplength=self.wrap_width(), justify="left").pack(side="left", padx=6)

    def appeal_dialog(self, p, log):
        """The OWNER of a taken-down post: explain why it was a mistake and attach evidence (optional)."""
        win = tk.Toplevel(self)
        win.title("Appeal")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("520x600")
        files = []
        btns = tk.Frame(win, bg=C["white"])
        btns.pack(side="bottom", fill="x", padx=22, pady=14)
        theme.label(win, "📨 Appeal this decision", 14, C["dark"], C["white"], True).pack(anchor="w", padx=22, pady=(16, 0))
        theme.label(win, f"“{p['title']}”", 9, C["muted"], C["white"], wraplength=470, justify="left"
                    ).pack(anchor="w", padx=22)
        if log and log["reason"]:
            theme.label(win, "Reason given: " + log["reason"], 9, C["red"], C["white"], wraplength=470,
                        justify="left").pack(anchor="w", padx=22, pady=(4, 0))
        form = tk.Frame(win, bg=C["white"])
        form.pack(fill="both", expand=True, padx=22)
        theme.field(form, "Supporting details - why should this post be put back?")
        text = tk.Text(form, height=8, font=(theme.FONT, 10), relief="solid", bd=1, wrap="word")
        text.pack(fill="x")
        row = tk.Frame(form, bg=C["white"])
        row.pack(fill="x")
        emoji_picker.attach(row, text).pack(side="left")
        theme.field(form, f"Evidence (optional) - photos, screenshots or documents, up to {MAX_EVIDENCE} files")
        box = tk.Listbox(form, height=4, font=(theme.FONT, 9), relief="solid", bd=1, activestyle="none")
        box.pack(fill="x")

        def add():
            if len(files) >= MAX_EVIDENCE:
                return messagebox.showinfo("Limit", f"You can attach up to {MAX_EVIDENCE} files.", parent=win)
            picked = filedialog.askopenfilenames(
                parent=win, title="Choose evidence",
                filetypes=[("Pictures and documents", "*.png *.jpg *.jpeg *.gif *.pdf *.doc *.docx *.txt"),
                           ("All files", "*.*")])
            for path in picked:
                if len(files) >= MAX_EVIDENCE:
                    break
                if os.path.getsize(path) > MAX_EVIDENCE_MB * 1024 * 1024:
                    messagebox.showwarning("Too big", f"{os.path.basename(path)} is bigger than {MAX_EVIDENCE_MB} MB.",
                                           parent=win)
                    continue
                if path not in files:
                    files.append(path)
                    box.insert("end", os.path.basename(path))

        def drop():
            for i in reversed(box.curselection()):
                box.delete(i)
                del files[i]
        eb = tk.Frame(form, bg=C["white"])
        eb.pack(fill="x", pady=4)
        theme.button(eb, "📎 Add evidence", add, bg=C["blue_dark"], size=9, pady=3,
                     hover_color=C["purple_dark"]).pack(side="left")
        theme.button(eb, "Remove selected", drop, bg=C["muted"], size=9, pady=3, hover_color=C["dark"]
                     ).pack(side="left", padx=6)

        def send():
            details = text.get("1.0", "end").strip()
            if len(details) < 10:
                return messagebox.showwarning("Details needed", "Please explain in a few words why this post "
                                              "should be put back.", parent=win)
            appeal_id = db.execute("INSERT INTO community_appeals (log_id, post_id, user_id, details) "
                                   "VALUES (%s,%s,%s,%s)",
                                   (log["log_id"] if log else None, p["post_id"], self.me, details))
            for src in files:
                try:
                    db.execute("INSERT INTO community_appeal_files (appeal_id, file_path) VALUES (%s,%s)",
                               (appeal_id, store_evidence(src, appeal_id)))
                except OSError:
                    pass
            win.destroy()
            messagebox.showinfo("Appeal sent", "Thank you. An administrator will review your appeal and "
                                               "send you a message with the decision.")
            self.reload()
            self.refresh_notifications()
        theme.button(btns, "Send appeal", send, bg=C["green_dark"], size=10, hover_color=C["green"]).pack(side="right")
        theme.button(btns, "Cancel", win.destroy, bg=C["muted"], size=10, hover_color=C["dark"]).pack(side="right", padx=6)

    def review_appeal_dialog(self, p, appeal):
        """ADMIN: read the owner's appeal and evidence, then keep the post removed or put it back."""
        owner = db.fetch_one("SELECT full_name FROM user_profiles WHERE user_id=%s", (p["user_id"],))
        info = self.removal_info(p["post_id"])
        evidence = db.fetch_all("SELECT * FROM community_appeal_files WHERE appeal_id=%s ORDER BY file_id",
                                (appeal["appeal_id"],))
        pending = appeal["status"] == "Pending"
        win = tk.Toplevel(self)
        win.title("Appeal")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("540x620")
        btns = tk.Frame(win, bg=C["white"])
        btns.pack(side="bottom", fill="x", padx=22, pady=14)
        theme.label(win, "📨 Appeal", 14, C["dark"], C["white"], True).pack(anchor="w", padx=22, pady=(16, 0))
        theme.label(win, f"“{p['title']}” by {owner['full_name'] if owner else 'the owner'} - sent {when(appeal['created_at'])}",
                    9, C["muted"], C["white"], wraplength=490, justify="left").pack(anchor="w", padx=22)
        if info["log"] and info["log"]["reason"]:
            theme.label(win, "Reason for the take-down: " + info["log"]["reason"], 9, C["red"], C["white"],
                        wraplength=490, justify="left").pack(anchor="w", padx=22, pady=(4, 0))
        form = tk.Frame(win, bg=C["white"])
        form.pack(fill="both", expand=True, padx=22)
        theme.field(form, "What the owner says")
        theme.label(form, appeal["details"], 10, C["text"], "#F6FAF1", wraplength=480, justify="left"
                    ).pack(fill="x", ipady=6, ipadx=6)
        theme.field(form, "Evidence")
        if not evidence:
            theme.label(form, "No evidence files were attached.", 9, C["muted"], C["white"]).pack(anchor="w")
        for f in evidence:
            small_button(form, "📎 " + os.path.basename(f["file_path"]), lambda path=f["file_path"]: open_file(path),
                         C["mint"], C["green_dark"]).pack(anchor="w", pady=1)
        if pending:
            theme.field(form, "Message to the owner (optional)")
            text = tk.Text(form, height=5, font=(theme.FONT, 10), relief="solid", bd=1, wrap="word")
            text.pack(fill="x")

            def put_back():
                note = text.get("1.0", "end").strip()
                win.destroy()
                self.restore_post(p, note, appeal["appeal_id"])

            def keep_removed():
                note = text.get("1.0", "end").strip()
                win.destroy()
                self.uphold_removal(p, appeal["appeal_id"], note)
            theme.button(btns, "↩ It was a mistake - put the post back", put_back, bg=C["green_dark"], size=9,
                         hover_color=C["green"]).pack(side="left")
            theme.button(btns, "Keep it removed", keep_removed, bg=C["red"], size=9, hover_color="#9E2F2F"
                         ).pack(side="left", padx=6)
        else:
            theme.field(form, "Decision")
            theme.label(form, f"{appeal['status']}" + (f" - {appeal['admin_note']}" if appeal["admin_note"] else ""),
                        10, C["text"], C["white"], wraplength=480, justify="left").pack(anchor="w")
            theme.button(btns, "↩ Put the post back after all", lambda: (win.destroy(), self.restore_post(p)),
                         bg=C["green_dark"], size=9, hover_color=C["green"]).pack(side="left")
        theme.button(btns, "Close", win.destroy, bg=C["muted"], size=9, hover_color=C["dark"]).pack(side="right")

    # ================================================================
    # create / edit a post
    # ================================================================
    def open_editor(self, post):
        """Pop-up form for a new post (post=None) or for editing one of my posts."""
        editing = post is not None
        win = tk.Toplevel(self)
        win.title("Edit post" if editing else "New post")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.geometry("560x640")

        default_cat = {"learn": "Tip", "fun": "Entertainment", "market": "Product Ad"}.get(self.tab, "Tip")
        cat = tk.StringVar(value=post["category"] if editing else default_cat)
        title = tk.StringVar(value=post["title"] if editing else "")
        price = tk.StringVar(value=(post["price"] or "") if editing else "")
        place = tk.StringVar(value=(post["location"] or "") if editing else "")
        state = {"new_photo": None, "remove": False}

        theme.label(win, "✏ Edit your post" if editing else "➕ Share with the community", 14, C["green_dark"],
                    C["white"], True).pack(anchor="w", padx=22, pady=(16, 0))
        form = tk.Frame(win, bg=C["white"])
        form.pack(fill="both", expand=True, padx=22)
        theme.field(form, "Category")
        ttk.Combobox(form, textvariable=cat, state="readonly",
                     values=list(CATEGORIES)).pack(fill="x")
        theme.field(form, "Title")
        title_row = tk.Frame(form, bg=C["white"])
        title_row.pack(fill="x")
        title_entry = theme.entry(title_row, title)
        title_entry.pack(side="left", fill="x", expand=True, ipady=5)
        emoji_picker.attach(title_row, title_entry).pack(side="left", padx=(4, 0))
        theme.field(form, "Description (steps, tips, details...)")
        body = tk.Text(form, height=8, font=(theme.FONT, 10), relief="solid", bd=1, wrap="word")
        body.pack(fill="x")
        if editing:
            body.insert("1.0", post["body"])
        emoji_row = tk.Frame(form, bg=C["white"])
        emoji_row.pack(fill="x")
        emoji_picker.attach(emoji_row, body).pack(side="left")
        theme.label(emoji_row, "add an emoji to your description", 8, C["muted"], C["white"]).pack(side="left")
        theme.field(form, "Price (optional - for ads, e.g. ₱1,500 / day)")
        theme.entry(form, price).pack(fill="x", ipady=5)
        theme.field(form, "Location (optional)")
        theme.entry(form, place).pack(fill="x", ipady=5)

        theme.field(form, "Photo (optional)")
        prow = tk.Frame(form, bg=C["white"])
        prow.pack(fill="x")
        photo_lbl = theme.label(prow, "", 9, C["muted"], C["white"])
        existing = post["photo_path"] if editing else None

        def show_photo_text():
            if state["new_photo"]:
                photo_lbl.configure(text="New: " + os.path.basename(state["new_photo"]))
            elif existing and not state["remove"]:
                photo_lbl.configure(text="Current: " + os.path.basename(existing))
            else:
                photo_lbl.configure(text="No photo")

        def choose():
            path = filedialog.askopenfilename(
                parent=win, title="Choose a photo",
                filetypes=[("Images", "*.png *.jpg *.jpeg *.gif"), ("All files", "*.*")])
            if path:
                state["new_photo"], state["remove"] = path, False
                show_photo_text()

        def drop():
            state["new_photo"], state["remove"] = None, True
            show_photo_text()
        theme.button(prow, "📷 Choose photo", choose, bg=C["purple_dark"], size=9, pady=5,
                     hover_color=C["blue_dark"]).pack(side="left")
        theme.button(prow, "Remove photo", drop, bg=C["muted"], size=9, pady=5,
                     hover_color=C["dark"]).pack(side="left", padx=6)
        photo_lbl.pack(side="left", padx=6)
        show_photo_text()

        def save():
            t, b = title.get().strip(), body.get("1.0", "end").strip()
            if not t or not b:
                return messagebox.showwarning("Missing", "Please enter a title and a description.", parent=win)
            values = (cat.get(), t, b, price.get().strip() or None, place.get().strip() or None)
            if editing:
                path = existing
                if state["new_photo"]:
                    path = store_photo(state["new_photo"], post["post_id"])
                elif state["remove"]:
                    path = None
                if path != existing:
                    remove_photo_file(existing)
                db.execute("UPDATE community_posts SET category=%s, title=%s, body=%s, price=%s, location=%s, "
                           "photo_path=%s, edited_at=NOW() WHERE post_id=%s AND user_id=%s",
                           values + (path, post["post_id"], self.me))
            else:
                new_id = db.execute("INSERT INTO community_posts (user_id, category, title, body, price, location) "
                                    "VALUES (%s,%s,%s,%s,%s,%s)", (self.me,) + values)
                if state["new_photo"]:
                    db.execute("UPDATE community_posts SET photo_path=%s WHERE post_id=%s",
                               (store_photo(state["new_photo"], new_id), new_id))
            win.destroy()
            self.limit = max(self.limit, self.PAGE_SIZE)
            self.only_post = None
            self.paint_tabs()
            self.reload()
            if not editing:
                self.canvas.yview_moveto(0)

        btns = tk.Frame(win, bg=C["white"])
        btns.pack(fill="x", padx=22, pady=14)
        theme.button(btns, "Save changes" if editing else "Post", save, size=10).pack(side="right")
        theme.button(btns, "Cancel", win.destroy, bg=C["muted"], size=10, hover_color=C["dark"]).pack(side="right", padx=6)

    # ================================================================
    # notifications: who reacted to / commented on MY posts
    # ================================================================
    def fetch_notifications(self):
        me = self.me
        return db.fetch_all(
            "SELECT n.*, pr.full_name, po.title FROM ("
            "  SELECT r.user_id AS actor, r.post_id, r.reaction AS kind, r.reacted_at AS happened "
            "  FROM community_reactions r JOIN community_posts p ON p.post_id=r.post_id "
            "  WHERE p.user_id=%s AND r.user_id<>%s AND p.is_removed=0 "
            "  UNION ALL "
            "  SELECT c.user_id, c.post_id, 'comment', c.created_at "
            "  FROM community_comments c JOIN community_posts p ON p.post_id=c.post_id "
            "  WHERE p.user_id=%s AND c.user_id<>%s AND p.is_removed=0"
            ") n JOIN user_profiles pr ON pr.user_id=n.actor JOIN community_posts po ON po.post_id=n.post_id "
            "ORDER BY n.happened DESC LIMIT 50", (me, me, me, me))

    def seen_at(self):
        row = db.fetch_one("SELECT seen_at FROM community_seen WHERE user_id=%s", (self.me,))
        return row["seen_at"] if row else None

    @staticmethod
    def describe(n):
        verb = {"up": "👍 liked your post", "down": "👎 disliked your post",
                "comment": "💬 commented on your post"}[n["kind"]]
        return f"{n['full_name']} {verb} “{n['title']}”"

    def refresh_notifications(self):
        """The yellow/white bar at the top of the page."""
        try:
            items = self.fetch_notifications()
            seen = self.seen_at()
            unread = [n for n in items if seen is None or n["happened"] > seen]
            bg = C["yellow"] if unread else C["white"]
            theme.clear(self.notif_bar)
            self.notif_bar.configure(bg=bg)
            if unread:
                theme.label(self.notif_bar, f"🔔 {len(unread)} new", 10, C["red"], bg, True
                            ).pack(side="left", padx=(12, 8), pady=8)
                preview = "   •   ".join(self.describe(n) for n in unread[:2])
                if len(unread) > 2:
                    preview += f"   •   and {len(unread) - 2} more"
                theme.label(self.notif_bar, preview, 9, C["dark"], bg, wraplength=620, justify="left"
                            ).pack(side="left", pady=8)
            else:
                theme.label(self.notif_bar, "🔔 No new notifications - you will see here who reacted to or "
                                            "commented on your posts.", 9, C["muted"], bg
                            ).pack(side="left", padx=12, pady=8)
            if self.is_admin:
                waiting = db.fetch_one("SELECT COUNT(DISTINCT post_id) AS n FROM community_reports "
                                       "WHERE status='Open'")["n"]
                if waiting:
                    theme.button(self.notif_bar, f"🚩 {waiting} reported - review", lambda: self.set_tab("reports"),
                                 bg=C["red"], size=9, pady=3, hover_color="#9E2F2F").pack(side="right", padx=(0, 4), pady=6)
                appeals = db.fetch_one("SELECT COUNT(*) AS n FROM community_appeals WHERE status='Pending'")["n"]
                if appeals:
                    theme.button(self.notif_bar, f"📨 {appeals} appeal(s) - review", lambda: self.set_tab("removed"),
                                 bg=C["orange_dark"], size=9, pady=3, hover_color="#8F4F22").pack(side="right", padx=(0, 4), pady=6)
            else:
                gone = db.fetch_one(
                    "SELECT COUNT(*) AS n FROM community_posts p WHERE p.user_id=%s AND p.is_removed=1 "
                    "AND NOT EXISTS (SELECT 1 FROM community_appeals a WHERE a.post_id=p.post_id AND a.log_id <=> "
                    "(SELECT MAX(l.log_id) FROM community_mod_log l WHERE l.post_id=p.post_id "
                    "AND l.action='Take down'))", (self.me,))["n"]
                if gone:
                    theme.button(self.notif_bar, f"🛑 {gone} of your posts taken down - appeal",
                                 lambda: self.set_tab("profile"), bg=C["red"], size=9, pady=3,
                                 hover_color="#9E2F2F").pack(side="right", padx=(0, 4), pady=6)
            theme.button(self.notif_bar, "View all", self.open_notifications, bg=C["blue_dark"], size=9, pady=3,
                         hover_color=C["purple_dark"]).pack(side="right", padx=(0, 10), pady=6)
            if unread:
                theme.button(self.notif_bar, "Mark all read", self.mark_read, bg=C["muted"], size=9, pady=3,
                             hover_color=C["dark"]).pack(side="right", padx=4, pady=6)
        except tk.TclError:
            pass

    def mark_read(self):
        db.execute("INSERT INTO community_seen (user_id, seen_at) VALUES (%s, NOW()) "
                   "ON DUPLICATE KEY UPDATE seen_at=NOW()", (self.me,))
        self.refresh_notifications()

    def open_notifications(self):
        """Window with the full notification list (new ones highlighted). Click one to open the post."""
        items = self.fetch_notifications()
        seen = self.seen_at()
        win = tk.Toplevel(self)
        win.title("Notifications")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.geometry("560x460")
        theme.label(win, "🔔 Notifications", 14, C["green_dark"], C["white"], True).pack(anchor="w", padx=18, pady=(14, 2))
        theme.label(win, "Who reacted to or commented on your posts. Click one to open the post.", 9, C["muted"],
                    C["white"]).pack(anchor="w", padx=18, pady=(0, 8))
        holder = tk.Frame(win, bg=C["white"])
        holder.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        canvas = tk.Canvas(holder, bg=C["white"], highlightthickness=0)
        sb = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=C["white"])
        wid = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(wid, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        if not items:
            theme.label(inner, "Nothing yet.", 10, C["muted"], C["white"]).pack(pady=30)

        def open_post(pid):
            win.destroy()
            self.only_post = pid
            self.paint_tabs()
            self.reload()
            self.canvas.yview_moveto(0)
        for n in items:
            fresh = seen is None or n["happened"] > seen
            bg = C["yellow"] if fresh else C["white"]
            row = tk.Frame(inner, bg=bg, cursor="hand2", highlightbackground=C["border"], highlightthickness=1)
            row.pack(fill="x", pady=2, padx=4)
            t1 = theme.label(row, self.describe(n), 10, C["dark"], bg, True, wraplength=460, justify="left")
            t1.pack(anchor="w", padx=10, pady=(6, 0))
            t2 = theme.label(row, when(n["happened"]) + ("   •   NEW" if fresh else ""), 8, C["muted"], bg)
            t2.pack(anchor="w", padx=10, pady=(0, 6))
            for w in (row, t1, t2):
                w.bind("<Button-1>", lambda e, pid=n["post_id"]: open_post(pid))
        self.mark_read()                                  # opening the list counts as "read"

    # ================================================================
    def poll(self):
        """Every 20 seconds check for new reactions / comments."""
        try:
            self.refresh_notifications()
            self._timer = self.after(20000, self.poll)
        except tk.TclError:
            pass

    def destroy(self):
        for job in (self._timer, self._reload_job):
            if job:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        try:
            self.unbind_all("<MouseWheel>")
            theme.unbind_scroll_keys(self)
        except tk.TclError:
            pass
        super().destroy()
