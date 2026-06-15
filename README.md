# 💬 SecureChat — Advanced Python Chat Application

---

## 🎯 Objective

Build a fully functional desktop chat application using Python and Tkinter, featuring user authentication, multiple chat rooms, multimedia sharing, message history, notifications, emoji support, and AES message encryption stored in a local SQLite database.

---

## ✨ Features Implemented

### 1. User Authentication
- Register and login with SHA-256 hashed passwords
- No plaintext password storage at any point
- Credentials stored securely in local SQLite database

### 2. Multiple Chat Rooms
- Default channels: General, Technology, Random, Gaming
- Create custom rooms dynamically from inside the app
- Each room maintains its own independent message history

### 3. Multimedia Sharing
- Send images with auto-generated thumbnails displayed in chat
- File attachment support for sharing documents
- Media encrypted before storage using Fernet AES

### 4. Message History
- All messages persist in a local SQLite database (chat_app.db)
- History reloads per room on every session start
- Keyword search across any room's full message history

### 5. In-App Notifications
- Popup alerts for new messages
- Notification log accessible via the bell icon
- All notifications stored and retrievable in the database

### 6. Emoji Support
- Built-in emoji picker panel inside the chat window
- Click to insert emoji at cursor position in message input

### 7. Encryption at Rest
- Messages and media encrypted using Fernet (AES symmetric encryption)
- Auto-generated secret key stored in chat_secret.key on first run
- Toggle encryption on or off per message before sending

---

## 🛠️ Tools and Technologies Used

| Tool / Library | Purpose |
|---|---|
| Python 3.x | Core programming language |
| Tkinter | Desktop GUI framework |
| SQLite3 | Local database for users, rooms, messages |
| Pillow (PIL) | Image processing and thumbnail generation |
| cryptography (Fernet) | AES symmetric encryption for messages and media |
| hashlib (SHA-256) | Secure password hashing |
| threading | Background polling for live message updates |

---

## 📂 File Structure

```
OIBSIP_Python_Task1/
|
|-- advanced_chat_app.py     <- Main application entry point
|-- requirements.txt         <- All Python dependencies
|-- README.md                <- This documentation file
|-- .gitignore               <- Excludes database and key files
|-- assets/
|   └── screenshot.png       <- App screenshot
```

> Generated at runtime (excluded from repo via .gitignore):
> - chat_app.db — SQLite database with all users, rooms, messages
> - chat_secret.key — Auto-generated Fernet encryption key

---

## 🚀 How to Run

### Step 1 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2 — Run the Application

```bash
python advanced_chat_app.py
```

### Step 3 — Create an Account

- On first launch, click the **Register** tab
- Enter a username and password
- Switch to **Sign In** and log in with the same credentials

---

## 📦 Requirements (requirements.txt)

```
Pillow
cryptography
```

> Tkinter and SQLite3 come built-in with Python — no separate install needed.

---

## 🎬 Demo Video

LinkedIn Post: [Insert LinkedIn Post Link Here]

---

## 📋 Steps Performed

1. Designed Tkinter GUI with login, registration, and chat panels
2. Implemented SHA-256 password hashing for secure authentication
3. Set up SQLite3 database schema for users, rooms, messages, notifications
4. Built multi-room architecture with dynamic room creation
5. Integrated Pillow for image thumbnail generation in chat
6. Added Fernet AES encryption for all messages and media at rest
7. Built keyword search across room message history
8. Implemented in-app notification system with bell icon log
9. Added emoji picker with cursor-position insertion
10. Used threading for background polling to simulate live updates

---

## 🏆 Outcome

A fully working secure desktop chat application that demonstrates:
- GUI development with Tkinter
- Database integration with SQLite3
- AES encryption for data security at rest
- Modular Python architecture with clean separation of concerns
- Real-world authentication and session management patterns

---

## ⚠️ Notes

- App uses polling every ~2 seconds to simulate live updates, not true WebSocket networking
- Encryption is symmetric local encryption-at-rest, not full end-to-end per-user encryption
- Intended as a learning and demo project for the OIBSIP internship

---

## 📝 File Naming Convention (As per OIBSIP Guidelines)

YourName_Task1 — e.g., RaviKumar_Task1

---

Submitted as part of the Oasis Infobyte Python Internship — OIBSIP
