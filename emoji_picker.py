"""
emoji_picker.py  --  one shared EMOJI PICKER used by the Messages page, the
Community page (posts and comments) and the About-page editor.

HOW TO USE (from any page)
    import emoji_picker
    btn = emoji_picker.attach(parent_frame, some_entry_or_text_widget)
    btn.pack(side="left")
Pressing the 😊 button opens a small window with eight categories of emoji
(smileys, gestures, farm & nature, food, tools & vehicles, money & places,
fun & objects, symbols). Click an emoji and it is typed into the text box
at the cursor. The last emoji you used are kept in a "Recent" row.
"""

import tkinter as tk

from theme import C, FONT

EMOJI_FONT = "Segoe UI Emoji"

# (tab icon, name, emoji...)  -  at most 72 per category (8 columns x 9 rows)
CATEGORIES = [
    ("😀", "Smileys",
     "😀 😃 😄 😁 😆 😅 😂 🤣 😊 😇 🙂 🙃 😉 😌 😍 🥰 😘 😗 😙 😚 😋 😛 😝 😜 🤪 🤨 🧐 🤓 😎 🤩 🥳 😏 😒 😞 😔 😟 "
     "😕 🙁 😣 😖 😫 😩 🥺 😢 😭 😤 😠 😡 🤬 🤯 😳 🥵 🥶 😱 😨 😰 😥 😓 🤗 🤔 🤭 🤫 🤥 😶 😐 😑 😬 🙄 😯"),
    ("😴", "More faces",
     "😦 😧 😮 😲 😴 🤤 😪 😵 🤐 🥴 🤢 🤮 🤧 😷 🤒 🤕 🤑 🤠 😈 👿 👹 👺 🤡 💩 👻 💀 👽 👾 🤖 😺 😸 😹 😻 😼 😽 🙀 😿 "
     "😾 🙈 🙉 🙊"),
    ("👍", "Gestures & people",
     "👍 👎 👌 🤞 🤟 🤘 🤙 👈 👉 👆 👇 🤚 🖖 👋 🤝 🙏 👏 🙌 👐 🤲 💪 🤳 💅 👀 👂 👃 🧠 👅 👄 🙋 🙆 🙅 🙇 🤦 🤷 "
     "👶 👦 👧 🧑 👨 👩 👴 👵 👮 👷 👸 🤴 🎅 💂 👼 🧙 🧚 🧛 🧜 🧝"),
    ("🌾", "Farm & nature",
     "🌾 🌽 🥕 🍅 🍆 🥔 🥒 🥦 🍄 🌱 🌿 🍀 🍃 🍂 🍁 🌳 🌲 🌴 🌵 🌻 🌼 🌷 🌹 🥀 🌺 🌸 💐 🌰 🥜 🍠 "
     "🐄 🐂 🐃 🐎 🐖 🐑 🐐 🐓 🐔 🐣 🐤 🐥 🦆 🦃 🐇 🐕 🐈 🐝 🐛 🦋 🐌 🐞 🐜 🐟 🐠 🐸 🐍 🦎 🐢 🦅"),
    ("🍎", "Fruit, food & drink",
     "🍎 🍏 🍐 🍊 🍋 🍌 🍉 🍇 🍓 🍈 🍒 🍑 🥭 🍍 🥥 🥝 🍞 🥖 🥐 🧀 🥚 🍳 🥓 🍗 🍖 🥩 🍔 🍟 🍕 🌭 🌮 🌯 🥗 🍲 🍜 "
     "🍝 🍣 🍤 🍙 🍚 🍛 🍢 🍡 🍦 🍰 🎂 🍪 🍩 🍫 🍬 🍯 🥛 ☕ 🍵 🍺 🍻 🥂 🍷"),
    ("🚜", "Tools & vehicles",
     "🚜 🚛 🚚 🚐 🚗 🚕 🚌 🚲 🛵 🚁 🛸 🚀 🔧 🔨 🔩 🧰 🧲 🔌 🔋 💡 🔦 🔭 🔬 🧪 🧫 💊 💉 📡 📱 💻 📷 📸 📹 🎥 📞 "
     "📦 📏 📐 🔪 🧯 ⛽ 🚧 🛒 🧺 🧴 🧼 🧽"),
    ("💰", "Money, places & weather",
     "💰 💵 💴 💶 💷 💸 💳 🧾 📈 📉 📊 📋 📌 📍 📎 📝 📅 📆 🏠 🏡 🏢 🏭 🏪 🏬 🏥 🏦 🏫 ⛪ 🌞 🌝 🌈 🌊 💧 💦 🔥 "
     "⚡ 🌋 🌍 🌎 🌏 🧭 🌅 🌄 🌇 🌃 🌌"),
    ("🎉", "Fun & objects",
     "🎉 🎊 🎈 🎁 🏆 🥇 🥈 🥉 🏅 🎯 🎮 🎵 🎶 🎤 🎧 🎸 🎹 🎺 🎻 🥁 🎬 🎨 🎭 📚 📖 📰 🔔 🔑 🔒 🔓 ⏰ ⌛ ⚽ 🏀 "
     "🏈 ⚾ 🎾 🏐 🎱 🎳 🏓 🥊 🎣 🎪 🎡 🎢 🎠"),
    ("💖", "Symbols & hearts",
     "💖 💗 💓 💞 💕 💘 💝 💙 💚 💛 🧡 💜 🖤 💯 ✨ ⭐ 🌟 💫 💥 💢 💤 💬 💭 ✅ ❌ ❓ ❗ ⛔ 🚫 🔴 🔵 ⚪ ⚫ 🔺 🔻 "
     "➕ ➖ ➗ 💲 🔔 🔕 🆗 🆕 🆒 🆓 🔝 🔜 🔙 🔰 🏁 🚩"),
]

_recent = []          # last emoji used (newest first)
_window = None        # the picker that is currently open


def _split(text):
    return [e for e in text.split() if e]


def insert(target, emoji, replace=False):
    """Type the emoji into an Entry or Text at the cursor (or replace everything)."""
    try:
        if isinstance(target, tk.Text):
            if replace:
                target.delete("1.0", "end")
            target.insert("insert", emoji)
        else:
            if replace:
                target.delete(0, "end")
            target.insert("insert", emoji)
        target.focus_set()
    except tk.TclError:
        pass


def attach(parent, target, replace=False, bg=None):
    """Make the small 😊 button that opens the picker for `target` (an Entry or Text)."""
    bg = bg or C["white"]
    btn = tk.Button(parent, text="😊", font=(EMOJI_FONT, 12), bg=bg, activebackground=C["mint"],
                    relief="flat", bd=0, padx=6, cursor="hand2", takefocus=0)
    btn.configure(command=lambda: open_picker(btn, target, replace))
    btn.bind("<Enter>", lambda e: btn.configure(bg=C["mint"]))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


def close():
    global _window
    if _window is not None:
        try:
            _window.destroy()
        except tk.TclError:
            pass
        _window = None


def open_picker(anchor, target, replace=False):
    """Open the emoji window next to `anchor`. `replace=True` = pick ONE emoji and close (icon fields)."""
    global _window
    close()
    win = tk.Toplevel(anchor)
    _window = win
    win.title("Emoji")
    win.configure(bg=C["white"])
    win.transient(anchor.winfo_toplevel())
    win.resizable(False, False)
    win.bind("<Escape>", lambda e: close())

    # ----- category tabs -----
    tabs = tk.Frame(win, bg=C["bg"])
    tabs.pack(fill="x")
    title = tk.Label(win, text="", font=(FONT, 9, "bold"), bg=C["white"], fg=C["muted"], anchor="w")
    title.pack(fill="x", padx=10, pady=(6, 0))
    recent_row = tk.Frame(win, bg=C["white"])
    recent_row.pack(fill="x", padx=6)
    body = tk.Frame(win, bg=C["white"])
    body.pack(padx=6, pady=(2, 6))
    state = {"cat": 0}
    buttons = []

    def pick(emoji):
        insert(target, emoji, replace)
        if emoji in _recent:
            _recent.remove(emoji)
        _recent.insert(0, emoji)
        del _recent[16:]
        if replace:
            close()
        else:
            draw_recent()

    def make(parent, emoji, size=15):
        b = tk.Button(parent, text=emoji, font=(EMOJI_FONT, size), width=2, relief="flat", bd=0,
                      bg=C["white"], activebackground=C["mint"], cursor="hand2", takefocus=0,
                      command=lambda: pick(emoji))
        b.bind("<Enter>", lambda e: b.configure(bg=C["mint"]))
        b.bind("<Leave>", lambda e: b.configure(bg=C["white"]))
        return b

    def draw_recent():
        for child in recent_row.winfo_children():
            child.destroy()
        if _recent:
            tk.Label(recent_row, text="Recent", font=(FONT, 8, "bold"), bg=C["white"], fg=C["muted"]
                     ).pack(side="left", padx=(4, 2))
            for emoji in _recent[:10]:
                make(recent_row, emoji, 13).pack(side="left")

    def show(index):
        state["cat"] = index
        for child in body.winfo_children():
            child.destroy()
        icon, name, text = CATEGORIES[index]
        title.configure(text=name.upper())
        for i, emoji in enumerate(_split(text)):
            make(body, emoji).grid(row=i // 8, column=i % 8, padx=1, pady=1)
        for i, b in enumerate(buttons):
            b.configure(bg=C["green"] if i == index else C["bg"])

    for i, (icon, name, _text) in enumerate(CATEGORIES):
        b = tk.Button(tabs, text=icon, font=(EMOJI_FONT, 13), relief="flat", bd=0, padx=5, pady=3,
                      bg=C["bg"], activebackground=C["green"], cursor="hand2", takefocus=0,
                      command=lambda n=i: show(n))
        b.pack(side="left")
        buttons.append(b)
    foot = tk.Frame(win, bg=C["white"])
    foot.pack(fill="x", padx=8, pady=(0, 8))
    tk.Button(foot, text="Close", command=close, font=(FONT, 9, "bold"), bg=C["muted"], fg="white",
              relief="flat", bd=0, padx=12, pady=3, cursor="hand2", takefocus=0).pack(side="right")
    tk.Label(foot, text="Click an emoji to add it" if not replace else "Click an emoji to use it",
             font=(FONT, 8), bg=C["white"], fg=C["muted"]).pack(side="left")
    draw_recent()
    show(0)

    # ----- place it next to the button, inside the screen -----
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    x = max(0, min(anchor.winfo_rootx(), sw - w - 10))
    y = anchor.winfo_rooty() + anchor.winfo_height() + 4
    if y + h > sh - 50:                       # not enough room below: open above the button
        y = max(0, anchor.winfo_rooty() - h - 4)
    win.geometry(f"+{x}+{y}")
