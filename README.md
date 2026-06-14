<# 💬 SecureChat

A desktop chat application built with **Python** and **Tkinter**, featuring user authentication, multiple chat rooms, multimedia sharing, message history, notifications, emoji support, and message encryption.

---

## ✨ Features

- **User Authentication** — Register and log in with SHA-256 hashed passwords (no plaintext storage)
- **Multiple Chat Rooms** — Default channels (General, Technology, Random, Gaming) plus the ability to create custom rooms
- **Multimedia Sharing** — Send images (auto-displayed as thumbnails) and file attachments
- **Message History** — All messages persist in a local SQLite database and reload per room
- **Message Search** — Keyword search across a room's message history
- **In-App Notifications** — Popup alerts plus a notification log accessible from the bell icon
- **Emoji Support** — Built-in emoji picker for inserting emojis into messages
- **Encryption at Rest** — Messages and media are encrypted using Fernet (AES) before being stored, with a toggle to enable/disable per message

---

## 🛠️ Tech Stack

- **Python 3**
- **Tkinter** — GUI
- **SQLite3** — Local database for users, rooms, messages, notifications
- **Pillow (PIL)** — Image processing
- **cryptography (Fernet)** — Symmetric encryption

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/securechat.git
cd securechat
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the application
```bash
python advanced_chat_app.py
```

### 4. Create an account
- On first launch, click the **Register** tab
- Enter a username and password, then create your account
- Switch to **Sign In** and log in with the same credentials

---

## 📂 Generated Files (not committed)

| File | Purpose |
|---|---|
| `chat_app.db` | SQLite database storing users, rooms, messages, notifications |
| `chat_secret.key` | Local Fernet encryption key — generated automatically on first run |

These are excluded via `.gitignore` since they contain user data and secrets.

---

## ⚠️ Notes & Limitations

- This app runs locally and uses a polling mechanism (every ~2 seconds) to simulate live updates — not true real-time networking.
- Encryption is **symmetric, local encryption-at-rest** (a single key encrypts/decrypts all messages), not full end-to-end encryption between distinct users with separate keys.
- Intended as a learning/demo project showcasing GUI development, database integration, multithreading, and basic security practices.

---

## 🔮 Future Improvements

- WebSocket-based real-time messaging between multiple clients
- Per-user encryption keys for true end-to-end encryption
- Typing indicators and read receipts
- Profile pictures / avatars
- Dark/light theme toggle

---

## 📄 License

This project is open source and available for learning purposes.
=======
# OIBSIP_Python_Task1
"Advanced Python Chat Application with GUI, encryption, and multimedia sharing"

