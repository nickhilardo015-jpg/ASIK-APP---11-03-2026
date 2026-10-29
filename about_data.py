"""
about_data.py  --  everything the About page needs from MySQL.

The About page is NOT hard-coded any more: its wording, info cards, community
guidelines, announcement and developer team are stored in three tables, so an
ADMINISTRATOR can change the whole page from the page itself ("Edit this page"),
and every other user sees it view-only.

TABLES (created automatically the first time the About page opens)
  about_settings  key/value texts: hero title + text, section titles, the
                  "when rules are broken" notice, developers intro, announcement
  about_items     the info cards (kind='card') and the community guidelines
                  (kind='guideline'): icon, title, text, sort_order
  about_team      the developers / team: name, role, bio, photo, sort_order
Developer photos are copied into the `about_photos` folder.
"""

import os
import shutil
import time
import tkinter as tk

import config
import database as db
from messages_page import MessagesPage

ABOUT_DIR = getattr(config, "ABOUT_DIR", os.path.join(os.path.dirname(config.PHOTO_DIR), "about_photos"))

# ------------------------------------------------------------------
# table definitions (also written in schema.sql)
# ------------------------------------------------------------------
ABOUT_DDL = [
    """CREATE TABLE IF NOT EXISTS about_settings (
    k           VARCHAR(40) PRIMARY KEY,             -- name of the text, e.g. hero_title
    v           TEXT,                                -- the wording itself
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS about_items (
    item_id     INT AUTO_INCREMENT PRIMARY KEY,
    kind        VARCHAR(20)  NOT NULL,               -- 'card' or 'guideline'
    icon        VARCHAR(10),
    title       VARCHAR(120) NOT NULL,
    body        TEXT NOT NULL,
    sort_order  INT NOT NULL DEFAULT 0,
    INDEX idx_about_kind (kind)
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS about_team (
    member_id   INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    role        VARCHAR(120),
    bio         TEXT,
    photo_path  VARCHAR(255),
    sort_order  INT NOT NULL DEFAULT 0
) ENGINE=InnoDB""",
    """CREATE TABLE IF NOT EXISTS about_suggestions (
    suggestion_id  INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    improve        TEXT NULL,                          -- what should be improved
    feature        TEXT NULL,                          -- what feature could be added
    status         VARCHAR(10) NOT NULL DEFAULT 'New', -- New, Read or Done
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_suggestion_status (status),
    FOREIGN KEY (user_id) REFERENCES account_credentials(user_id) ON DELETE CASCADE
) ENGINE=InnoDB""",
]

# ------------------------------------------------------------------
# the starting content (what the page said before it became editable)
# ------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "hero_title": "GROW SMARTER. HARVEST BETTER.",
    "hero_text": "Helping farmers rent machinery, find farm jobs, hire workers and connect across the Philippines.",
    "guidelines_title": "📜 Community Guidelines",
    "guidelines_intro": "The Community page works because farmers look after each other. Please follow these "
                        "rules whenever you post, comment, trade or message.",
    "rules_title": "🛑 What happens when the rules are broken",
    "rules_text": "• Only the owner of a post can delete it.\n"
                  "• Reported posts, and posts that break these guidelines, can be taken down by an administrator.\n"
                  "• When a post is taken down, the owner always receives a message that explains why.\n"
                  "• Repeated or serious violations can lead to the account being disabled.\n"
                  "• Think we made a mistake? Reply to the administrator's message.",
    "dev_title": "👩‍💻 Meet the Developers",
    "dev_intro": "The people who designed and built Asik.",
    "announcement_title": "",
    "announcement_body": "",
    "announcement_at": "",
}

DEFAULT_CARDS = [
    ("🌱", "Our Mission", "Make modern agricultural machinery, farm jobs and smart technology easier to "
                          "discover and access."),
    ("🚜", "Equipment Rental", "Rent tractors, harvesters, drones and sensors in every region, or lend your own "
                               "equipment to other farmers."),
    ("📢", "Hiring Now!", "Farm jobs from laborers to agronomists, with salaries in pesos, and a portal where "
                          "employers hire and interview applicants."),
    ("🌾", "Community", "Learn farming tips and procedures, share your own, have fun, and trade products, "
                        "rentals and supplies with other farmers."),
    ("🤝", "Our Vision", "Support efficient, informed and sustainable farming through responsible use of "
                         "technology and a connected community."),
]

DEFAULT_GUIDELINES = [
    ("🤝", "Be respectful",
     "Treat every farmer, worker, employer and lender with courtesy. No harassment, insults, hate speech, "
     "threats or bullying - in posts, comments or messages."),
    ("🌾", "Share honest farming advice",
     "Post tips and procedures you have really tried, and say when something is only your own experience. "
     "Do not spread false or misleading information. For pesticides, fertilizer and animal medicine, always "
     "follow the product label and wear protective gear."),
    ("📂", "Post in the right place",
     "Use the correct category: Tip, Technique, Procedure, Entertainment, Product Ad, Rental Ad, Vacancy or "
     "Supplies / Wanted. Do not spam, repeat the same post again and again, or advertise in the Learn and "
     "Fun tabs."),
    ("🛒", "Trade honestly",
     "Ads must show a true price in pesos (₱) and a real location. Vacancies must be genuine and fairly paid. "
     "Never ask for money before the item, job or rental is confirmed, and agree on details through Messages. "
     "Meet in safe, public places."),
    ("🔒", "Protect privacy",
     "Do not post other people's phone numbers, addresses, ID or photos without their permission. Share your "
     "own contact details only when you want to be contacted."),
    ("📷", "Photos and content",
     "Upload only photos you took or are allowed to use. No offensive, violent or sexual content, and nothing "
     "illegal - such as banned pesticides, stolen equipment or protected wildlife."),
    ("👍", "React and comment fairly",
     "Use 👍 and 👎 honestly, not to attack someone or to pile on. Keep comments helpful. You can edit or "
     "remove your own comments and reactions at any time."),
    ("🚩", "Report problems",
     "See spam, a scam, false information or something inappropriate? Press 🚩 Report on the post. An "
     "administrator will review it."),
]

# placeholders - the administrator replaces these with the real team
DEFAULT_TEAM = [
    ("Developer Name", "Lead Developer", "Designed the system and wrote the code. Edit this text on the About page."),
    ("Team Member", "Database & Backend", "Built the MySQL database. Edit this text on the About page."),
    ("Team Member", "UI / UX Designer", "Designed the look of Asik. Edit this text on the About page."),
]

_ready = False


def ensure_tables():
    """Create the About tables once per run and fill them with the starting content the first time."""
    global _ready
    if _ready:
        return
    for ddl in ABOUT_DDL:
        db.execute(ddl)
    if not db.fetch_one("SELECT COUNT(*) AS n FROM about_settings")["n"]:
        for key, value in DEFAULT_SETTINGS.items():
            db.execute("INSERT INTO about_settings (k, v) VALUES (%s,%s)", (key, value))
        for n, (icon, title, body) in enumerate(DEFAULT_CARDS):
            db.execute("INSERT INTO about_items (kind, icon, title, body, sort_order) VALUES ('card',%s,%s,%s,%s)",
                       (icon, title, body, n))
        for n, (icon, title, body) in enumerate(DEFAULT_GUIDELINES):
            db.execute("INSERT INTO about_items (kind, icon, title, body, sort_order) "
                       "VALUES ('guideline',%s,%s,%s,%s)", (icon, title, body, n))
        for n, (name, role, bio) in enumerate(DEFAULT_TEAM):
            db.execute("INSERT INTO about_team (name, role, bio, sort_order) VALUES (%s,%s,%s,%s)",
                       (name, role, bio, n))
    _ready = True


def get_settings():
    """All the page texts as a dict (missing keys fall back to the defaults)."""
    data = dict(DEFAULT_SETTINGS)
    for row in db.fetch_all("SELECT k, v FROM about_settings"):
        data[row["k"]] = row["v"] or ""
    return data


def set_setting(key, value):
    db.execute("INSERT INTO about_settings (k, v) VALUES (%s,%s) ON DUPLICATE KEY UPDATE v=VALUES(v)",
               (key, value))


# ------------------------------------------------------------------
# developer photos
# ------------------------------------------------------------------
def store_photo(src):
    """Copy a chosen picture into about_photos/ and return the new path."""
    os.makedirs(ABOUT_DIR, exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    dest = os.path.join(ABOUT_DIR, "member_%d%s" % (int(time.time() * 1000), ext))
    shutil.copyfile(src, dest)
    return dest


def remove_photo_file(path):
    """Delete a picture, but only our own copy inside about_photos/."""
    try:
        if path and os.path.abspath(os.path.dirname(path)) == os.path.abspath(ABOUT_DIR) and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


_cache = {}


def round_photo(parent, path, size, bg):
    """Round picture with a green ring (a silhouette when there is no photo)."""
    path = path if path and os.path.exists(path) else None
    try:
        key = (path, os.path.getmtime(path) if path else 0, size)
        if key not in _cache:
            _cache[key] = MessagesPage._round_image(path, size, "#DDF0DA", "#2F7A4A", ring=4)
        lbl = tk.Label(parent, image=_cache[key], bg=bg, bd=0)
        lbl.image = _cache[key]
        return lbl
    except Exception:                                   # Pillow missing: plain emoji
        return tk.Label(parent, text="👤", font=("Segoe UI", max(14, size // 2)), bg=bg, fg="#6E8575")
