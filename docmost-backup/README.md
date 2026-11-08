# Docmost Backup — Run This Folder

This folder contains the backup tool. You only need two files here:

```
docmost-backup/
├── docmost_backup.py    # ← RUN THIS
├── pyproject.toml       # (for pip install)
└── README.md            # (this file)
```

---

## Quick Commands

```bash
# Run backup (main command)
python docmost_backup.py run

# First time? It will ask for:
#   • Docmost URL (e.g., http://192.168.1.50:3000)
#   • Your Docmost email
#   • Your Docmost password (stored securely in OS keychain)

# Other useful commands:
python docmost_backup.py config    # Change settings
python docmost_backup.py test      # Test connection
python docmost_backup.py spaces    # List all spaces
python docmost_backup.py version   # Show version
python docmost_backup.py reset     # Delete all settings + password
```

---

## Install Globally (Optional)

```bash
pip install .
# Then use anywhere: docmost-backup run
```

---

## Automation / CI

```bash
python docmost_backup.py --no-deps run
```

---

## Prerequisites

- **Python 3.8+** (check "Add to PATH" on Windows)
- **7-Zip** (`winget install 7zip.7zip` / `brew install p7zip` / `apt install p7zip-full`)

---

## Where's My Backup?

After running, look for:
```
C:\Users\You\DocmostBackup\docmost-backup-YYYYMMDD-HHMMSS\
```
(Or `~/DocmostBackup/...` on Mac/Linux)

Drag that folder into **Obsidian** → done.

---

## Password Security

Your password goes to your **OS keychain** (Windows Credential Manager / macOS Keychain / Linux Secret Service). **Never written to any file.** See main README for details.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `python` not found | Reinstall Python with "Add to PATH" |
| `requests`/`keyring` missing | `pip install requests keyring` |
| `7z` not found | Install 7-Zip |
| Connection failed | Check URL, VPN, firewall |
| Login failed | Test in browser first |

---

See the main [README.md](../README.md) for full documentation.