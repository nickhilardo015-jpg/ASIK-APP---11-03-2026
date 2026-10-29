"""
session.py  --  Remembers WHO is logged in while the program runs.

Every page imports this module and reads `session.user` to know the
current user, their roles, and their active role.
"""

user = None          # dictionary: {"user_id":..., "username":..., "full_name":..., "roles":[...]}


def login(user_dict):
    """Store the logged-in user."""
    global user
    user = user_dict


def logout():
    """Forget the user (used by the Log Out button)."""
    global user
    user = None


def has_role(role):
    """True when the logged-in user holds the given role."""
    return bool(user) and role in user["roles"]


def user_id():
    """Shortcut for the current user's id."""
    return user["user_id"] if user else None
