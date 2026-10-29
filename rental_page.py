"""
rental_page.py  --  Equipment Rental page.

* Every equipment card shows its LOCATION (municipality, province, region)
  and its PRICE per day in Philippine peso.
* Filters: Search text + Category + Region -> Province -> Municipality.
* "Rent Equipment" asks for the number of days and the location of the
  renter's own farm where the equipment will be used.
Data comes from MySQL tables `equipment` and `equipment_rentals`.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import database as db
import language
import session
import theme
from theme import C

TINTS = [C["mint"], C["blue"], C["yellow"], C["purple"], C["pink"], C["orange"]]


class RentalPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self.category = "All Equipment"

        head = theme.page_header(self, language.t("rental.title"), language.t("rental.subtitle"))
        theme.button(head, language.t("rental.my_rentals_btn"), self.show_my_rentals,
                     bg=C["purple_dark"], size=9, hover_color=C["blue_dark"]
                     ).place(relx=1.0, rely=0.2, anchor="ne")

        # ---------- search bar (with clickable Search button) ----------
        self.search = theme.SearchBar(self, self.refresh, language.t("rental.search_placeholder"))
        self.search.pack(fill="x", padx=28, pady=(0, 8))

        # ---------- filter panel ----------
        panel = theme.card(self)
        panel.pack(fill="x", padx=28, pady=(0, 8))
        theme.label(panel, language.t("rental.filter_by_location"), 9, C["green"], C["white"], True
                    ).pack(anchor="w", padx=12, pady=(8, 0))
        self.location = theme.LocationPicker(panel, all_option=True, horizontal=True)
        self.location.pack(fill="x", padx=12, pady=(2, 4))

        bar = tk.Frame(panel, bg=C["white"])
        bar.pack(fill="x", padx=12, pady=(0, 10))
        self.cat_buttons = {}
        for cat_key, cat_value in (("rental.cat_all", "All Equipment"),
                                   ("rental.cat_heavy", "Heavy Equipment"),
                                   ("rental.cat_ict", "ICT Farming Tools")):
            b = theme.button(bar, language.t(cat_key), lambda c=cat_value: self.set_category(c),
                             bg=C["white"], fg=C["text"], size=9, hover_color=C["mint"])
            b.pack(side="left", padx=(0, 6))
            self.cat_buttons[cat_value] = b
        theme.button(bar, language.t("common.search"), self.refresh, size=9).pack(side="right")
        theme.button(bar, language.t("rental.reset_filters"), self.reset, bg=C["muted"], size=9,
                     hover_color=C["dark"]).pack(side="right", padx=6)
        self.count_lbl = theme.label(bar, "", 9, C["muted"], C["white"])
        self.count_lbl.pack(side="right", padx=12)

        self.area = theme.Scrollable(self)
        self.area.pack(fill="both", expand=True, padx=22, pady=(0, 10))
        self.set_category("All Equipment")

    # ---------------- filters ----------------
    def set_category(self, cat):
        self.category = cat
        for name, b in self.cat_buttons.items():
            b.configure(bg=C["green"] if name == cat else C["white"],
                        fg=C["white"] if name == cat else C["text"])
        self.refresh()

    def reset(self):
        self.location.reset()
        self.search.entry.delete(0, "end")
        self.search._show_placeholder()
        self.set_category("All Equipment")

    def refresh(self):
        """Build the SQL from the filters and redraw the cards."""
        sql = ("SELECT e.*, p.full_name AS owner_name FROM equipment e "
               "LEFT JOIN user_profiles p ON p.user_id=e.owner_user_id "
               "WHERE e.is_available=1")
        params = []
        if self.category != "All Equipment":
            sql += " AND e.category=%s"
            params.append(self.category)
        region, province, muni, _barangay = self.location.get()
        for column, value in (("region", region), ("province", province), ("municipality", muni)):
            if value:
                sql += f" AND e.{column}=%s"
                params.append(value)
        text = self.search.text()
        if text:
            sql += " AND (e.name LIKE %s OR e.description LIKE %s OR e.municipality LIKE %s)"
            params += [f"%{text}%"] * 3
        sql += " ORDER BY e.region, e.province, e.name"
        items = db.fetch_all(sql, params)
        self.count_lbl.configure(text=f"{len(items)} {language.t('rental.result_count')}")

        inner = self.area.inner
        theme.clear(inner)
        if not items:
            theme.label(inner, language.t("rental.no_results"), 12, C["muted"]).pack(pady=40)
            return
        for col in range(3):
            inner.columnconfigure(col, weight=1, uniform="equip")
        for i, it in enumerate(items):
            r, c = divmod(i, 3)
            self.draw_card(inner, it, TINTS[i % len(TINTS)]).grid(row=r, column=c, sticky="nsew",
                                                                   padx=5, pady=6)

    def draw_card(self, parent, it, tint):
        """One equipment card."""
        box = theme.card(parent)
        art = tk.Frame(box, bg=tint, height=80)
        art.pack(fill="x", padx=9, pady=(9, 0))
        art.pack_propagate(False)
        theme.label(art, it["icon"], 36, C["dark"], tint).place(relx=.5, rely=.5, anchor="center")
        accent = C["green"] if it["category"] == "Heavy Equipment" else C["purple_dark"]
        theme.label(box, it["category"].upper(), 8, accent, C["white"], True
                    ).pack(anchor="w", padx=12, pady=(8, 2))
        theme.label(box, it["name"], 12, C["dark"], C["white"], True, wraplength=230, justify="left"
                    ).pack(anchor="w", padx=12)
        theme.label(box, it["description"] or "", 9, C["muted"], C["white"], wraplength=230,
                    justify="left").pack(anchor="w", padx=12, pady=(2, 4))
        # ----- location -----
        theme.label(box, f"📍 {it['municipality']}, {it['province']}", 9, C["text"], C["white"], True,
                    wraplength=230, justify="left").pack(anchor="w", padx=12)
        theme.label(box, it["region"], 8, C["muted"], C["white"], wraplength=230, justify="left"
                    ).pack(anchor="w", padx=12)
        owner = it["owner_name"] or language.t("rental.asik_partner")
        theme.label(box, f"{language.t('rental.owner')}: {owner}", 8, C["muted"], C["white"]
                    ).pack(anchor="w", padx=12, pady=(2, 0))
        # ----- price -----
        theme.label(box, f"{theme.peso(it['price_per_day'])} {language.t('rental.per_day')}",
                    13, C["green"], C["white"], True).pack(anchor="w", padx=12, pady=(4, 6))
        row = tk.Frame(box, bg=C["white"])
        row.pack(fill="x", padx=10, pady=(0, 10))
        theme.button(row, language.t("rental.rent_btn"), lambda e=it: self.rent(e), bg=accent,
                     size=9, hover_color=C["dark"]).pack(side="left", fill="x", expand=True)
        if it["owner_user_id"] and it["owner_user_id"] != session.user_id():
            theme.button(row, "💬",
                         lambda e=it: self.app.navigate("Messages", to_user=e["owner_user_id"]),
                         bg=C["blue_dark"], size=9, hover_color=C["purple_dark"]
                         ).pack(side="left", padx=(6, 0))
        return box

    # ---------------- renting ----------------
    def rent(self, it):
        """Pop-up: choose days and the farm location where it will be used."""
        win = tk.Toplevel(self)
        win.title(language.t("rental.reserve_title"))
        win.geometry("460x640")
        win.configure(bg=C["white"])
        win.transient(self.winfo_toplevel())
        win.grab_set()

        theme.label(win, it["icon"], 36, C["green"], C["white"]).pack(pady=(14, 0))
        theme.label(win, it["name"], 15, C["dark"], C["white"], True).pack()
        theme.label(win, f"📍 {it['municipality']}, {it['province']}, {it['region']}", 9,
                    C["muted"], C["white"], wraplength=400).pack(pady=3)
        price = float(it["price_per_day"])
        theme.label(win, f"{theme.peso(price)} {language.t('rental.per_day')}", 14,
                    C["green"], C["white"], True).pack(pady=4)

        body = tk.Frame(win, bg=C["white"])
        body.pack(fill="x", padx=30)
        theme.field(body, language.t("rental.duration_days"))
        days = tk.StringVar(value="1")
        tk.Spinbox(body, from_=1, to=365, textvariable=days, font=(theme.FONT, 12), width=8,
                   justify="center").pack(anchor="w")
        total = theme.label(body, f"{language.t('rental.estimated_total')}: {theme.peso(price)}",
                            12, C["purple_dark"], C["white"], True)
        total.pack(anchor="w", pady=6)

        def recalc(*_):
            try:
                n = int(days.get())
                if n > 0:
                    total.configure(
                        text=f"{language.t('rental.estimated_total')}: {theme.peso(price * n)}")
            except ValueError:
                pass
        days.trace_add("write", recalc)

        theme.label(body, language.t("rental.farm_where"), 8, C["dark"], C["white"], True
                    ).pack(anchor="w", pady=(8, 2))
        picker = theme.LocationPicker(body, all_option=False)
        picker.pack(fill="x")
        me = db.fetch_one(
            "SELECT region, province, municipality FROM user_profiles WHERE user_id=%s",
            (session.user_id(),))
        if me and me["region"]:
            picker.set(me["region"], me["province"], me["municipality"])
        theme.field(body, language.t("rental.farm_street"))
        street = theme.entry(body)
        street.pack(fill="x", ipady=5)

        def confirm():
            try:
                n = int(days.get())
                if not 1 <= n <= 365:
                    raise ValueError
            except ValueError:
                return messagebox.showerror(language.t("rental.invalid_title"),
                                            language.t("rental.invalid_days"), parent=win)
            region, province, muni, _barangay = picker.get()
            if not (region and province and muni):
                return messagebox.showwarning(language.t("rental.farm_loc_title"),
                                              language.t("rental.farm_loc_msg"), parent=win)
            farm = ", ".join(x for x in (street.get().strip(), muni, province, region) if x)
            db.execute(
                "INSERT INTO equipment_rentals (equipment_id, renter_id, days, total_price, farm_location) "
                "VALUES (%s,%s,%s,%s,%s)",
                (it["equipment_id"], session.user_id(), n, price * n, farm))
            win.destroy()
            messagebox.showinfo(
                language.t("rental.reserved_title"),
                f"{it['name']}\n{n} {language.t('rental.day_word')}\n"
                f"{language.t('rental.estimated_total')}: {theme.peso(price * n)}\n"
                f"{language.t('rental.farm_word')}: {farm}\n\n"
                + language.t("rental.reserved_note"))

        theme.button(win, language.t("rental.confirm_btn"), confirm
                     ).pack(fill="x", padx=30, pady=16)

    def show_my_rentals(self):
        """Pop-up table of this user's reservations with a Cancel button."""
        win = tk.Toplevel(self)
        win.title(language.t("rental.my_rentals_btn"))
        win.geometry("900x430")
        win.configure(bg=C["bg"])
        theme.label(win, "📋  " + language.t("rental.my_rentals_btn"), 18, C["dark"], C["bg"], True
                    ).pack(anchor="w", padx=20, pady=14)
        cols = ("id", "name", "days", "total", "farm", "status")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for col, title_key, w in (("id", "rental.col_id", 40),
                                  ("name", "rental.col_equipment", 170),
                                  ("days", "rental.col_days", 50),
                                  ("total", "rental.col_total", 100),
                                  ("farm", "rental.col_farm", 380),
                                  ("status", "rental.col_status", 90)):
            tree.heading(col, text=language.t(title_key))
            tree.column(col, width=w, anchor="w")
        tree.pack(fill="both", expand=True, padx=20)

        def load():
            tree.delete(*tree.get_children())
            for r in db.fetch_all(
                    "SELECT r.*, e.name FROM equipment_rentals r "
                    "JOIN equipment e ON e.equipment_id=r.equipment_id "
                    "WHERE r.renter_id=%s ORDER BY r.rental_id DESC", (session.user_id(),)):
                tree.insert("", "end", values=(
                    r["rental_id"], r["name"], r["days"],
                    theme.peso(r["total_price"]), r["farm_location"], r["status"]))
        load()

        def cancel():
            sel = tree.selection()
            if not sel:
                return messagebox.showwarning(language.t("rental.select_title"),
                                              language.t("rental.select_res_msg"), parent=win)
            rid = tree.item(sel[0])["values"][0]
            if messagebox.askyesno(language.t("rental.cancel_title"),
                                   language.t("rental.cancel_msg"), parent=win):
                db.execute(
                    "UPDATE equipment_rentals SET status='Cancelled' "
                    "WHERE rental_id=%s AND renter_id=%s",
                    (rid, session.user_id()))
                load()
        bar = tk.Frame(win, bg=C["bg"])
        bar.pack(fill="x", padx=20, pady=12)
        theme.button(bar, language.t("rental.cancel_selected"), cancel, bg=C["red"], size=9,
                     hover_color="#8F3030").pack(side="left")
        theme.button(bar, language.t("common.close"), win.destroy, bg=C["dark"], size=9
                     ).pack(side="right")