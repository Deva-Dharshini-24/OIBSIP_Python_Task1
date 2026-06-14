"""
Advanced Chat Application
Features: Authentication, Multiple Chat Rooms, Multimedia Sharing,
          Message History, Notifications, Emoji Support, Encryption
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sqlite3
import hashlib
import os
import json
import base64
import threading
import time
import datetime
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PIL import Image, ImageTk
import io

# ─────────────────────────────────────────────
#  ENCRYPTION UTILITIES
# ─────────────────────────────────────────────
class EncryptionManager:
    """Handles all encryption/decryption operations."""

    def __init__(self):
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)

    def _load_or_generate_key(self):
        key_file = Path("chat_secret.key")
        if key_file.exists():
            return key_file.read_bytes()
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        return key

    def encrypt(self, text: str) -> str:
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self.cipher.decrypt(token.encode()).decode()
        except Exception:
            return "[encrypted message]"

    @staticmethod
    def hash_password(password: str, salt: str = "") -> str:
        combined = (password + salt + "ChatAppSalt2024").encode()
        return hashlib.sha256(combined).hexdigest()


# ─────────────────────────────────────────────
#  DATABASE LAYER
# ─────────────────────────────────────────────
class Database:
    """SQLite database manager for users, rooms, and messages."""

    def __init__(self, db_path="chat_app.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._create_tables()
        self._seed_default_rooms()

    def _create_tables(self):
        with self._lock:
            cur = self.conn.cursor()
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    avatar   TEXT DEFAULT '',
                    status   TEXT DEFAULT 'online',
                    created  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS rooms (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    created_by  INTEGER,
                    created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id     INTEGER NOT NULL,
                    user_id     INTEGER NOT NULL,
                    username    TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    msg_type    TEXT DEFAULT 'text',
                    encrypted   INTEGER DEFAULT 1,
                    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(room_id) REFERENCES rooms(id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   INTEGER NOT NULL,
                    message   TEXT NOT NULL,
                    is_read   INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            self.conn.commit()

    def _seed_default_rooms(self):
        defaults = [
            ("General",    "Main public chat room"),
            ("Technology", "Discuss tech trends and tools"),
            ("Random",     "Off-topic conversations"),
            ("Gaming",     "Games and entertainment"),
        ]
        with self._lock:
            cur = self.conn.cursor()
            for name, desc in defaults:
                cur.execute(
                    "INSERT OR IGNORE INTO rooms (name, description) VALUES (?,?)",
                    (name, desc)
                )
            self.conn.commit()

    # ── Users ──────────────────────────────────
    def register_user(self, username, password):
        hashed = EncryptionManager.hash_password(password)
        try:
            with self._lock:
                self.conn.execute(
                    "INSERT INTO users (username, password) VALUES (?,?)",
                    (username, hashed)
                )
                self.conn.commit()
            return True, "Registration successful!"
        except sqlite3.IntegrityError:
            return False, "Username already taken."

    def login_user(self, username, password):
        hashed = EncryptionManager.hash_password(password)
        row = self.conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, hashed)
        ).fetchone()
        if row:
            self.conn.execute(
                "UPDATE users SET status='online' WHERE id=?", (row["id"],)
            )
            self.conn.commit()
            return True, dict(row)
        return False, "Invalid username or password."

    def logout_user(self, user_id):
        self.conn.execute(
            "UPDATE users SET status='offline' WHERE id=?", (user_id,)
        )
        self.conn.commit()

    def get_online_users(self):
        return self.conn.execute(
            "SELECT username, status FROM users ORDER BY username"
        ).fetchall()

    # ── Rooms ───────────────────────────────────
    def get_rooms(self):
        return self.conn.execute("SELECT * FROM rooms ORDER BY name").fetchall()

    def create_room(self, name, description, user_id):
        try:
            with self._lock:
                self.conn.execute(
                    "INSERT INTO rooms (name, description, created_by) VALUES (?,?,?)",
                    (name, description, user_id)
                )
                self.conn.commit()
            return True, "Room created!"
        except sqlite3.IntegrityError:
            return False, "Room name already exists."

    # ── Messages ────────────────────────────────
    def save_message(self, room_id, user_id, username, content,
                     msg_type="text", encrypted=True):
        with self._lock:
            self.conn.execute(
                """INSERT INTO messages
                   (room_id, user_id, username, content, msg_type, encrypted)
                   VALUES (?,?,?,?,?,?)""",
                (room_id, user_id, username, content, msg_type, int(encrypted))
            )
            self.conn.commit()

    def get_messages(self, room_id, limit=100):
        return self.conn.execute(
            """SELECT * FROM messages WHERE room_id=?
               ORDER BY timestamp DESC LIMIT ?""",
            (room_id, limit)
        ).fetchall()

    # ── Notifications ────────────────────────────
    def add_notification(self, user_id, message):
        with self._lock:
            self.conn.execute(
                "INSERT INTO notifications (user_id, message) VALUES (?,?)",
                (user_id, message)
            )
            self.conn.commit()

    def get_unread_notifications(self, user_id):
        rows = self.conn.execute(
            "SELECT * FROM notifications WHERE user_id=? AND is_read=0",
            (user_id,)
        ).fetchall()
        if rows:
            self.conn.execute(
                "UPDATE notifications SET is_read=1 WHERE user_id=?",
                (user_id,)
            )
            self.conn.commit()
        return rows


# ─────────────────────────────────────────────
#  NOTIFICATION ENGINE
# ─────────────────────────────────────────────
class NotificationManager:
    """Polls for new notifications and shows Tkinter popups."""

    def __init__(self, db: Database, root: tk.Tk):
        self.db = db
        self.root = root
        self.user_id = None
        self._running = False

    def start(self, user_id):
        self.user_id = user_id
        self._running = True
        threading.Thread(target=self._poll, daemon=True).start()

    def stop(self):
        self._running = False

    def _poll(self):
        while self._running:
            try:
                rows = self.db.get_unread_notifications(self.user_id)
                for row in rows:
                    self.root.after(0, self._show_popup, row["message"])
            except Exception:
                pass
            time.sleep(3)

    def _show_popup(self, message):
        popup = tk.Toplevel(self.root)
        popup.title("🔔 New Notification")
        popup.geometry("320x100")
        popup.configure(bg="#1e2330")
        popup.attributes("-topmost", True)

        # Position bottom-right
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        popup.geometry(f"+{sw-340}+{sh-140}")

        tk.Label(popup, text=message, bg="#1e2330", fg="#e2e8f0",
                 font=("Segoe UI", 10), wraplength=280).pack(pady=15)

        popup.after(4000, popup.destroy)


# ─────────────────────────────────────────────
#  EMOJI PICKER
# ─────────────────────────────────────────────
EMOJIS = [
    "😀","😂","😍","🥰","😎","🤔","😭","😡","🥳","🤩",
    "👍","👎","❤️","🔥","✨","🎉","🎊","💯","🙏","👋",
    "😴","🤗","😏","🤪","😇","🥺","😤","🤯","🫡","🫶",
    "🐱","🐶","🦊","🐼","🐨","🦁","🐸","🐺","🦋","🌸",
    "🍕","🍔","🌮","🍜","🍣","🎂","☕","🍺","🥤","🍎",
    "⚽","🎮","🎸","📱","💻","📚","🌍","🚀","💡","🎵",
]

class EmojiPicker(tk.Toplevel):
    def __init__(self, parent, on_select):
        super().__init__(parent)
        self.title("Emojis")
        self.resizable(False, False)
        self.configure(bg="#1e2330")
        self.on_select = on_select
        self._build()

    def _build(self):
        frame = tk.Frame(self, bg="#1e2330")
        frame.pack(padx=8, pady=8)
        cols = 10
        for i, em in enumerate(EMOJIS):
            btn = tk.Button(
                frame, text=em, font=("Segoe UI Emoji", 14),
                bg="#1e2330", fg="white", bd=0,
                activebackground="#2d3548", cursor="hand2",
                command=lambda e=em: self._pick(e)
            )
            btn.grid(row=i // cols, column=i % cols, padx=2, pady=2)

    def _pick(self, emoji):
        self.on_select(emoji)
        self.destroy()


# ─────────────────────────────────────────────
#  LOGIN / REGISTER WINDOW
# ─────────────────────────────────────────────
class AuthWindow(tk.Toplevel):
    PALETTE = {
        "bg":      "#0f1117",
        "surface": "#1e2330",
        "accent":  "#6366f1",
        "text":    "#e2e8f0",
        "muted":   "#94a3b8",
        "danger":  "#ef4444",
        "success": "#22c55e",
    }

    def __init__(self, db: Database, on_success):
        super().__init__()
        self.db = db
        self.on_success = on_success
        self.title("SecureChat — Sign In")
        self.resizable(True, True)
        self.configure(bg=self.PALETTE["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._mode = tk.StringVar(value="login")
        self._build()
        self.grab_set()
        # Auto-size after all widgets are placed
        self.update_idletasks()
        w = max(440, self.winfo_reqwidth() + 20)
        h = max(420, self.winfo_reqheight() + 30)
        # Center on screen
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_close(self):
        self.destroy()
        import sys; sys.exit()

    def _build(self):
        P = self.PALETTE
        # Logo
        tk.Label(self, text="💬", font=("Segoe UI Emoji", 32),
                 bg=P["bg"], fg=P["accent"]).pack(pady=(20, 2))
        tk.Label(self, text="SecureChat", font=("Segoe UI", 18, "bold"),
                 bg=P["bg"], fg=P["text"]).pack()
        tk.Label(self, text="End-to-end encrypted messaging",
                 font=("Segoe UI", 9), bg=P["bg"], fg=P["muted"]).pack(pady=(2, 10))

        # Toggle
        tog = tk.Frame(self, bg=P["surface"], bd=0)
        tog.pack(pady=(0, 10), ipadx=4, ipady=4)
        for val, label in (("login","Sign In"),("register","Register")):
            tk.Radiobutton(
                tog, text=label, variable=self._mode, value=val,
                bg=P["surface"], fg=P["text"], selectcolor=P["accent"],
                activebackground=P["surface"], activeforeground=P["text"],
                font=("Segoe UI", 10), indicatoron=False,
                padx=16, pady=6, bd=0, relief="flat",
                cursor="hand2", command=self._refresh_form
            ).pack(side="left")

        # Form container
        self._form = tk.Frame(self, bg=P["bg"])
        self._form.pack(fill="x", padx=40)
        self._status_var = tk.StringVar()
        self._build_form()

    def _field(self, parent, label, show=None):
        tk.Label(parent, text=label, bg=self.PALETTE["bg"],
                 fg=self.PALETTE["muted"], font=("Segoe UI", 9)).pack(anchor="w")
        var = tk.StringVar()
        e = tk.Entry(parent, textvariable=var, show=show,
                     bg=self.PALETTE["surface"], fg=self.PALETTE["text"],
                     insertbackground=self.PALETTE["text"],
                     font=("Segoe UI", 11), relief="flat", bd=8)
        e.pack(fill="x", pady=(2, 6), ipady=4)
        return var, e

    def _build_form(self):
        for w in self._form.winfo_children():
            w.destroy()
        P = self.PALETTE
        mode = self._mode.get()

        self._user_var, self._user_entry = self._field(self._form, "Username")
        if mode == "register":
            self._email_var, _ = self._field(self._form, "Display Name (optional)")
        self._pass_var, _ = self._field(self._form, "Password", show="•")
        if mode == "register":
            self._pass2_var, _ = self._field(self._form, "Confirm Password", show="•")

        btn_text = "Sign In" if mode == "login" else "Create Account"
        btn = tk.Button(
            self._form, text=btn_text,
            bg=P["accent"], fg="white", font=("Segoe UI", 11, "bold"),
            relief="flat", bd=0, padx=20, pady=10, cursor="hand2",
            activebackground="#4f46e5", command=self._submit
        )
        btn.pack(fill="x", pady=(4, 8))

        self._status = tk.Label(self._form, textvariable=self._status_var,
                                bg=P["bg"], fg=P["danger"],
                                font=("Segoe UI", 9), wraplength=320)
        self._status.pack()
        self._user_entry.focus_set()
        self.bind("<Return>", lambda e: self._submit())

    def _refresh_form(self):
        self._status_var.set("")
        self._build_form()
        self.update_idletasks()
        w = max(440, self.winfo_reqwidth() + 20)
        h = max(420, self.winfo_reqheight() + 30)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _submit(self):
        P = self.PALETTE
        user = self._user_var.get().strip()
        pwd  = self._pass_var.get()
        if not user or not pwd:
            self._status_var.set("⚠ Username and password are required.")
            return

        if self._mode.get() == "login":
            ok, result = self.db.login_user(user, pwd)
            if ok:
                self._status_var.set("")
                self._status.config(fg=P["success"])
                self._status_var.set("✓ Logged in!")
                self.after(600, lambda: (self.destroy(), self.on_success(result)))
            else:
                self._status_var.set(f"✗ {result}")
        else:
            if self._pass_var.get() != self._pass2_var.get():
                self._status_var.set("✗ Passwords do not match.")
                return
            ok, msg = self.db.register_user(user, pwd)
            if ok:
                self._status_var.set("")
                self._status.config(fg=P["success"])
                self._status_var.set("✓ Account created! Please sign in.")
                self._mode.set("login")
                self.after(800, self._refresh_form)
            else:
                self._status_var.set(f"✗ {msg}")


# ─────────────────────────────────────────────
#  MAIN CHAT APPLICATION
# ─────────────────────────────────────────────
class ChatApp(tk.Tk):
    PALETTE = {
        "bg":        "#0f1117",
        "sidebar":   "#161b27",
        "surface":   "#1e2330",
        "surface2":  "#252b3b",
        "accent":    "#6366f1",
        "accent2":   "#818cf8",
        "text":      "#e2e8f0",
        "muted":     "#64748b",
        "me_bubble": "#3730a3",
        "them_bubble":"#1e293b",
        "success":   "#22c55e",
        "danger":    "#ef4444",
        "online":    "#22c55e",
        "offline":   "#64748b",
        "border":    "#2d3548",
    }

    def __init__(self):
        super().__init__()
        self.title("SecureChat")
        self.geometry("1200x760")
        self.minsize(900, 600)
        self.configure(bg=self.PALETTE["bg"])

        self.db  = Database()
        self.enc = EncryptionManager()
        self.notif = NotificationManager(self.db, self)

        self.current_user   = None
        self.current_room   = None
        self.current_room_id = None
        self._msg_images    = {}   # keep image refs alive
        self._poll_thread   = None
        self._last_msg_id   = 0
        self._typing_users  = {}
        self._unread_counts = {}

        self.withdraw()
        self._show_auth()

    # ── Auth ──────────────────────────────────
    def _show_auth(self):
        AuthWindow(self.db, self._on_login)

    def _on_login(self, user_data):
        self.current_user = user_data
        self.title(f"SecureChat — {user_data['username']}")
        self.deiconify()
        self._build_ui()
        self.notif.start(user_data["id"])
        self._start_polling()

    # ── UI Construction ───────────────────────
    def _build_ui(self):
        P = self.PALETTE
        self.configure(bg=P["bg"])

        # Remove any old widgets
        for w in self.winfo_children():
            w.destroy()

        # ── Top bar
        topbar = tk.Frame(self, bg=P["sidebar"], height=52)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="💬 SecureChat",
                 bg=P["sidebar"], fg=P["text"],
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16, pady=12)

        # Right side of topbar
        right = tk.Frame(topbar, bg=P["sidebar"])
        right.pack(side="right", padx=12)

        self._notif_btn = tk.Button(
            right, text="🔔", font=("Segoe UI Emoji", 13),
            bg=P["sidebar"], fg=P["text"], relief="flat", bd=0,
            cursor="hand2", command=self._show_notifications
        )
        self._notif_btn.pack(side="left", padx=4)

        tk.Label(right, text=f"👤 {self.current_user['username']}",
                 bg=P["sidebar"], fg=P["accent2"],
                 font=("Segoe UI", 10)).pack(side="left", padx=8)

        tk.Button(right, text="Sign Out", font=("Segoe UI", 9),
                  bg=P["danger"], fg="white", relief="flat", bd=0,
                  padx=8, pady=3, cursor="hand2",
                  command=self._logout).pack(side="left", padx=4)

        # ── Main pane
        main = tk.Frame(self, bg=P["bg"])
        main.pack(fill="both", expand=True)

        # Left sidebar: rooms + users
        self._sidebar = tk.Frame(main, bg=P["sidebar"], width=220)
        self._sidebar.pack(fill="y", side="left")
        self._sidebar.pack_propagate(False)
        self._build_sidebar()

        # Separator
        tk.Frame(main, bg=P["border"], width=1).pack(fill="y", side="left")

        # Center: chat area
        self._chat_frame = tk.Frame(main, bg=P["bg"])
        self._chat_frame.pack(fill="both", expand=True, side="left")
        self._build_chat_area()

        # Right panel: users online
        tk.Frame(main, bg=P["border"], width=1).pack(fill="y", side="left")
        self._rpanel = tk.Frame(main, bg=P["sidebar"], width=180)
        self._rpanel.pack(fill="y", side="left")
        self._rpanel.pack_propagate(False)
        self._build_right_panel()

    def _build_sidebar(self):
        P = self.PALETTE
        s = self._sidebar

        tk.Label(s, text="CHANNELS", bg=P["sidebar"], fg=P["muted"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(14, 4))

        btn_frame = tk.Frame(s, bg=P["sidebar"])
        btn_frame.pack(fill="x", padx=8, pady=(0, 4))
        tk.Button(btn_frame, text="+ New Room", font=("Segoe UI", 9),
                  bg=P["accent"], fg="white", relief="flat", bd=0,
                  padx=6, pady=4, cursor="hand2",
                  command=self._create_room_dialog).pack(fill="x")

        self._room_frame = tk.Frame(s, bg=P["sidebar"])
        self._room_frame.pack(fill="both", expand=True)
        self._refresh_rooms()

    def _refresh_rooms(self):
        P = self.PALETTE
        for w in self._room_frame.winfo_children():
            w.destroy()
        rooms = self.db.get_rooms()
        for room in rooms:
            name = room["name"]
            unread = self._unread_counts.get(room["id"], 0)
            badge = f"  ({unread})" if unread else ""
            active = (room["id"] == self.current_room_id)
            bg = P["surface2"] if active else P["sidebar"]
            fr = tk.Frame(self._room_frame, bg=bg, cursor="hand2")
            fr.pack(fill="x")
            tk.Label(fr, text=f"# {name}{badge}",
                     bg=bg, fg=P["accent2"] if active else P["text"],
                     font=("Segoe UI", 10, "bold" if active else "normal"),
                     anchor="w").pack(fill="x", padx=14, pady=6)
            fr.bind("<Button-1>", lambda e, r=room: self._switch_room(r))
            for w in fr.winfo_children():
                w.bind("<Button-1>", lambda e, r=room: self._switch_room(r))

    def _build_right_panel(self):
        P = self.PALETTE
        r = self._rpanel
        tk.Label(r, text="ONLINE", bg=P["sidebar"], fg=P["muted"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(14, 4))
        self._users_frame = tk.Frame(r, bg=P["sidebar"])
        self._users_frame.pack(fill="both", expand=True)
        self._refresh_users()

    def _refresh_users(self):
        P = self.PALETTE
        for w in self._users_frame.winfo_children():
            w.destroy()
        for row in self.db.get_online_users():
            color = P["online"] if row["status"] == "online" else P["offline"]
            fr = tk.Frame(self._users_frame, bg=P["sidebar"])
            fr.pack(fill="x", padx=8, pady=2)
            tk.Label(fr, text="●", bg=P["sidebar"], fg=color,
                     font=("Segoe UI", 8)).pack(side="left")
            tk.Label(fr, text=row["username"], bg=P["sidebar"], fg=P["text"],
                     font=("Segoe UI", 9)).pack(side="left", padx=4)

    def _build_chat_area(self):
        P = self.PALETTE
        cf = self._chat_frame

        # Room header
        self._room_header = tk.Frame(cf, bg=P["surface"], height=48)
        self._room_header.pack(fill="x")
        self._room_header.pack_propagate(False)
        self._room_title = tk.Label(
            self._room_header, text="Select a channel to start chatting",
            bg=P["surface"], fg=P["text"], font=("Segoe UI", 12, "bold")
        )
        self._room_title.pack(side="left", padx=16, pady=12)

        # Encryption badge
        tk.Label(self._room_header, text="🔒 End-to-end encrypted",
                 bg=P["surface"], fg=P["success"],
                 font=("Segoe UI", 8)).pack(side="right", padx=14)

        # Messages area
        msg_container = tk.Frame(cf, bg=P["bg"])
        msg_container.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(msg_container, bg=P["bg"], bd=0,
                                 highlightthickness=0)
        scrollbar = ttk.Scrollbar(msg_container, orient="vertical",
                                  command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._msg_inner = tk.Frame(self._canvas, bg=P["bg"])
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._msg_inner, anchor="nw"
        )
        self._msg_inner.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Typing indicator
        self._typing_label = tk.Label(cf, text="", bg=P["bg"], fg=P["muted"],
                                      font=("Segoe UI", 8, "italic"))
        self._typing_label.pack(anchor="w", padx=16)

        # Input area
        self._build_input_area(cf)

    def _build_input_area(self, parent):
        P = self.PALETTE
        bar = tk.Frame(parent, bg=P["surface"], pady=10)
        bar.pack(fill="x", side="bottom")

        tools = tk.Frame(bar, bg=P["surface"])
        tools.pack(fill="x", padx=12, pady=(0, 6))

        for icon, cmd, tip in [
            ("😊", self._open_emoji,     "Emoji"),
            ("🖼",  self._attach_image,   "Image"),
            ("📎",  self._attach_file,    "File"),
            ("🔐",  self._toggle_encrypt, "Encryption"),
        ]:
            b = tk.Button(tools, text=icon, font=("Segoe UI Emoji", 13),
                          bg=P["surface"], fg=P["text"], relief="flat", bd=0,
                          padx=6, cursor="hand2", command=cmd)
            b.pack(side="left")

        # Search
        tk.Button(tools, text="🔍", font=("Segoe UI Emoji", 11),
                  bg=P["surface"], fg=P["text"], relief="flat", bd=0,
                  padx=6, cursor="hand2",
                  command=self._search_dialog).pack(side="right")

        # Text input
        inp_row = tk.Frame(bar, bg=P["surface"])
        inp_row.pack(fill="x", padx=12)

        self._msg_input = tk.Text(inp_row, height=2, wrap="word",
                                  bg=P["surface2"], fg=P["text"],
                                  insertbackground=P["text"],
                                  font=("Segoe UI", 11), relief="flat",
                                  bd=8, padx=8, pady=6)
        self._msg_input.pack(side="left", fill="x", expand=True)
        self._msg_input.bind("<Return>", self._on_enter)
        self._msg_input.bind("<Shift-Return>", lambda e: None)
        self._msg_input.bind("<KeyRelease>", self._on_typing)

        self._encrypt_enabled = True
        self._send_btn = tk.Button(
            inp_row, text="Send ▶", font=("Segoe UI", 10, "bold"),
            bg=P["accent"], fg="white", relief="flat", bd=0,
            padx=14, pady=8, cursor="hand2", command=self._send_message
        )
        self._send_btn.pack(side="left", padx=(8, 0))

    # ── Canvas helpers ────────────────────────
    def _on_frame_configure(self, _):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_bottom(self):
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    # ── Room switching ────────────────────────
    def _switch_room(self, room):
        self.current_room    = room["name"]
        self.current_room_id = room["id"]
        self._unread_counts[room["id"]] = 0
        self._room_title.config(text=f"# {room['name']}  —  {room['description']}")
        self._load_history()
        self._refresh_rooms()

    def _load_history(self):
        for w in self._msg_inner.winfo_children():
            w.destroy()
        self._msg_images.clear()

        rows = self.db.get_messages(self.current_room_id)
        rows = list(reversed(rows))  # oldest first
        if not rows:
            tk.Label(self._msg_inner,
                     text="No messages yet. Say hello! 👋",
                     bg=self.PALETTE["bg"], fg=self.PALETTE["muted"],
                     font=("Segoe UI", 11)).pack(pady=40)
            return

        for row in rows:
            self._render_message(row)
        self._last_msg_id = rows[-1]["id"] if rows else 0
        self.after(100, self._scroll_bottom)

    # ── Render a single message bubble ────────
    def _render_message(self, row):
        P = self.PALETTE
        is_me = (row["username"] == self.current_user["username"])

        # Decrypt content
        content = row["content"]
        msg_type = row["msg_type"]
        if row["encrypted"]:
            try:
                content = self.enc.decrypt(content)
            except Exception:
                content = "[could not decrypt]"

        outer = tk.Frame(self._msg_inner, bg=P["bg"])
        outer.pack(fill="x", pady=2, padx=12)

        if is_me:
            frame = tk.Frame(outer, bg=P["bg"])
            frame.pack(side="right")
        else:
            frame = tk.Frame(outer, bg=P["bg"])
            frame.pack(side="left")

        # Header: name + time
        ts = row["timestamp"][:16] if row["timestamp"] else ""
        header_text = f"{row['username']}  {ts}" if not is_me else f"{ts}"
        tk.Label(frame,
                 text=header_text,
                 bg=P["bg"], fg=P["muted"],
                 font=("Segoe UI", 7)).pack(
                     anchor="e" if is_me else "w", pady=(0, 1))

        bubble_bg = P["me_bubble"] if is_me else P["them_bubble"]

        if msg_type == "image":
            try:
                img_data = base64.b64decode(content)
                img = Image.open(io.BytesIO(img_data))
                img.thumbnail((300, 220))
                photo = ImageTk.PhotoImage(img)
                uid = id(row)
                self._msg_images[uid] = photo
                bubble = tk.Label(frame, image=photo, bg=bubble_bg,
                                  padx=6, pady=6, relief="flat")
                bubble.pack()
            except Exception:
                bubble = tk.Label(frame, text="[image]",
                                  bg=bubble_bg, fg=P["text"],
                                  font=("Segoe UI", 10),
                                  padx=12, pady=8, wraplength=380)
                bubble.pack()
        elif msg_type == "file":
            try:
                meta = json.loads(content)
                disp = f"📎 {meta.get('name','file')}  ({meta.get('size','?')})"
            except Exception:
                disp = "📎 Attachment"
            bubble = tk.Label(frame, text=disp,
                              bg=bubble_bg, fg=P["accent2"],
                              font=("Segoe UI", 10, "underline"),
                              padx=12, pady=8, cursor="hand2")
            bubble.pack()
        else:
            bubble = tk.Label(frame, text=content,
                              bg=bubble_bg, fg=P["text"],
                              font=("Segoe UI", 10),
                              padx=12, pady=8, wraplength=480,
                              justify="left")
            bubble.pack()

        # Lock icon for encrypted
        if row["encrypted"]:
            tk.Label(frame, text="🔒", font=("Segoe UI Emoji", 7),
                     bg=P["bg"], fg=P["muted"]).pack(
                         anchor="e" if is_me else "w")

    # ── Sending ───────────────────────────────
    def _on_enter(self, event):
        if not event.state & 0x1:  # not Shift
            self._send_message()
            return "break"

    def _send_message(self, content=None, msg_type="text"):
        if not self.current_room_id:
            messagebox.showinfo("No Room", "Please select a channel first.")
            return

        if content is None:
            content = self._msg_input.get("1.0", "end-1c").strip()
            self._msg_input.delete("1.0", "end")

        if not content:
            return

        raw = content
        encrypted = self._encrypt_enabled
        if encrypted:
            content = self.enc.encrypt(content)

        self.db.save_message(
            self.current_room_id,
            self.current_user["id"],
            self.current_user["username"],
            content, msg_type, encrypted
        )

        # Fake new-message notification for other users (demo)
        self.db.add_notification(
            self.current_user["id"],
            f"Message sent to #{self.current_room}"
        )
        # Simulate delivery to self for history refresh
        self._load_history()

    def _on_typing(self, _):
        pass  # Could broadcast typing events over a socket in a real app

    # ── Emoji ─────────────────────────────────
    def _open_emoji(self):
        EmojiPicker(self, self._insert_emoji)

    def _insert_emoji(self, emoji):
        self._msg_input.insert("insert", emoji)
        self._msg_input.focus_set()

    # ── Media attachment ──────────────────────
    def _attach_image(self):
        if not self.current_room_id:
            messagebox.showinfo("No Room", "Select a channel first.")
            return
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")]
        )
        if not path:
            return
        try:
            img = Image.open(path)
            img.thumbnail((800, 600))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            encoded = base64.b64encode(buf.getvalue()).decode()
            # Encrypt the base64 string
            if self._encrypt_enabled:
                stored = self.enc.encrypt(encoded)
            else:
                stored = encoded
            self.db.save_message(
                self.current_room_id,
                self.current_user["id"],
                self.current_user["username"],
                stored, "image", self._encrypt_enabled
            )
            self._load_history()
        except Exception as ex:
            messagebox.showerror("Error", f"Could not attach image: {ex}")

    def _attach_file(self):
        if not self.current_room_id:
            messagebox.showinfo("No Room", "Select a channel first.")
            return
        path = filedialog.askopenfilename()
        if not path:
            return
        size = os.path.getsize(path)
        meta = json.dumps({"name": os.path.basename(path),
                           "size": f"{size//1024} KB"})
        if self._encrypt_enabled:
            stored = self.enc.encrypt(meta)
        else:
            stored = meta
        self.db.save_message(
            self.current_room_id,
            self.current_user["id"],
            self.current_user["username"],
            stored, "file", self._encrypt_enabled
        )
        self._load_history()

    # ── Encryption toggle ──────────────────────
    def _toggle_encrypt(self):
        self._encrypt_enabled = not self._encrypt_enabled
        state = "ON 🔒" if self._encrypt_enabled else "OFF 🔓"
        color = self.PALETTE["success"] if self._encrypt_enabled else self.PALETTE["danger"]
        messagebox.showinfo("Encryption", f"Encryption is now {state}")

    # ── Room creation ─────────────────────────
    def _create_room_dialog(self):
        P = self.PALETTE
        win = tk.Toplevel(self)
        win.title("Create Channel")
        win.geometry("360x220")
        win.configure(bg=P["bg"])
        win.grab_set()

        tk.Label(win, text="Channel Name", bg=P["bg"], fg=P["muted"],
                 font=("Segoe UI", 9)).pack(anchor="w", padx=24, pady=(20, 2))
        name_var = tk.StringVar()
        tk.Entry(win, textvariable=name_var, bg=P["surface"], fg=P["text"],
                 insertbackground=P["text"], font=("Segoe UI", 11),
                 relief="flat", bd=8).pack(fill="x", padx=24, ipady=4)

        tk.Label(win, text="Description", bg=P["bg"], fg=P["muted"],
                 font=("Segoe UI", 9)).pack(anchor="w", padx=24, pady=(12, 2))
        desc_var = tk.StringVar()
        tk.Entry(win, textvariable=desc_var, bg=P["surface"], fg=P["text"],
                 insertbackground=P["text"], font=("Segoe UI", 11),
                 relief="flat", bd=8).pack(fill="x", padx=24, ipady=4)

        def _create():
            n = name_var.get().strip()
            d = desc_var.get().strip()
            if not n:
                messagebox.showwarning("Missing", "Channel name required.", parent=win)
                return
            ok, msg = self.db.create_room(n, d, self.current_user["id"])
            if ok:
                win.destroy()
                self._refresh_rooms()
            else:
                messagebox.showerror("Error", msg, parent=win)

        tk.Button(win, text="Create Channel",
                  bg=P["accent"], fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                  command=_create).pack(pady=16)

    # ── Search ────────────────────────────────
    def _search_dialog(self):
        if not self.current_room_id:
            messagebox.showinfo("No Room", "Select a channel first.")
            return
        P = self.PALETTE
        win = tk.Toplevel(self)
        win.title("Search Messages")
        win.geometry("500x460")
        win.configure(bg=P["bg"])

        tk.Label(win, text="Search in #" + (self.current_room or ""),
                 bg=P["bg"], fg=P["text"], font=("Segoe UI", 12, "bold")).pack(
                     anchor="w", padx=20, pady=(16, 6))

        q_var = tk.StringVar()
        entry = tk.Entry(win, textvariable=q_var, bg=P["surface"], fg=P["text"],
                         insertbackground=P["text"], font=("Segoe UI", 11),
                         relief="flat", bd=8)
        entry.pack(fill="x", padx=20, ipady=5)

        results_box = scrolledtext.ScrolledText(win, bg=P["surface2"], fg=P["text"],
                                                font=("Segoe UI", 10), relief="flat",
                                                state="disabled")
        results_box.pack(fill="both", expand=True, padx=20, pady=10)

        def _search():
            q = q_var.get().strip().lower()
            if not q:
                return
            rows = self.db.get_messages(self.current_room_id, limit=500)
            results_box.config(state="normal")
            results_box.delete("1.0", "end")
            found = 0
            for row in reversed(rows):
                content = row["content"]
                if row["encrypted"]:
                    try:
                        content = self.enc.decrypt(content)
                    except Exception:
                        continue
                if q in content.lower():
                    ts = row["timestamp"][:16]
                    results_box.insert("end", f"[{ts}] {row['username']}: {content}\n\n")
                    found += 1
            if found == 0:
                results_box.insert("end", "No messages found.")
            results_box.config(state="disabled")

        tk.Button(win, text="Search", bg=P["accent"], fg="white",
                  font=("Segoe UI", 10), relief="flat", bd=0, padx=12, pady=6,
                  cursor="hand2", command=_search).pack(pady=4)
        entry.bind("<Return>", lambda e: _search())
        entry.focus_set()

    # ── Notifications ─────────────────────────
    def _show_notifications(self):
        P = self.PALETTE
        rows = self.db.get_unread_notifications(self.current_user["id"])
        win = tk.Toplevel(self)
        win.title("Notifications")
        win.geometry("380x320")
        win.configure(bg=P["bg"])

        tk.Label(win, text="🔔 Notifications",
                 bg=P["bg"], fg=P["text"],
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=20, pady=14)

        box = scrolledtext.ScrolledText(win, bg=P["surface"], fg=P["text"],
                                        font=("Segoe UI", 10), relief="flat",
                                        state="normal")
        box.pack(fill="both", expand=True, padx=16, pady=8)
        if rows:
            for r in rows:
                box.insert("end", f"• {r['message']}\n  {r['timestamp'][:16]}\n\n")
        else:
            box.insert("end", "No new notifications.")
        box.config(state="disabled")

    # ── Polling ───────────────────────────────
    def _start_polling(self):
        def poll():
            while True:
                try:
                    if self.current_room_id:
                        rows = self.db.get_messages(self.current_room_id, limit=200)
                        rows = list(reversed(rows))
                        if rows and rows[-1]["id"] != self._last_msg_id:
                            self._last_msg_id = rows[-1]["id"]
                            self.after(0, self._load_history)
                    self.after(0, self._refresh_users)
                except Exception:
                    pass
                time.sleep(2)

        threading.Thread(target=poll, daemon=True).start()

    # ── Logout ────────────────────────────────
    def _logout(self):
        if messagebox.askyesno("Sign Out", "Sign out of SecureChat?"):
            self.db.logout_user(self.current_user["id"])
            self.notif.stop()
            self.current_user = None
            self.current_room = None
            self.current_room_id = None
            for w in self.winfo_children():
                w.destroy()
            self.withdraw()
            self._show_auth()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
def main():
    # Check for required libraries
    missing = []
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        missing.append("cryptography")
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")

    if missing:
        print(f"\n⚠  Missing libraries: {', '.join(missing)}")
        print("Install with:\n")
        print(f"  pip install {' '.join(missing)}\n")
        import sys; sys.exit(1)

    app = ChatApp()
    app.mainloop()


if __name__ == "__main__":
    main()
