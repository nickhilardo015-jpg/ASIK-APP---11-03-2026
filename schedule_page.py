"""
schedule_page.py  --  Farm Schedule, built ONLY with ttk widgets.

Design (from the mock-up you sent):
  * a big month calendar with colour-coded activity chips
  * Month / Week / Day view buttons and  < >  navigation
  * "Today's Schedule" card, "Upcoming" card and a motivation card on the right
  * colour legend:  Planting, Harvest, Irrigation, Feeding, Fertilizing, Maintenance

Every widget on this page is a ttk widget (ttk.Frame, ttk.Label, ttk.Button,
ttk.Entry, ttk.Combobox, ttk.Checkbutton). Colours and fonts are applied with
ttk.Style in make_styles() below.
Data: MySQL table `farm_tasks` (each user only sees their own activities).
"""

import calendar
import tkinter as tk                       # only used for the pop-up window container and messagebox
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk

import database as db
import session

FONT = "Segoe UI"

# ---------------- colours (soft farm-green palette from the mock-up) ----------------
PAGE_BG = "#E8F2DC"      # light green behind the cards
CARD = "#FDFBEF"         # cream card
CARD_EDGE = "#DCE7C8"
OTHER_MONTH = "#F4F6E6"  # days that belong to the previous / next month
HEAD_BG = "#E3EED0"      # weekday header row
INK = "#1F4A32"          # dark green text
MUTED = "#7A8F7F"
GREEN = "#2F7A4A"
GREEN_DARK = "#1F5A38"
SELECTED = "#DDF0DA"

# Activity types:  name -> (emoji, chip background, chip text colour, legend dot colour)
TYPE_STYLE = {
    "Planting": ("🌱", "#CFEFC0", "#2E6B2E", "#4CAF50"),
    "Harvest": ("🌾", "#DDD2F7", "#5B3FA0", "#7E57C2"),
    "Irrigation": ("💧", "#CFE0FA", "#2F5DA8", "#4A7BD0"),
    "Feeding": ("🐄", "#FBE3AE", "#8A5A00", "#F2B63C"),
    "Fertilizing": ("🧪", "#F9D2D2", "#A63A3A", "#E5534B"),
    "Maintenance": ("🚜", "#C6EEDD", "#1E6B52", "#26A69A"),
    "Pest Control": ("🐛", "#F9D2D2", "#A63A3A", "#E5534B"),
    "Other": ("📌", "#E8E8DC", "#555555", "#999999"),
}
LEGEND = ["Planting", "Harvest", "Irrigation", "Feeding", "Fertilizing", "Maintenance"]
TYPES = list(TYPE_STYLE.keys())
TIMES = ["06:00 AM", "07:00 AM", "08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
         "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM", "06:00 PM"]
DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def chip_style(kind):
    """Name of the ttk label style used for an activity type."""
    return f"Chip{kind.replace(' ', '')}.TLabel" if kind in TYPE_STYLE else "ChipOther.TLabel"


def make_styles():
    """Create every ttk style used by this page (safe to call many times)."""
    s = ttk.Style()
    # ----- frames -----
    s.configure("SchBg.TFrame", background=PAGE_BG)
    s.configure("SchCard.TFrame", background=CARD, relief="solid", borderwidth=1, bordercolor=CARD_EDGE)
    s.configure("SchPlain.TFrame", background=CARD)
    s.configure("SchPill.TFrame", background=HEAD_BG)
    s.configure("SchCell.TFrame", background=CARD, relief="solid", borderwidth=1, bordercolor=CARD_EDGE)
    s.configure("SchCellOther.TFrame", background=OTHER_MONTH, relief="solid", borderwidth=1, bordercolor=CARD_EDGE)
    s.configure("SchCellSel.TFrame", background=SELECTED, relief="solid", borderwidth=2, bordercolor=GREEN)
    s.configure("SchQuote.TFrame", background="#DDEFC9", relief="solid", borderwidth=1, bordercolor=CARD_EDGE)
    # ----- labels -----
    s.configure("SchTitle.TLabel", background=CARD, foreground=GREEN_DARK, font=(FONT, 22, "bold"))
    s.configure("SchSub.TLabel", background=CARD, foreground=MUTED, font=(FONT, 10))
    s.configure("SchIcon.TLabel", background=CARD, foreground=GREEN_DARK, font=(FONT, 26))
    s.configure("SchMonth.TLabel", background=CARD, foreground=GREEN_DARK, font=(FONT, 17, "bold"))
    s.configure("SchDow.TLabel", background=HEAD_BG, foreground=INK, font=(FONT, 10, "bold"), anchor="center",
                padding=(0, 8))
    s.configure("SchDay.TLabel", background=CARD, foreground=INK, font=(FONT, 9, "bold"))
    s.configure("SchDayOther.TLabel", background=OTHER_MONTH, foreground="#B5C0B0", font=(FONT, 9))
    s.configure("SchDaySel.TLabel", background=SELECTED, foreground=GREEN_DARK, font=(FONT, 9, "bold"))
    s.configure("SchDayToday.TLabel", background=GREEN, foreground="#FFFFFF", font=(FONT, 9, "bold"),
                padding=(5, 0))
    s.configure("SchMore.TLabel", background=CARD, foreground=MUTED, font=(FONT, 8))
    s.configure("SchMoreSel.TLabel", background=SELECTED, foreground=MUTED, font=(FONT, 8))
    s.configure("SchMoreOther.TLabel", background=OTHER_MONTH, foreground=MUTED, font=(FONT, 8))
    s.configure("SchCardTitle.TLabel", background=CARD, foreground=GREEN_DARK, font=(FONT, 15, "bold"))
    s.configure("SchCardSub.TLabel", background=CARD, foreground=MUTED, font=(FONT, 10))
    s.configure("SchRowTime.TLabel", background=CARD, foreground=INK, font=(FONT, 10))
    s.configure("SchRowTitle.TLabel", background=CARD, foreground=INK, font=(FONT, 10, "bold"))
    s.configure("SchRowIcon.TLabel", background=CARD, font=(FONT, 14))
    s.configure("SchEmpty.TLabel", background=CARD, foreground=MUTED, font=(FONT, 10), justify="center")
    s.configure("SchLegend.TLabel", background=CARD, foreground=INK, font=(FONT, 9))
    s.configure("SchQuote.TLabel", background="#DDEFC9", foreground=GREEN_DARK, font=(FONT, 13, "bold"))
    s.configure("SchQuoteArt.TLabel", background="#DDEFC9", font=(FONT, 34))
    s.configure("SchForm.TLabel", background="#FFFFFF", foreground=INK, font=(FONT, 9, "bold"))
    s.configure("SchFormTitle.TLabel", background="#FFFFFF", foreground=GREEN_DARK, font=(FONT, 16, "bold"))
    s.configure("SchForm.TFrame", background="#FFFFFF")
    # one chip style per activity type
    for kind, (_icon, bg, fg, dot) in TYPE_STYLE.items():
        name = f"Chip{kind.replace(' ', '')}.TLabel"
        s.configure(name, background=bg, foreground=fg, font=(FONT, 8, "bold"), padding=(4, 2))
        s.configure(f"Dot{kind.replace(' ', '')}.TLabel", background=CARD, foreground=dot, font=(FONT, 11))
    # ----- buttons -----
    s.configure("SchPrimary.TButton", background=GREEN, foreground="#FFFFFF", font=(FONT, 10, "bold"),
                padding=(14, 8), borderwidth=0, focuscolor=GREEN)
    s.map("SchPrimary.TButton", background=[("active", GREEN_DARK), ("pressed", GREEN_DARK)])
    s.configure("SchGhost.TButton", background=HEAD_BG, foreground=INK, font=(FONT, 10, "bold"),
                padding=(14, 6), borderwidth=0, focuscolor=HEAD_BG)
    s.map("SchGhost.TButton", background=[("active", "#D3E5BB")])
    s.configure("SchOn.TButton", background=GREEN_DARK, foreground="#FFFFFF", font=(FONT, 10, "bold"),
                padding=(14, 6), borderwidth=0, focuscolor=GREEN_DARK)
    s.map("SchOn.TButton", background=[("active", GREEN_DARK)])
    s.configure("SchArrow.TButton", background=CARD, foreground=GREEN_DARK, font=(FONT, 16, "bold"),
                padding=(8, 0), borderwidth=0, focuscolor=CARD)
    s.map("SchArrow.TButton", background=[("active", HEAD_BG)])
    s.configure("SchX.TButton", background=CARD, foreground="#C44747", font=(FONT, 10, "bold"),
                padding=(4, 0), borderwidth=0, focuscolor=CARD)
    s.map("SchX.TButton", background=[("active", "#F9D2D2")])
    s.configure("SchCheck.TCheckbutton", background=CARD, focuscolor=CARD)
    s.configure("SchFlat.TButton", background=CARD, foreground=INK, font=(FONT, 10), padding=(2, 4),
                borderwidth=0, focuscolor=CARD, anchor="w")
    s.map("SchFlat.TButton", background=[("active", HEAD_BG)])


def time_key(task):
    """Sort key so '08:00 AM' < '01:00 PM'."""
    try:
        return datetime.strptime(task["task_time"] or "12:00 AM", "%I:%M %p").time()
    except ValueError:
        return datetime.min.time()


def short(text, n):
    """Cut long text so chips never stretch a calendar cell."""
    return text if len(text) <= n else text[: n - 1] + "…"


class SchedulePage(ttk.Frame):
    def __init__(self, parent, app):
        make_styles()
        super().__init__(parent, style="SchBg.TFrame")
        self.app = app
        self.selected = date.today()          # day shown in the right-hand card
        self.view = "Month"                   # Month / Week / Day
        self.view_buttons = {}
        self.cal_area = None
        self.today_card = self.upcoming_card = None

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0, minsize=330)
        self.rowconfigure(0, weight=1)

        # ================= LEFT: calendar card =================
        left = ttk.Frame(self, style="SchCard.TFrame", padding=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(24, 10), pady=(4, 18))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        head = ttk.Frame(left, style="SchPlain.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text="🗓", style="SchIcon.TLabel").grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ttk.Label(head, text="Farm Schedule", style="SchTitle.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(head, text="Plan your farming activities, keep track of your crops, and make your "
                             "farm more productive!", style="SchSub.TLabel", wraplength=520, justify="left").grid(row=1, column=1, sticky="w")
        head.columnconfigure(1, weight=1)
        ttk.Button(head, text="＋ Add Activity", style="SchPrimary.TButton", cursor="hand2",
                   command=self.add_task).grid(row=0, column=2, rowspan=2, sticky="e")

        bar = ttk.Frame(left, style="SchPlain.TFrame")
        bar.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        # the Month / Week / Day buttons are packed FIRST so a long translation never pushes them out of view
        pill = ttk.Frame(bar, style="SchPill.TFrame", padding=3)
        pill.pack(side="right")
        for name in ("Month", "Week", "Day"):
            b = ttk.Button(pill, text=name, cursor="hand2", command=lambda n=name: self.set_view(n))
            b.pack(side="left", padx=1)
            self.view_buttons[name] = b
        ttk.Button(bar, text="‹", style="SchArrow.TButton", cursor="hand2",
                   command=lambda: self.shift(-1)).pack(side="left")
        self.title_lbl = ttk.Label(bar, text="", style="SchMonth.TLabel")
        self.title_lbl.pack(side="left", padx=14)
        ttk.Button(bar, text="›", style="SchArrow.TButton", cursor="hand2",
                   command=lambda: self.shift(1)).pack(side="left")
        ttk.Button(bar, text="Today", style="SchGhost.TButton", cursor="hand2",
                   command=self.go_today).pack(side="left", padx=14)

        self.cal_area = ttk.Frame(left, style="SchPlain.TFrame")
        self.cal_area.grid(row=2, column=0, sticky="nsew")

        legend = ttk.Frame(left, style="SchPlain.TFrame")
        legend.grid(row=3, column=0, sticky="w", pady=(10, 0))
        for kind in LEGEND:
            ttk.Label(legend, text="●", style=f"Dot{kind}.TLabel").pack(side="left", padx=(0, 3))
            ttk.Label(legend, text=kind, style="SchLegend.TLabel").pack(side="left", padx=(0, 16))

        # ================= RIGHT: today / upcoming / quote =================
        right = ttk.Frame(self, style="SchBg.TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 24), pady=(4, 18))
        right.columnconfigure(0, weight=1)
        self.today_card = ttk.Frame(right, style="SchCard.TFrame", padding=14)
        self.today_card.grid(row=0, column=0, sticky="ew")
        self.upcoming_card = ttk.Frame(right, style="SchCard.TFrame", padding=14)
        self.upcoming_card.grid(row=1, column=0, sticky="ew", pady=10)
        quote = ttk.Frame(right, style="SchQuote.TFrame", padding=14)
        quote.grid(row=2, column=0, sticky="ew")
        ttk.Label(quote, text="🌱  Small steps\nmake a big harvest!", style="SchQuote.TLabel",
                  justify="left").pack(side="left")
        ttk.Label(quote, text="☀️", style="SchQuoteArt.TLabel").pack(side="right")

        self.render()

    # ======================================================================
    #  helpers
    # ======================================================================
    def clear(self, widget):
        for child in widget.winfo_children():
            child.destroy()

    def tasks_between(self, first, last):
        """Return {date: [task, ...]} for every activity between two dates."""
        rows = db.fetch_all("SELECT * FROM farm_tasks WHERE user_id=%s AND task_date BETWEEN %s AND %s",
                            (session.user_id(), first, last))
        by_day = {}
        for r in rows:
            by_day.setdefault(r["task_date"], []).append(r)
        for lst in by_day.values():
            lst.sort(key=time_key)
        return by_day

    def week_start(self, d):
        """The Sunday that starts the week containing d."""
        return d - timedelta(days=(d.weekday() + 1) % 7)

    # ======================================================================
    #  navigation
    # ======================================================================
    def set_view(self, name):
        self.view = name
        self.render()

    def go_today(self):
        self.selected = date.today()
        self.render()

    def shift(self, step):
        """Previous / next month, week or day depending on the view."""
        if self.view == "Month":
            idx = self.selected.year * 12 + self.selected.month - 1 + step
            y, m0 = divmod(idx, 12)
            m = m0 + 1
            self.selected = date(y, m, min(self.selected.day, calendar.monthrange(y, m)[1]))
        elif self.view == "Week":
            self.selected += timedelta(days=7 * step)
        else:
            self.selected += timedelta(days=step)
        self.render()

    def select(self, d):
        self.selected = d
        self.render()

    # ======================================================================
    #  drawing
    # ======================================================================
    def render(self):
        """Redraw the title, view buttons, calendar and the right-hand cards."""
        for name, b in self.view_buttons.items():
            b.configure(style="SchOn.TButton" if name == self.view else "SchGhost.TButton")
        d = self.selected
        if self.view == "Month":
            self.title_lbl.configure(text=d.strftime("%B %Y"))
        elif self.view == "Week":
            start = self.week_start(d)
            end = start + timedelta(days=6)
            self.title_lbl.configure(text=f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}")
        else:
            self.title_lbl.configure(text=d.strftime("%A, %B %d, %Y"))

        self.clear(self.cal_area)
        if self.view == "Month":
            self.draw_month()
        elif self.view == "Week":
            self.draw_week()
        else:
            self.draw_day()
        self.draw_today_card()
        self.draw_upcoming_card()

    # ---------------- month view ----------------
    def draw_month(self):
        weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(self.selected.year, self.selected.month)
        by_day = self.tasks_between(weeks[0][0], weeks[-1][-1])
        grid = ttk.Frame(self.cal_area, style="SchCard.TFrame")
        grid.pack(fill="both", expand=True)
        for c in range(7):
            grid.columnconfigure(c, weight=1, uniform="day")
            ttk.Label(grid, text=DOW[c], style="SchDow.TLabel", anchor="center"
                      ).grid(row=0, column=c, sticky="nsew")
        for r, week in enumerate(weeks, start=1):
            grid.rowconfigure(r, weight=1, uniform="week")
            for c, d in enumerate(week):
                self.month_cell(grid, d, by_day.get(d, [])).grid(row=r, column=c, sticky="nsew")

    def month_cell(self, parent, d, tasks):
        """One day box in the month grid."""
        other = d.month != self.selected.month
        sel = d == self.selected
        cell_style = "SchCellSel.TFrame" if sel else ("SchCellOther.TFrame" if other else "SchCell.TFrame")
        cell = ttk.Frame(parent, style=cell_style, padding=2, cursor="hand2")
        day_style = ("SchDayToday.TLabel" if d == date.today() else
                     "SchDaySel.TLabel" if sel else "SchDayOther.TLabel" if other else "SchDay.TLabel")
        more_style = "SchMoreSel.TLabel" if sel else ("SchMoreOther.TLabel" if other else "SchMore.TLabel")
        num = ttk.Label(cell, text=str(d.day), style=day_style)
        num.pack(anchor="w", padx=3, pady=(1, 2))
        widgets = [cell, num]
        for t in tasks[:2]:
            icon = TYPE_STYLE.get(t["task_type"], TYPE_STYLE["Other"])[0]
            mark = "✓ " if t["is_done"] else ""
            chip = ttk.Label(cell, text=f"{icon} {mark}{short(t['title'], 13)}", style=chip_style(t["task_type"]),
                             cursor="hand2")
            chip.pack(fill="x", padx=2, pady=1)
            widgets.append(chip)
        if len(tasks) > 2:
            more = ttk.Label(cell, text=f"+{len(tasks) - 2} more", style=more_style)
            more.pack(anchor="w", padx=4)
            widgets.append(more)
        for w in widgets:                                  # clicking anything in the box selects the day
            w.bind("<Button-1>", lambda e, day=d: self.select(day))
        cell.bind("<Double-Button-1>", lambda e, day=d: self.add_task(day))
        return cell

    # ---------------- week view ----------------
    def draw_week(self):
        start = self.week_start(self.selected)
        by_day = self.tasks_between(start, start + timedelta(days=6))
        grid = ttk.Frame(self.cal_area, style="SchCard.TFrame")
        grid.pack(fill="both", expand=True)
        grid.rowconfigure(1, weight=1)
        for c in range(7):
            d = start + timedelta(days=c)
            grid.columnconfigure(c, weight=1, uniform="wk")
            ttk.Label(grid, text=f"{DOW[c]} {d.day}", style="SchDow.TLabel", anchor="center"
                      ).grid(row=0, column=c, sticky="nsew")
            col = ttk.Frame(grid, style="SchCellSel.TFrame" if d == self.selected else "SchCell.TFrame",
                            padding=3, cursor="hand2")
            col.grid(row=1, column=c, sticky="nsew")
            col.bind("<Button-1>", lambda e, day=d: self.select(day))
            col.bind("<Double-Button-1>", lambda e, day=d: self.add_task(day))
            for t in by_day.get(d, []):
                icon = TYPE_STYLE.get(t["task_type"], TYPE_STYLE["Other"])[0]
                chip = ttk.Label(col, text=f"{t['task_time']}\n{icon} {short(t['title'], 14)}",
                                 style=chip_style(t["task_type"]), cursor="hand2")
                chip.pack(fill="x", padx=2, pady=2)
                chip.bind("<Button-1>", lambda e, day=d: self.select(day))

    # ---------------- day view ----------------
    def draw_day(self):
        tasks = self.tasks_between(self.selected, self.selected).get(self.selected, [])
        box = ttk.Frame(self.cal_area, style="SchCard.TFrame", padding=10)
        box.pack(fill="both", expand=True)
        if not tasks:
            ttk.Label(box, text="🌱\nNothing planned for this day.\nUse “＋ Add Activity” to plan one.",
                      style="SchEmpty.TLabel", anchor="center").pack(expand=True)
            return
        for t in tasks:
            icon = TYPE_STYLE.get(t["task_type"], TYPE_STYLE["Other"])[0]
            row = ttk.Frame(box, style="SchPlain.TFrame")
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=t["task_time"], style="SchRowTime.TLabel", width=10).pack(side="left")
            ttk.Label(row, text=f"{icon}  {t['title']}  ({t['task_type']})" + ("   ✓ done" if t["is_done"] else ""),
                      style=chip_style(t["task_type"]), padding=(10, 8)).pack(side="left", fill="x", expand=True)

    # ---------------- right-hand cards ----------------
    def draw_today_card(self):
        card = self.today_card
        self.clear(card)
        card.columnconfigure(1, weight=1)
        d = self.selected
        heading = "Today's Schedule" if d == date.today() else d.strftime("%A's Schedule")
        ttk.Label(card, text="📋", style="SchIcon.TLabel", font=(FONT, 20)).grid(row=0, column=0, rowspan=2,
                                                                              padx=(0, 10))
        ttk.Label(card, text=heading, style="SchCardTitle.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(card, text=d.strftime("%B %d, %Y (%A)"), style="SchCardSub.TLabel"
                  ).grid(row=1, column=1, sticky="w")
        ttk.Separator(card, orient="horizontal").grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)

        tasks = self.tasks_between(d, d).get(d, [])
        body = ttk.Frame(card, style="SchPlain.TFrame")
        body.grid(row=3, column=0, columnspan=2, sticky="ew")
        body.columnconfigure(1, weight=1)
        if not tasks:
            ttk.Label(body, text="🌱  No activities yet.\nUse “＋ Add Activity” to plan this day.",
                      style="SchEmpty.TLabel", anchor="center").grid(row=0, column=0, columnspan=4, pady=14)
        for i, t in enumerate(tasks):
            icon = TYPE_STYLE.get(t["task_type"], TYPE_STYLE["Other"])[0]
            var = tk.BooleanVar(value=bool(t["is_done"]))
            ttk.Checkbutton(body, variable=var, style="SchCheck.TCheckbutton", cursor="hand2",
                            command=lambda tid=t["task_id"], v=var: self.toggle(tid, v.get())
                            ).grid(row=i, column=0, padx=(0, 4), pady=5)
            info = ttk.Frame(body, style="SchPlain.TFrame")
            info.grid(row=i, column=1, sticky="w")
            ttk.Label(info, text=t["title"] + ("  ✓" if t["is_done"] else ""), style="SchRowTitle.TLabel"
                      ).pack(anchor="w")
            ttk.Label(info, text=f"{t['task_time']}  •  {t['task_type']}", style="SchRowTime.TLabel"
                      ).pack(anchor="w")
            ttk.Label(body, text=icon, style="SchRowIcon.TLabel").grid(row=i, column=2, padx=6)
            ttk.Button(body, text="✕", style="SchX.TButton", cursor="hand2", width=3,
                       command=lambda tid=t["task_id"], n=t["title"]: self.delete(tid, n)
                       ).grid(row=i, column=3)

    def draw_upcoming_card(self):
        card = self.upcoming_card
        self.clear(card)
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text="🕒  Upcoming", style="SchCardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Separator(card, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=8)
        rows = db.fetch_all("SELECT * FROM farm_tasks WHERE user_id=%s AND task_date>%s AND is_done=0 "
                            "ORDER BY task_date, task_id LIMIT 4", (session.user_id(), date.today()))
        if not rows:
            ttk.Label(card, text="Nothing upcoming yet.", style="SchEmpty.TLabel").grid(row=2, column=0, pady=6)
        for i, t in enumerate(rows, start=2):
            icon = TYPE_STYLE.get(t["task_type"], TYPE_STYLE["Other"])[0]
            text = f"{t['task_date'].strftime('%b %d')}    {icon}  {short(t['title'], 22)}"
            ttk.Button(card, text=text + "      ›", style="SchFlat.TButton", cursor="hand2",
                       command=lambda d=t["task_date"]: self.select(d)).grid(row=i, column=0, sticky="ew")

    # ======================================================================
    #  database actions
    # ======================================================================
    def toggle(self, task_id, done):
        db.execute("UPDATE farm_tasks SET is_done=%s WHERE task_id=%s AND user_id=%s",
                   (1 if done else 0, task_id, session.user_id()))
        self.render()

    def delete(self, task_id, name):
        if messagebox.askyesno("Cancel Activity", f"Are you sure you want to cancel '{name}'?"):
            db.execute("DELETE FROM farm_tasks WHERE task_id=%s AND user_id=%s", (task_id, session.user_id()))
            self.render()

    def add_task(self, day=None):
        """Pop-up form (all ttk widgets) to add an activity."""
        day = day if isinstance(day, date) else self.selected
        win = tk.Toplevel(self)
        win.title("Add Farm Activity")
        win.geometry("420x520")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        form = ttk.Frame(win, style="SchForm.TFrame", padding=22)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="🗓  Add Farm Activity", style="SchFormTitle.TLabel").pack(anchor="w", pady=(0, 8))

        name = tk.StringVar()
        d = tk.StringVar(value=day.isoformat())
        t = tk.StringVar(value="08:00 AM")
        kind = tk.StringVar(value="Planting")
        for caption, widget in (("ACTIVITY NAME", lambda: ttk.Entry(form, textvariable=name, font=(FONT, 11))),
                                ("DATE (YYYY-MM-DD)", lambda: ttk.Entry(form, textvariable=d, font=(FONT, 11))),
                                ("TIME", lambda: ttk.Combobox(form, textvariable=t, values=TIMES, state="readonly")),
                                ("ACTIVITY TYPE", lambda: ttk.Combobox(form, textvariable=kind, values=TYPES,
                                                                       state="readonly"))):
            ttk.Label(form, text=caption, style="SchForm.TLabel").pack(anchor="w", pady=(10, 4))
            widget().pack(fill="x", ipady=3)

        def save():
            if not name.get().strip():
                return messagebox.showwarning("Missing", "Enter an activity name.", parent=win)
            try:
                valid = datetime.strptime(d.get().strip(), "%Y-%m-%d").date()
            except ValueError:
                return messagebox.showerror("Invalid Date", "Use YYYY-MM-DD.", parent=win)
            db.execute("INSERT INTO farm_tasks (user_id, title, task_date, task_time, task_type) "
                       "VALUES (%s,%s,%s,%s,%s)", (session.user_id(), name.get().strip(), valid, t.get(), kind.get()))
            win.destroy()
            self.selected = valid
            self.render()
        ttk.Button(form, text="Save Activity  ✓", style="SchPrimary.TButton", cursor="hand2",
                   command=save).pack(fill="x", pady=22)
