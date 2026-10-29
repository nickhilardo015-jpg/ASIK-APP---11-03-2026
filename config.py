"""
config.py  --  Settings used by every part of Asik.

Change the MySQL values below to match YOUR MySQL server.
"""

import os

# ---------- MySQL connection settings ----------
DB_HOST = "localhost"            # where MySQL is running
DB_PORT = 3306                   # default MySQL port
DB_USER = "root"                 # your MySQL username
DB_PASSWORD = "C202500629"                 # <-- put your MySQL password here
DB_NAME = "asik_database"        # the database name required for Asik

# ---------- Application settings ----------

APP_NAME = "Asik"
APP_TAGLINE = "Smart Agriculture"

# Folder that contains this file (so images load no matter where you run it)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# The logo you sent. Save your picture in this folder with this exact name.
LOGO_FILE = os.path.join(BASE_DIR, "asik_logo.png")

# Uploaded profile photos are copied into this folder.
PHOTO_DIR = os.path.join(BASE_DIR, "profile_photos")
