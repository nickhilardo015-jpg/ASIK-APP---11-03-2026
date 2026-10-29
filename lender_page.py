"""
lender_page.py  --  "Lend My Equipment" page for rental owners (lenders).

A lender can:
  * ADD equipment they want to rent out (name, category, price, location)
  * EDIT / DELETE their listings (select a row, change the form, press Update)
  * switch a listing Available / Unavailable
  * see the reservations other farmers made on their equipment
Data: MySQL tables `equipment` and `equipment_rentals`.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import database as db
import session
import theme
from theme import C

ICONS = ["🚜", "⚒", "🌾", "⚙", "🌱", "🌽", "🛸", "🚁", "📡", "🌦", "📷", "🛰", "💧", "🔬"]


class LenderPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.selected_id = None          # equipment being edited (None = adding new)
        theme.page_header(self, "Lend My Equipment 🤝",
                          "List your equipment so other farmers can rent it. Prices are per day in Philippine peso.",
                          C["green_dark"])

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=(0, 14))

        # ---------------- left: the form ----------------
        form_card = theme.card(body)
        form_card.pack(side="left", fill="y", padx=(0, 12))
        form_card.configure(width=330)
        scroll = theme.Scrollable(form_card, C["white"])
        scroll.pack(fill="both", expand=True)
        f = tk.Frame(scroll.inner, bg=C["white"])
        f.pack(fill="x", padx=16, pady=10)

        self.form_title = theme.label(f, "➕ New listing", 13, C["green"], C["white"], True)
        self.form_title.pack(anchor="w")
        self.name = tk.StringVar()
        self.price = tk.StringVar()
        self.desc = tk.StringVar()
        self.cat = tk.StringVar(value="Heavy Equipment")
        self.icon = tk.StringVar(value="🚜")

        theme.field(f, "Equipment name")
        theme.entry(f, self.name).pack(fill="x", ipady=5)
        theme.field(f, "Category")
        ttk.Combobox(f, textvariable=self.cat, state="readonly",
                     values=["Heavy Equipment", "ICT Farming Tools"]).pack(fill="x")
        theme.field(f, "Icon")
        ttk.Combobox(f, textvariable=self.icon, state="readonly", values=ICONS).pack(fill="x")
        theme.field(f, "Short description")
        theme.entry(f, self.desc).pack(fill="x", ipady=5)
        theme.field(f, "Price per day (₱)")
        theme.entry(f, self.price).pack(fill="x", ipady=5)
        theme.label(f, "WHERE IS THE EQUIPMENT?", 8, C["dark"], C["white"], True).pack(anchor="w", pady=(10, 2))
        self.location = theme.LocationPicker(f, all_option=False)
        self.location.pack(fill="x")

        btns = tk.Frame(f, bg=C["white"])
        btns.pack(fill="x", pady=(10, 0))
        theme.button(btns, "Save", self.save, size=9).pack(side="left", padx=(0, 4))
        theme.button(btns, "Clear", self.clear_form, bg=C["muted"], size=9, hover_color=C["dark"]).pack(side="left")
        theme.button(btns, "Delete", self.delete, bg=C["red"], size=9, hover_color="#8F3030").pack(side="right")

        # ---------------- right: my listings + incoming reservations ----------------
        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        theme.label(right, "My equipment listings (click a row to edit)", 11, C["dark"], C["bg"], True
                    ).pack(anchor="w")
        cols = ("id", "name", "category", "price", "location", "available")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=8)
        for col, title, w in (("id", "#", 40), ("name", "Equipment", 160), ("category", "Category", 120),
                              ("price", "₱ / day", 80), ("location", "Location", 230), ("available", "Available", 70)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="x", pady=(4, 6))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        theme.button(right, "Toggle Available / Unavailable", self.toggle, bg=C["blue_dark"], size=9,
                     hover_color=C["purple_dark"]).pack(anchor="w")

        theme.label(right, "Reservations on my equipment", 11, C["dark"], C["bg"], True).pack(anchor="w", pady=(14, 0))
        cols2 = ("rid", "equipment", "renter", "days", "total", "farm", "status")
        self.rent_tree = ttk.Treeview(right, columns=cols2, show="headings", height=6)
        for col, title, w in (("rid", "#", 40), ("equipment", "Equipment", 140), ("renter", "Renter", 130),
                              ("days", "Days", 45), ("total", "Total", 90), ("farm", "Farm location", 220),
                              ("status", "Status", 80)):
            self.rent_tree.heading(col, text=title)
            self.rent_tree.column(col, width=w, anchor="w")
        self.rent_tree.pack(fill="x", pady=(4, 6))
        theme.button(right, "💬 Message Selected Renter", self.message_renter, size=9,
                     bg=C["purple_dark"], hover_color=C["blue_dark"]).pack(anchor="w")
        self.load()

    # ---------------- data ----------------
    def load(self):
        """Reload both tables from MySQL."""
        self.tree.delete(*self.tree.get_children())
        for e in db.fetch_all("SELECT * FROM equipment WHERE owner_user_id=%s ORDER BY equipment_id DESC",
                              (session.user_id(),)):
            self.tree.insert("", "end", iid=str(e["equipment_id"]), values=(
                e["equipment_id"], e["name"], e["category"], theme.peso(e["price_per_day"]),
                f"{e['municipality']}, {e['province']}", "Yes" if e["is_available"] else "No"))
        self.rent_tree.delete(*self.rent_tree.get_children())
        self.rent_rows = {}
        for r in db.fetch_all(
                "SELECT r.*, e.name, p.full_name FROM equipment_rentals r "
                "JOIN equipment e ON e.equipment_id=r.equipment_id "
                "JOIN user_profiles p ON p.user_id=r.renter_id "
                "WHERE e.owner_user_id=%s ORDER BY r.rental_id DESC", (session.user_id(),)):
            self.rent_tree.insert("", "end", iid=str(r["rental_id"]), values=(
                r["rental_id"], r["name"], r["full_name"], r["days"], theme.peso(r["total_price"]),
                r["farm_location"], r["status"]))
            self.rent_rows[str(r["rental_id"])] = r["renter_id"]

    def clear_form(self):
        """Empty the form and go back to 'new listing' mode."""
        self.selected_id = None
        self.form_title.configure(text="➕ New listing")
        for v in (self.name, self.price, self.desc):
            v.set("")
        self.location.reset()
        self.tree.selection_remove(self.tree.selection())

    def on_select(self, _e=None):
        """Load the clicked listing into the form (for editing)."""
        sel = self.tree.selection()
        if not sel:
            return
        e = db.fetch_one("SELECT * FROM equipment WHERE equipment_id=%s", (int(sel[0]),))
        self.selected_id = e["equipment_id"]
        self.form_title.configure(text=f"✏️ Editing #{self.selected_id}")
        self.name.set(e["name"])
        self.price.set(str(int(e["price_per_day"])))
        self.desc.set(e["description"] or "")
        self.cat.set(e["category"])
        self.icon.set(e["icon"])
        self.location.set(e["region"], e["province"], e["municipality"])

    def save(self):
        """Insert a new listing, or update the one being edited."""
        name = self.name.get().strip()
        region, province, muni, _barangay = self.location.get()          # ← FIXED (4 values)
        try:
            price = float(self.price.get().replace(",", ""))
            if price <= 0:
                raise ValueError
        except ValueError:
            return messagebox.showwarning("Price", "Enter a valid price in pesos.")
        if not name or not (region and province and muni):
            return messagebox.showwarning("Missing", "Enter the name and the full location.")
        args = (name, self.icon.get(), self.cat.get(), self.desc.get().strip(), price, region, province, muni)
        if self.selected_id:
            db.execute("UPDATE equipment SET name=%s, icon=%s, category=%s, description=%s, price_per_day=%s, "
                       "region=%s, province=%s, municipality=%s WHERE equipment_id=%s AND owner_user_id=%s",
                       args + (self.selected_id, session.user_id()))
        else:
            db.execute("INSERT INTO equipment (name, icon, category, description, price_per_day, region, province, "
                       "municipality, owner_user_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                       args + (session.user_id(),))
        self.clear_form()
        self.load()
        messagebox.showinfo("Saved", "Your equipment listing was saved.")

    def delete(self):
        if not self.selected_id:
            return messagebox.showwarning("Select", "Click a listing in the table first.")
        if messagebox.askyesno("Delete", "Delete this listing permanently?"):
            db.execute("DELETE FROM equipment WHERE equipment_id=%s AND owner_user_id=%s",
                       (self.selected_id, session.user_id()))
            self.clear_form()
            self.load()

    def toggle(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning("Select", "Click a listing first.")
        db.execute("UPDATE equipment SET is_available = 1 - is_available WHERE equipment_id=%s AND owner_user_id=%s",
                   (int(sel[0]), session.user_id()))
        self.load()

    def message_renter(self):
        sel = self.rent_tree.selection()
        if not sel:
            return messagebox.showwarning("Select", "Click a reservation first.")
        self.app.navigate("Messages", to_user=self.rent_rows[sel[0]])