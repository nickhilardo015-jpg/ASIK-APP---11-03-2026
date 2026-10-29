"""
database.py  --  All MySQL access for Asik lives in this file.

Other files never write connection code. They call the small helpers here:
    fetch_all(sql, params)  -> list of dictionaries (many rows)
    fetch_one(sql, params)  -> one dictionary or None
    execute(sql, params)    -> runs INSERT/UPDATE/DELETE, returns new id
Parameters are passed separately (%s placeholders) which protects the
database from SQL-injection.

Requires:  pip install mysql-connector-python
"""

import hashlib
import hmac
import os

import mysql.connector

import config


def get_connection(with_database=True):
    """Open a new MySQL connection using the values from config.py."""
    kwargs = dict(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        charset="utf8mb4",
    )
    if with_database:
        kwargs["database"] = config.DB_NAME
    return mysql.connector.connect(**kwargs)


def fetch_all(sql, params=()):
    """Run a SELECT and return every row as a dictionary."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def fetch_one(sql, params=()):
    """Run a SELECT and return the first row (or None)."""
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run INSERT / UPDATE / DELETE. Returns the last inserted id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        new_id = cur.lastrowid
        cur.close()
        return new_id
    finally:
        conn.close()


# ------------------------------------------------------------------
# Password security
# ------------------------------------------------------------------
def make_salt():
    """Random text added to each password before hashing."""
    return os.urandom(16).hex()


def hash_password(password, salt):
    """Turn a password into a one-way PBKDF2 hash (cannot be reversed)."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
    ).hex()


def verify_password(password, salt, stored_hash):
    """True when the typed password matches the stored hash."""
    return hmac.compare_digest(hash_password(password, salt), stored_hash)


# ------------------------------------------------------------------
# Account helpers shared by login, register, admin pages
# ------------------------------------------------------------------
def create_account(username, password, full_name, roles,
                   email="", phone="", region="", province="",
                   municipality="", address=""):
    """
    Create an account + profile + roles in one go.
    roles is a list such as ["job_seeker"] or ["employer", "lender"].
    Returns the new user_id.
    """
    salt = make_salt()
    user_id = execute(
        "INSERT INTO account_credentials (username, password_salt, password_hash) "
        "VALUES (%s, %s, %s)",
        (username, salt, hash_password(password, salt)),
    )
    execute(
        "INSERT INTO user_profiles (user_id, full_name, email, phone, region, "
        "province, municipality, address) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (user_id, full_name, email, phone, region, province, municipality, address),
    )
    for role in roles:
        execute("INSERT INTO user_roles (user_id, role) VALUES (%s, %s)",
                (user_id, role))
    return user_id


def get_roles(user_id):
    """List of role names for an account."""
    return [r["role"] for r in
            fetch_all("SELECT role FROM user_roles WHERE user_id=%s", (user_id,))]


# ------------------------------------------------------------------
# Location helpers (feed the Region > Province > Municipality > Barangay chain)
# ------------------------------------------------------------------
def get_regions():
    return [r["region"] for r in fetch_all(
        # GROUP BY (not DISTINCT) so MySQL 8 accepts ordering by the first-added region
        "SELECT region FROM ph_locations GROUP BY region ORDER BY MIN(location_id)")]


def get_provinces(region):
    return [r["province"] for r in fetch_all(
        "SELECT DISTINCT province FROM ph_locations WHERE region=%s "
        "ORDER BY province", (region,))]


def get_municipalities(province):
    return [r["municipality"] for r in fetch_all(
        "SELECT municipality FROM ph_locations WHERE province=%s "
        "ORDER BY municipality", (province,))]


def get_barangays(municipality, province=None):
    """
    Return the barangays of a municipality.

    If `province` is given, it's used to disambiguate towns that share a
    name across provinces (e.g. 'San Isidro' exists in many provinces).

    Assumes a table named `barangays` with columns:
        barangay, municipality, province
    Change those names below if your table/columns differ.
    """
    if province:
        sql = ("SELECT DISTINCT barangay FROM barangays "
               "WHERE municipality=%s AND province=%s ORDER BY barangay")
        params = (municipality, province)
    else:
        sql = ("SELECT DISTINCT barangay FROM barangays "
               "WHERE municipality=%s ORDER BY barangay")
        params = (municipality,)
    return [r["barangay"] for r in fetch_all(sql, params)]