# Docmost Backup

**A simple, cross-platform backup tool for your Docmost notes and knowledge base.**

Download all your Docmost spaces, pages, and images as Markdown files, ready to use with [Obsidian](https://obsidian.md/) or any other Markdown-compatible note-taking application.

Works on **Windows, macOS, and Linux**.

---

## 📌 Overview

Docmost Backup connects to your self-hosted Docmost instance and exports your content into an organized local backup.

-   **Complete backups** – Download all your spaces, pages, and associated images.
-   **Markdown format** – Your notes are saved as `.md` files, making them easy to browse, edit, or import elsewhere.
-   **Organized structure** – Each Docmost space gets its own folder.
-   **Secure credentials** – Your password is stored in your operating system's secure keychain, never in a plain-text file.
-   **Cross-platform** – Works on Windows, macOS, and Linux.
-   **Simple CLI** – Configure, test, and run backups using straightforward commands.

> **TL;DR:** Connect to Docmost, run one command, and get a local copy of your notes.

---

## ⚠️ Important Notice

This project was developed entirely using **Claude Code** (primarily Claude Opus 5.5) for my personal use. I'm sharing it publicly in case someone else finds it useful.

This software is provided **as-is**, without warranties, guarantees, or dedicated support. Use it at your own risk.

---

## 📋 Prerequisites

You'll need the following installed on your computer.

### 1\. A self-hosted Docmost instance

Follow the official [Docmost installation instructions](https://docmost.com/docs/installation).

### 2\. Python 3.8+

-   **Windows:** Download from [python.org](https://www.python.org/downloads/). Make sure to check **Add Python to PATH** during installation.
-   **macOS:** `brew install python` or download from [python.org](https://www.python.org/downloads/).
-   **Linux:** `sudo apt install python3 python3-pip` (or your distribution's equivalent).

### 3\. 7-Zip

Required for extracting and processing the backup.

-   **Windows:** `winget install 7zip.7zip` or download from [7-zip.org](https://www.7-zip.org/).
-   **macOS:** `brew install p7zip`.
-   **Linux:** `sudo apt install p7zip-full`.

---

## 🚀 Quick Start

### Step 1: Download the Code

Choose whichever method you're most comfortable with.

**Option A: Download ZIP (easiest)**

1.  Click **Code → Download ZIP** on this GitHub page.
2.  Extract the downloaded ZIP file.
3.  Open the `docmost-backup` folder containing the project files.

**Option B: Clone with Git**

```bash
git clone https://github.com/YOUR_USERNAME/docmost-backup.git
cd docmost-backup/docmost-backup
```

### Step 2: Run or Install

There are two ways to use Docmost Backup.

#### Option A: Run Directly with Python

No installation required. However, you'll need to open a terminal in the script's directory whenever you want to run it.

1.  Open a terminal in the folder containing `docmost_backup.py`.
2.  Run the appropriate command:

**Windows (PowerShell / Command Prompt):**

```powershell
python docmost_backup.py
```

**macOS / Linux (Terminal):**

```bash
python3 docmost_backup.py
```

#### Option B: Install with Pip (Recommended)

Install the tool once, then run it from any terminal window, regardless of your current directory.

1.  Open a terminal in the folder containing both `docmost_backup.py` and `pyproject.toml`.
2.  Install the package:

```bash
pip install .
```

3.  Once installed, you can run the tool from anywhere:

```bash
docmost-backup
```

### Step 3: Configure and Run Your First Backup

You can start with:  

```bash
docmost backup run
```

On your first run, you'll be prompted to enter:

-   **Docmost URL** – The address of your Docmost instance.
-   **Email** – Your Docmost login email.
-   **Password** – Your Docmost account password.
-   **Backup folder** – Where you'd like your backups saved.

Your password is securely stored in your operating system's keychain (Windows Credential Manager, macOS Keychain, or Linux Secret Service).

**It is never stored in a plain-text configuration file.**

Once configured, simply run  **`docmost-backup run`** every time you want to backup your Docmost notes.

## 💻 Commands Cheat Sheet

| Command | Description |
| --- | --- |
| `docmost-backup run` | Run a backup (main command) |
| `docmost-backup config` | Change settings (URL, email, backup folder) |
| `docmost-backup test` | Test your connection without starting a backup |
| `docmost-backup spaces` | List all spaces in your Docmost instance |
| `docmost-backup version` | Display the installed version |
| `docmost-backup reset` | Delete all settings and stored credentials |

---

## 📁 Where to Find Your Backup

Once the backup finishes, you'll see a confirmation similar to this:

```text
+ Done
Location: C:\Users\You\DocmostBackup\docmost-backup-20250115-143022
```

Open the specified folder to find your backup.

The exported content is organized into individual space folders containing Markdown files and associated images.

You can open these files directly in Obsidian or any other application that supports Markdown.

---

## 🔧 Advanced Usage

### Running Without Installing Dependencies

If you're running the script in an automated environment, such as a custom script, GitHub Actions, or Docker, you can use:

```bash
python docmost_backup.py --no-deps run
```

This assumes the required dependencies are already available in your Python environment.

---

## 🔐 Where Is My Data Stored?

Docmost Backup keeps your configuration and credentials separate.

| Data | Storage Location | Security |
| --- | --- | --- |
| Docmost URL | Configuration file | User-only permissions |
| Email | Configuration file | User-only permissions |
| Backup folder | Configuration file | User-only permissions |
| **Password** | **Operating system keychain** | **Encrypted secure storage** |

### Configuration File Locations

-   **Windows:** `%APPDATA%\DocmostBackup\config.json`
-   **macOS / Linux:** `~/.config/DocmostBackup/config.json`

### Password Storage

Your password is stored in your operating system's secure credential vault:

-   **Windows:** Credential Manager
-   **macOS:** Keychain
-   **Linux:** Secret Service

**Your password is never written to the configuration file or stored as plain text on disk.**

This uses the same secure storage mechanism that applications and browsers use for saved credentials.

### Removing Your Credentials

To remove your saved settings and password, run:

```bash
docmost-backup reset
```

Alternatively, you can open your operating system's credential manager and remove the entry named `DocmostBackup`.

---

## 🌐 Network Requirements

Your computer must be able to connect directly to your Docmost server.

Supported connection methods include:

-   **Local network (LAN/Wi-Fi):** For example, `http://192.168.1.50:3000`.
-   **VPN:** If your Docmost server is hosted on a remote private network.
-   **Port forwarding:** For remote access (HTTPS is strongly recommended).

### Test Your Connection

Open your Docmost URL in a web browser.

For example:

```text
http://your-docmost-ip:3000
```

If you can see the Docmost login page, your server is reachable from your computer.

You can also test the connection using:

```bash
docmost-backup test
```

---

## 🛠️ Troubleshooting

| Problem | Possible Solution |
| --- | --- |
| `python` not found | Reinstall Python and make sure **Add Python to PATH** is enabled (Windows). |
| `requests` / `keyring` errors | Install the missing dependencies manually: `pip install requests keyring`. |
| `7z` not found | Install 7-Zip. See [Prerequisites](#-prerequisites). |
| Connection refused / timeout | Check your Docmost URL and ensure your computer can reach the server through your LAN, VPN, or reverse proxy. |
| Login failed | Verify your email and password by logging into Docmost through your browser. |
| ZIP validation failed | Try running the backup again. If the problem persists, check your Docmost server logs. |

### Still Having Problems?

1.  Run `docmost-backup test` to diagnose connection issues.
2.  Check the troubleshooting table above.
3.  If the issue persists, open a GitHub issue and include the error message.

---

## 📄 License

This project is licensed under the **MIT License**.

Free to use, modify, and share.

---

## 🙏 A Final Note

This is a personal project that I'm sharing with the community in the hope that it helps someone else keep a local copy of their Docmost knowledge base.

If you find it useful, feel free to use it, modify it, or contribute.

**Happy backing up!**