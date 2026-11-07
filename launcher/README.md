# Docmost Backup Launcher (Direct API + Secure Credentials)

**One-click backup. No Pi setup. No SSH. No rsync. Passwords in Windows Credential Manager.**

## Security: Where Your Password Goes

| What | Where | Protection |
|------|-------|------------|
| Docmost URL, Email, Backup folder, Retention | `%APPDATA%\DocmostBackup\config.json` | User-only ACL (icacls) |
| **Docmost Password** | **Windows Credential Manager** (Credential Locker) | **Encrypted, user-isolated, DPAPI** |

**The password is NEVER written to any file.** It's stored in Windows' built-in secure vault — same place browsers and Outlook store passwords.

### How It Works

1. **First run**: You enter password → stored via `keyring` → Windows Credential Manager
2. **Subsequent runs**: Password retrieved from Credential Manager automatically
3. **Reconfigure**: Delete `%APPDATA%\DocmostBackup\config.json` and run again

### Windows Credential Manager

Your password appears here (run `control keymgr.dll`):
```
Windows Credentials
└── DocmostBackup
    └── you@example.com  →  ********
```

---

## Quick Start

### Prerequisites (Windows)
- **Python 3.8+** — [python.org](https://python.org) (check "Add to PATH")
- **7-Zip** — `winget install 7zip.7zip`
- **Network access** to Docmost (e.g., `http://192.168.1.100:3000` on LAN)

### Run
1. Copy `launcher` folder anywhere (e.g., `C:\DocmostBackup\launcher\`)
2. **Double-click** `run-backup.bat`
3. First run: Enter settings → password stored securely
4. Subsequent runs: Progress bar → done
5. Open `C:\Users\You\DocmostBackup\docmost-backup-YYYYMMDD-HHMMSS` in Obsidian

---

## What Happens (Direct from Windows)

| Step | API Call | Result |
|------|----------|--------|
| 1 | `POST /api/auth/login` | Session cookie (email + password from Credential Manager) |
| 2 | `POST /api/spaces` | List all spaces |
| 3 | `POST /api/spaces/export` | Streams ZIP (markdown + images + attachments) |
| 4 | 7-Zip validation | Integrity check + SHA256 |
| 5 | Extract to `docmost-backup-<timestamp>/<space>/` | Obsidian-ready |

**No Pi script. No SSH. No rsync. No Pi config.**

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Python not found" | Install Python from python.org; check "Add to PATH" |
| "requests/keyring not installed" | Auto-installed on first run; or `pip install requests keyring` |
| "Connection refused" | Check Docmost URL/IP; ensure Windows reaches Pi on port 3000 |
| "Login failed" | Verify email/password; try in browser first |
| "7z not recognized" | `winget install 7zip.7zip` and restart terminal |
| "ZIP validation failed" | Re-run; if persistent, check Docmost logs on server |
| "keyring not available" | Password prompted each run; install: `pip install keyring` |

---

## Files

```
launcher/
├── docmost_backup.py    # Main launcher (Python, secure credentials)
├── run-backup.bat       # Double-click this!
└── README.md            # This file
```

---

## Why Credential Manager?

| Storage Method | Security | Persistence |
|----------------|----------|-------------|
| Plain text file | ❌ Anyone with file access | ✅ |
| Config file (user ACL) | ⚠️ Admin/other users can read | ✅ |
| **Windows Credential Manager** | ✅ **Encrypted (DPAPI), user-isolated** | ✅ |
| Environment variable | ⚠️ Visible in process list | ❌ Session only |

**Windows Credential Manager** uses DPAPI (Data Protection API) — encryption tied to your user account. Even if someone copies the credential blob, they can't decrypt it without your login.

---

## Reconfiguring

To change settings:
```powershell
# Delete config (password stays in Credential Manager)
del "%APPDATA%\DocmostBackup\config.json"

# Or fully reset (removes password too)
del "%APPDATA%\DocmostBackup\config.json"
# Then run: control keymgr.dll → Windows Credentials → Remove "DocmostBackup"
```

---

## Network Requirements

Your Windows machine must reach Docmost directly:
- Same LAN/WiFi as the Pi
- Or VPN to Pi's network
- Or port forwarding if remote

**Test:** Open `http://<pi-ip>:3000` in browser on Windows → should load Docmost.

---

## License

MIT License — Use freely, adapt as needed.