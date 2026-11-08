#!/usr/bin/env python3
"""
Docmost Backup Launcher - Direct API with secure credential storage.
Double-click to run. Uses Windows Credential Manager for passwords.
"""

import os
import sys
import json
import time
import getpass
import shutil
import subprocess
import traceback
import argparse
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Try to import keyring for secure credential storage
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# ─── Auto-install dependencies ──────────────────────────────────────
def ensure_deps():
    """Install missing dependencies on first run."""
    if "--no-deps" in sys.argv:
        return
    required = ["requests", "keyring"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing, "--quiet"])
            print("Done.")
        except subprocess.CalledProcessError:
            print(f"Failed. Run manually: pip install {' '.join(missing)}")
            sys.exit(1)

# ─── Configuration ────────────────────────────────────────────────

CONFIG_DIR = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "DocmostBackup"
CONFIG_FILE = CONFIG_DIR / "config.json"
CREDENTIAL_SERVICE = "DocmostBackup"
VERSION = "1.0.0"
SPACES_LIMIT = 100

DEFAULT_CONFIG = {
    "docmost_url": "",
    "docmost_email": "",
    "local_backup_dir": str(Path.home() / "DocmostBackup"),
}

# ─── Secure Credential Storage ────────────────────────────────────

def get_stored_password(email: str) -> Optional[str]:
    if not KEYRING_AVAILABLE:
        return None
    try:
        return keyring.get_password(CREDENTIAL_SERVICE, email)
    except Exception:
        return None

def store_password(email: str, password: str) -> bool:
    if not KEYRING_AVAILABLE:
        return False
    try:
        keyring.set_password(CREDENTIAL_SERVICE, email, password)
        return True
    except Exception:
        return False

def delete_stored_password(email: str) -> bool:
    if not KEYRING_AVAILABLE:
        return False
    try:
        keyring.delete_password(CREDENTIAL_SERVICE, email)
        return True
    except Exception:
        return False

# ─── Configuration Management ────────────────────────────────────

def load_config() -> Optional[Dict[str, Any]]:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
        except Exception as e:
            print(f"[ERROR] Could not load config: {e}")
    return None

def save_config(config: Dict[str, Any]):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    safe_config = {k: v for k, v in config.items() if k != "docmost_password"}

    # On Windows, fix permissions on existing file BEFORE writing
    if os.name == "nt" and CONFIG_FILE.exists():
        try:
            subprocess.run(["icacls", str(CONFIG_FILE), "/inheritance:r", "/grant:r", f"{os.getlogin()}:F"],
                         capture_output=True, check=False)
        except Exception:
            pass

    with open(CONFIG_FILE, "w") as f:
        json.dump(safe_config, f, indent=2)

    if os.name == "nt":
        try:
            # Grant Full control so user can read/write/delete
            subprocess.run(["icacls", str(CONFIG_FILE), "/inheritance:r", "/grant:r", f"{os.getlogin()}:F"],
                         capture_output=True, check=False)
        except Exception:
            pass

# ─── UI Helpers ───────────────────────────────────────────────────

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    WHITE = "\033[97m"

def enable_vt_mode():
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass

# ─── Logo ─────────────────────────────────────────────────────────────

LOGO = r"""
{cyan}{bold}
______ _____ _____ ___  ________ _____ _____  ______  ___  _____  _   ___   _______
|  _  \  _  /  __ \|  \/  |  _  /  ___|_   _| | ___ \/ _ \/  __ \| | / / | | | ___ \
| | | | | | | /  \/| .  . | | | \ `--.  | |   | |_/ / /_\ \ /  \/| |/ /| | | | |_/ /
| | | | | | | |    | |\/| | | | |`--. \ | |   | ___ \  _  | |    |    \| | | |  __/
| |/ /\ \_/ / \__/\| |  | \ \_/ /\__/ / | |   | |_/ / | | | \__/\| |\  \ |_| | |
|___/  \___/ \____/\_|  |_/\___/\____/  \_/   \____/\_| |_/\____/\_| \_/\___/\_|

                            v{version}

A simple and reliable way to back up your Docmost spaces and pages directly from your PC.

Run a docmost-backup with a command to get started!
{reset}
""".format(cyan=Colors.CYAN, bold=Colors.BOLD, reset=Colors.RESET, version=VERSION)

def print_logo():
    print(LOGO)


def print_header(text: str):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 64}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}  {text}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 64}{Colors.RESET}\n")

def print_step(text: str):
    print(f"{Colors.BLUE}> {text}{Colors.RESET}")

def print_success(text: str):
    print(f"{Colors.GREEN}+ {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}! {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}x {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.GRAY}  {text}{Colors.RESET}")

def _get_password_with_asterisks(prompt_text: str) -> str:
    """Read password showing asterisks instead of nothing."""
    import sys
    sys.stdout.write(prompt_text)
    sys.stdout.flush()

    password = []
    try:
        if os.name == "nt":
            import msvcrt
            while True:
                ch = msvcrt.getwch()
                if ch == "\r" or ch == "\n":
                    break
                elif ch == "\b":  # Backspace
                    if password:
                        password.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ch == "\x03":  # Ctrl+C
                    raise KeyboardInterrupt
                else:
                    password.append(ch)
                    sys.stdout.write("*")
                    sys.stdout.flush()
        else:
            import termios
            import tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    ch = sys.stdin.read(1)
                    if ch == "\r" or ch == "\n":
                        break
                    elif ch == "\x7f" or ch == "\b":  # Backspace
                        if password:
                            password.pop()
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                    elif ch == "\x03":  # Ctrl+C
                        raise KeyboardInterrupt
                    else:
                        password.append(ch)
                        sys.stdout.write("*")
                        sys.stdout.flush()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except KeyboardInterrupt:
        print("\n")
        sys.exit(1)

    print()  # Newline after password entry
    return "".join(password)


def prompt(text: str, default: str = "", secret: bool = False) -> str:
    if default:
        display = f"{text} [{Colors.GRAY}{default}{Colors.RESET}]: "
    else:
        display = f"{text}: "

    while True:
        try:
            if secret:
                value = _get_password_with_asterisks(display)
            else:
                value = input(display).strip()

            if not value and default:
                return default
            if value:
                return value
            print_error("This field is required.")
        except KeyboardInterrupt:
            print("\n")
            sys.exit(1)

def confirm(text: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        try:
            response = input(f"{text}{suffix}: ").strip().lower()
            if not response:
                return default
            if response in ("y", "yes"):
                return True
            if response in ("n", "no"):
                return False
            print_error("Please enter 'y' or 'n'.")
        except KeyboardInterrupt:
            print("\n")
            sys.exit(1)

# ─── Space Status Tracker ─────────────────────────────────────────

class SpaceStatus:
    PENDING = "pending"
    CONNECTING = "connecting"
    DOWNLOADING = "downloading"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    COMPLETE = "complete"
    FAILED = "failed"

    ICONS = {
        PENDING: f"{Colors.GRAY}o{Colors.RESET}",
        CONNECTING: f"{Colors.BLUE}@{Colors.RESET}",
        DOWNLOADING: f"{Colors.BLUE}@>{Colors.RESET}",
        VALIDATING: f"{Colors.YELLOW}?{Colors.RESET}",
        EXTRACTING: f"{Colors.YELLOW}#{Colors.RESET}",
        COMPLETE: f"{Colors.GREEN}+{Colors.RESET}",
        FAILED: f"{Colors.RED}x{Colors.RESET}",
    }

    LABELS = {
        PENDING: "waiting",
        CONNECTING: "connecting",
        DOWNLOADING: "downloading",
        VALIDATING: "validating",
        EXTRACTING: "extracting",
        COMPLETE: "complete",
        FAILED: "failed",
    }

    def __init__(self, name: str):
        self.name = name
        self.state = self.PENDING
        self.detail = ""
        self.bytes_downloaded = 0
        self.total_bytes = 0

    def set_state(self, state: str, detail: str = ""):
        self.state = state
        self.detail = detail

    def update_download(self, downloaded: int, total: int):
        self.bytes_downloaded = downloaded
        self.total_bytes = total

    def render(self, width: int = 60) -> str:
        icon = self.ICONS.get(self.state, "?")
        label = self.LABELS.get(self.state, self.state)
        name = self.name[:30] + "…" if len(self.name) > 30 else self.name
        name_padded = name.ljust(32)

        if self.state == self.DOWNLOADING and self.total_bytes > 0:
            pct = self.bytes_downloaded / self.total_bytes * 100
            bar_width = 20
            filled = int(bar_width * pct / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            mb = self.bytes_downloaded / 1024 / 1024
            total_mb = self.total_bytes / 1024 / 1024
            detail = f"{bar} {pct:5.1f}% ({mb:.1f}/{total_mb:.1f} MB)"
        elif self.detail:
            detail = self.detail
        else:
            detail = label

        # \033[K clears from cursor to end of line (prevents leftover chars from longer previous lines)
        return f"  {icon} {Colors.WHITE}{name_padded}{Colors.RESET} {Colors.GRAY}{detail}{Colors.RESET}\033[K"

# ─── Progress Display ─────────────────────────────────────────────

class ProgressDisplay:
    def __init__(self, spaces: List[str]):
        self.spaces = [SpaceStatus(name) for name in spaces]
        self.current_space_idx = 0
        self.overall_start = time.time()
        self._visible = False
        self._lines_rendered = 0

    def start_space(self, idx: int):
        self.current_space_idx = idx
        if idx > 0:
            self.spaces[idx - 1].set_state(SpaceStatus.COMPLETE)
        self.spaces[idx].set_state(SpaceStatus.CONNECTING)
        self._render()

    def set_downloading(self, idx: int):
        self.spaces[idx].set_state(SpaceStatus.DOWNLOADING)
        self._render()

    def update_download(self, idx: int, downloaded: int, total: int):
        self.spaces[idx].update_download(downloaded, total)
        self._render()

    def set_validating(self, idx: int):
        self.spaces[idx].set_state(SpaceStatus.VALIDATING)
        self._render()

    def set_extracting(self, idx: int):
        self.spaces[idx].set_state(SpaceStatus.EXTRACTING)
        self._render()

    def set_complete(self, idx: int):
        self.spaces[idx].set_state(SpaceStatus.COMPLETE)
        self._render()

    def set_failed(self, idx: int, reason: str = ""):
        self.spaces[idx].set_state(SpaceStatus.FAILED, reason)
        self._render()

    def _render(self):
        # Move cursor up to overwrite previous render
        if self._visible:
            sys.stdout.write(f"\033[{self._lines_rendered}A")

        lines = []
        for i, space in enumerate(self.spaces):
            lines.append(space.render())

        self._lines_rendered = len(lines)
        output = "\n".join(lines) + "\n"
        sys.stdout.write(output)
        sys.stdout.flush()
        self._visible = True

    def finish(self):
        # Ensure all complete
        for space in self.spaces:
            if space.state not in (SpaceStatus.COMPLETE, SpaceStatus.FAILED):
                space.set_state(SpaceStatus.COMPLETE)
        self._render()
        print()  # Final newline

# ─── 7-Zip Helpers ────────────────────────────────────────────────

def find_sevenz() -> Optional[str]:
    """Find 7z executable."""
    candidates = [
        "7z",
        "7za",
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for c in candidates:
        if shutil.which(c):
            return c
        if os.path.isfile(c):
            return c
    return None

SEVENZ = find_sevenz()

def validate_zip(zip_path: Path) -> bool:
    if not SEVENZ:
        return True
    if not zip_path.exists():
        return False
    try:
        result = subprocess.run([SEVENZ, "t", str(zip_path)], capture_output=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False

def extract_zip(zip_path: Path, dest_dir: Path) -> bool:
    if not SEVENZ:
        return False
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([SEVENZ, "x", str(zip_path), f"-o{dest_dir}", "-y"],
                               capture_output=True, timeout=120)
        return result.returncode == 0
    except Exception:
        return False

# ─── Docmost API Client ───────────────────────────────────────────

class DocmostClient:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"docmost-backup/{VERSION}",
            "Accept": "application/json",
            # Do NOT set Content-Type here - let individual requests set it
            # (JSON for API calls, multipart/form-data for file uploads)
        })
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self._auth_token: Optional[str] = None

    def login(self) -> bool:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"email": self.email, "password": self.password},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                print_error(f"Login failed: {data.get('message', 'Unknown error')}")
                return False
            for cookie in self.session.cookies:
                if cookie.name == "authToken":
                    self._auth_token = cookie.value
                    break
            if not self._auth_token:
                print_warning("No authToken cookie found in response")
            return True
        except requests.RequestException as e:
            print_error(f"Login failed: {e}")
            return False
        except Exception as e:
            print_error(f"Login unexpected error: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._auth_token:
            headers["Cookie"] = f"authToken={self._auth_token}"
        return headers

    def get_spaces(self) -> List[Dict]:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/spaces",
                json={"limit": SPACES_LIMIT, "query": ""},
                headers=self._get_headers(),
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                if "data" in data and isinstance(data["data"], dict) and "items" in data["data"]:
                    return data["data"]["items"]
                elif "data" in data and isinstance(data["data"], list):
                    return data["data"]
            print_warning(f"Unexpected spaces response format: {type(data)}")
            return []
        except requests.RequestException as e:
            print_error(f"Failed to fetch spaces: {e}")
            return []
        except Exception as e:
            print_error(f"Spaces unexpected error: {e}")
            return []

    def find_space_by_name(self, name: str) -> Optional[str]:
        """Find a space by name (case-insensitive) and return its ID."""
        spaces = self.get_spaces()
        for space in spaces:
            if space.get("name", "").lower() == name.lower():
                return space.get("id")
        return None

    def export_space(self, space_id: str, display: ProgressDisplay, idx: int) -> Optional[bytes]:
        payload = {
            "spaceId": space_id,
            "format": "markdown",
            "includeAttachments": True
        }

        try:
            display.set_downloading(idx)
            resp = self.session.post(
                f"{self.base_url}/api/spaces/export",
                json=payload,
                headers=self._get_headers(),
                timeout=600,
                stream=True
            )
            resp.raise_for_status()

            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunks = []

            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        display.update_download(idx, downloaded, total_size)
                    else:
                        display.spaces[idx].update_download(downloaded, 0)
                        display._render()

            content = b"".join(chunks)
            return content

        except requests.RequestException as e:
            print_error(f"Export failed: {e}")
            return None
        except Exception as e:
            print_error(f"Export unexpected error: {e}")
            return None

    def create_space(self, name: str, slug: str = None, description: str = "") -> Optional[str]:
        """Create a new space and return its ID."""
        if slug is None:
            # Generate slug from name
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

        payload = {
            "name": name,
            "slug": slug,
            "description": description,
        }

        try:
            print_info(f"  Creating space: name='{name}', slug='{slug}'")
            resp = self.session.post(
                f"{self.base_url}/api/spaces/create",
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            print_info(f"  Response status: {resp.status_code}")
            print_info(f"  Response body: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()

            # Handle different response formats
            if isinstance(data, dict):
                if data.get("success") and "data" in data:
                    return data["data"].get("id")
                elif "id" in data:
                    return data["id"]
            print_error(f"Unexpected create space response: {data}")
            return None

        except requests.RequestException as e:
            print_error(f"Failed to create space: {e}")
            if hasattr(e, "response") and e.response is not None:
                print_error(f"  Status: {e.response.status_code}")
                print_error(f"  Response: {e.response.text[:500]}")
                try:
                    err_data = e.response.json()
                    if "message" in err_data:
                        print_error(f"  Message: {err_data['message']}")
                except Exception:
                    pass
            return None
        except Exception as e:
            print_error(f"Create space unexpected error: {e}")
            return None

    def import_pages(self, space_id: str, space_folder: Path, display: ProgressDisplay = None, idx: int = 0) -> bool:
        """Import all .md files from a space folder into an existing space."""
        # Find all .md files in the space folder
        md_files = list(space_folder.rglob("*.md"))
        if not md_files:
            print_warning(f"No markdown files found in {space_folder}")
            return True  # Nothing to import, but not a failure

        print_info(f"  Found {len(md_files)} markdown file(s) to import")

        success_count = 0
        for md_file in md_files:
            try:
                if display:
                    display.set_downloading(idx)

                relative_path = md_file.relative_to(space_folder)
                print_info(f"  Importing: {relative_path}")

                with open(md_file, "rb") as f:
                    # Include spaceId as a form field in the multipart body
                    # (not as data=, which can cause content-type issues)
                    files = {
                        "spaceId": (None, space_id),
                        "file": (md_file.name, f, "application/octet-stream"),
                    }
                    # Remove Content-Type header for multipart upload
                    headers = {k: v for k, v in self._get_headers().items() if k.lower() != "content-type"}
                    # Add Referer header like the web UI
                    headers["Referer"] = f"{self.base_url}/s/{space_id}"

                    print_info(f"    POST {self.base_url}/api/pages/import")
                    resp = self.session.post(
                        f"{self.base_url}/api/pages/import",
                        files=files,
                        headers=headers,
                        timeout=120
                    )

                print_info(f"    Response status: {resp.status_code}")
                print_info(f"    Response body: {resp.text[:500]}")
                resp.raise_for_status()
                resp_data = resp.json()

                if isinstance(resp_data, dict) and resp_data.get("success"):
                    success_count += 1
                elif isinstance(resp_data, dict) and resp_data.get("message"):
                    print_error(f"    Import failed: {resp_data['message']}")
                else:
                    # Assume success if no error message
                    success_count += 1

            except requests.RequestException as e:
                print_error(f"    Import failed for {md_file.name}: {e}")
                if hasattr(e, "response") and e.response is not None:
                    print_error(f"    Status: {e.response.status_code}")
                    print_error(f"    Response: {e.response.text[:500]}")
                    try:
                        err_data = e.response.json()
                        if "message" in err_data:
                            print_error(f"    {err_data['message']}")
                    except Exception:
                        pass
            except Exception as e:
                print_error(f"    Import unexpected error for {md_file.name}: {e}")

        if display:
            display.set_complete(idx)

        if success_count == len(md_files):
            print_success(f"  Imported {success_count}/{len(md_files)} page(s) successfully")
            return True
        elif success_count > 0:
            print_warning(f"  Partially imported: {success_count}/{len(md_files)} page(s)")
            return True  # Partial success
        else:
            print_error(f"  Failed to import any pages")
            return False

# ─── Backup Operations ────────────────────────────────────────────

def run_backup(config: Dict[str, Any], password: str) -> bool:
    print_header("Docmost Backup")
    print_info(f"Source: {config['docmost_url']}")
    print_info(f"Destination: {config['local_backup_dir']}\n")

    client = DocmostClient(config["docmost_url"], config["docmost_email"], password)

    print_step("Connecting to Docmost...")
    if not client.login():
        return False

    print_step("Fetching spaces...")
    spaces = client.get_spaces()
    if not spaces:
        print_warning("No spaces found")
        return True

    # Let user select which spaces to back up
    selected_spaces = select_spaces_to_backup(spaces)
    if not selected_spaces:
        print_info("No spaces selected. Cancelled.")
        return False

    space_names = [s.get("name", s["id"]) for s in selected_spaces]
    print_info(f"Backing up {len(selected_spaces)} space(s)\n")

    # Use selected_spaces for the summary
    total_spaces = len(selected_spaces)

    local_dir = Path(config["local_backup_dir"])
    local_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_folder = local_dir / f"docmost-backup-{timestamp}"
    backup_folder.mkdir(parents=True, exist_ok=True)

    display = ProgressDisplay(space_names)
    success_count = 0
    failed_spaces = []

    for i, space in enumerate(selected_spaces):
        space_id = space["id"]
        space_name = space.get("name", space_id)
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in space_name)

        display.start_space(i)

        zip_content = client.export_space(space_id, display, i)
        if not zip_content:
            display.set_failed(i, "download failed")
            failed_spaces.append(space_name)
            continue

        # Save temp ZIP
        zip_name = f"backup-{safe_name}-{timestamp}.zip"
        tmp_path = backup_folder / f".{zip_name}.tmp"

        try:
            tmp_path.write_bytes(zip_content)
        except Exception as e:
            display.set_failed(i, "write failed")
            failed_spaces.append(space_name)
            continue

        display.set_validating(i)
        if not validate_zip(tmp_path):
            display.set_failed(i, "validation failed")
            tmp_path.unlink(missing_ok=True)
            failed_spaces.append(space_name)
            continue

        display.set_extracting(i)
        space_dir = backup_folder / safe_name
        if not extract_zip(tmp_path, space_dir):
            display.set_failed(i, "extraction failed")
            failed_spaces.append(space_name)
            continue

        # Remove temp ZIP
        tmp_path.unlink(missing_ok=True)

        display.set_complete(i)
        success_count += 1

    display.finish()

    # Summary
    print()
    if success_count > 0:
        print_success(f"Backup completed: {success_count}/{total_spaces} spaces")
    else:
        print_error("Backup failed: no spaces backed up")
        return False

    if failed_spaces:
        print_warning(f"Failed: {', '.join(failed_spaces)}")

    print_info(f"Location: {backup_folder}")
    for space_dir in sorted(backup_folder.iterdir()):
        if space_dir.is_dir():
            md_count = len(list(space_dir.rglob("*.md")))
            print(f"  {Colors.GREEN}+{Colors.RESET} {space_dir.name}: {md_count} markdown files")

    return True


def run_first_time_setup() -> Dict[str, Any]:
    """Run first-time setup wizard."""
    print_header("Docmost Backup - First Time Setup")
    print_info("Configures direct connection to Docmost. Password stored securely in Windows Credential Manager.\n")

    config = DEFAULT_CONFIG.copy()

    print(f"{Colors.BOLD}Docmost Connection{Colors.RESET}")
    config["docmost_url"] = prompt("Docmost URL (e.g., http://192.168.1.100:3000)", secret=False).rstrip("/")
    config["docmost_email"] = prompt("Docmost Email", secret=False)
    password = prompt("Docmost Password", secret=True)
    print()

    print(f"{Colors.BOLD}Local Storage{Colors.RESET}")
    default_local = str(Path.home() / "DocmostBackup")
    config["local_backup_dir"] = prompt("Local backup folder", default=default_local, secret=False)
    print()

    if store_password(config["docmost_email"], password):
        print_success("Password stored securely in Windows Credential Manager")
    else:
        print_warning("Could not store password in Credential Manager (keyring not available).")
        print_info("Password will be prompted each run, or you can install: pip install keyring")

    if confirm("Test connection to Docmost now?", default=True):
        test_client = DocmostClient(config["docmost_url"], config["docmost_email"], password)
        if test_client.login():
            print_success("Connection successful!")
        else:
            print_warning("Connection test failed. Check URL and credentials.")

    save_config(config)
    print_success(f"\nConfiguration saved to {CONFIG_FILE}")
    print_info("Password is NOT in config file — stored in Windows Credential Manager only.")
    return config


# ─── Command Functions ────────────────────────────────────────────

def cmd_run(config: Dict[str, Any], password: Optional[str] = None) -> bool:
    """Run the backup."""
    # Check config FIRST
    required = ["docmost_url", "docmost_email", "local_backup_dir"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        print_error("Missing configuration")
        if confirm("Run configuration now?", default=True):
            return cmd_config({})
        return False

    # Config exists, now handle password
    email = config.get("docmost_email", "")
    if password is None:
        password = get_stored_password(email) if email else None

    if not password:
        print_warning("No stored password found (or keyring unavailable).")
        password = prompt("Docmost Password", secret=True)
        if email and confirm("Store password securely in Windows Credential Manager?", default=True):
            store_password(email, password)

    return run_backup(config, password)


def cmd_config(_config: Dict[str, Any], _password: Optional[str] = None) -> bool:
    """Run first-time setup / reconfigure."""
    config = run_first_time_setup()
    print()
    if confirm("Run backup now?", default=True):
        return cmd_run(config)
    print_info("Configuration complete. Run 'docmost-backup run' to start a backup.")
    return True


def cmd_test(config: Dict[str, Any], _password: Optional[str] = None) -> bool:
    """Test connection to Docmost."""
    email = config.get("docmost_email", "")
    password = get_stored_password(email) if email else None

    if not password:
        password = prompt("Docmost Password", secret=True)

    print_step("Testing connection to Docmost...")
    client = DocmostClient(config["docmost_url"], config["docmost_email"], password)
    if client.login():
        print_success("Connection successful!")
        return True
    else:
        print_error("Connection failed. Check URL and credentials.")
        return False


def cmd_version(_config: Dict[str, Any], _password: Optional[str] = None) -> bool:
    """Show version info."""
    print(f"docmost-backup v{VERSION}")
    print(f"Config: {CONFIG_FILE}")
    print(f"Credential Manager: {CREDENTIAL_SERVICE}")
    return True


def cmd_spaces(config: Dict[str, Any], _password: Optional[str] = None) -> bool:
    """List available spaces."""
    email = config.get("docmost_email", "")
    password = get_stored_password(email) if email else None

    if not password:
        password = prompt("Docmost Password", secret=True)

    print_step("Fetching spaces...")
    client = DocmostClient(config["docmost_url"], config["docmost_email"], password)
    if not client.login():
        return False

    spaces = client.get_spaces()
    if not spaces:
        print_warning("No spaces found")
        return True

    print_info(f"Found {len(spaces)} space(s):")
    for s in spaces:
        print(f"  • {s.get('name', s['id'])}  ({Colors.GRAY}{s['id']}{Colors.RESET})")
    return True


def cmd_reset(_config: Dict[str, Any], _password: Optional[str] = None) -> bool:
    """Reset all configuration and credentials."""
    print_warning("This will delete all saved configuration and stored password.")
    if not confirm("Are you sure?", default=False):
        print_info("Cancelled.")
        return True

    CONFIG_FILE.unlink(missing_ok=True)
    email = input("Email to remove from Credential Manager (leave blank to skip): ").strip()
    if email:
        delete_stored_password(email)
        print_success(f"Removed credentials for {email}")
    print_success("Reset complete. Run 'docmost-backup config' to set up again.")
    return True


def cmd_restore(config: Dict[str, Any], _password: Optional[str] = None) -> bool:
    """Restore a space from a local backup folder."""
    # Get path from command line args (stored globally by parser)
    backup_path = getattr(sys, '_restore_path', None)
    space_name = getattr(sys, '_restore_space_name', None)

    # Get backup directory from config
    backup_dir = Path(config.get("local_backup_dir", Path.home() / "DocmostBackup"))

    # If no path provided, scan for available backups
    if not backup_path:
        backup_folders = find_backup_folders(backup_dir)
        if not backup_folders:
            print_error(f"No backup folders found in {backup_dir}")
            print_info("Run a backup first, or specify a path with --path")
            return False

        # Show available backups
        print_header("Available Backups")
        print_info(f"Scanning: {backup_dir}\n")

        for i, folder in enumerate(backup_folders):
            marker = " <- latest" if i == 0 else ""
            mtime = datetime.fromtimestamp(folder.stat().st_mtime)
            print(f"  [{i + 1}] {folder.name}  ({Colors.GRAY}{mtime.strftime('%Y-%m-%d %H:%M')}{Colors.RESET}){marker}")

        print()
        print_info("Press Enter for latest [1], or type number to select:")
        choice = input("Selection: ").strip()

        if not choice:
            idx = 0  # Default to most recent
        else:
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(backup_folders):
                    print_error("Invalid selection")
                    return False
            except ValueError:
                print_error("Invalid selection")
                return False

        backup_folder = backup_folders[idx]
        backup_path = str(backup_folder)
    else:
        backup_folder = Path(backup_path)
        if not backup_folder.exists():
            print_error(f"Backup folder not found: {backup_path}")
            return False

    # Scan for spaces in the selected backup folder
    space_folders = find_space_folders(backup_folder)
    if not space_folders:
        print_error(f"No spaces found in backup folder: {backup_folder.name}")
        print_info("Backup folder should contain space subdirectories with .md files")
        return False

    # Show available spaces and let user select
    selected_spaces = select_spaces_to_restore(space_folders)
    if not selected_spaces:
        print_info("No spaces selected. Cancelled.")
        return False

    # If no space name provided via CLI, we'll use each folder's name
    # (space_name from CLI is ignored when multiple spaces selected)

    # Get password once
    email = config.get("docmost_email", "")
    password = get_stored_password(email) if email else None

    if not password:
        password = prompt("Docmost Password", secret=True)

    client = DocmostClient(config["docmost_url"], config["docmost_email"], password)

    print_step("Connecting to Docmost...")
    if not client.login():
        return False

    # Restore each selected space
    success_count = 0
    failed_spaces = []

    for space_folder in selected_spaces:
        space_display_name = space_folder.name

        print_header(f"Restoring: {space_display_name}")
        print_info(f"Source: {space_folder}")

        print_step("Checking for existing space in Docmost...")
        # Check if space already exists
        space_id = client.find_space_by_name(space_display_name)
        if space_id:
            print_info(f"Space '{space_display_name}' already exists (ID: {space_id})")
        else:
            print_step("Creating space in Docmost...")
            space_id = client.create_space(space_display_name)
            if not space_id:
                print_error(f"Failed to create space '{space_display_name}'")
                failed_spaces.append(space_display_name)
                continue
            print_success(f"Space created with ID: {space_id}")

        print_step("Importing pages into space...")
        display = ProgressDisplay([space_display_name])
        if client.import_pages(space_id, space_folder, display, 0):
            print_success(f"Space '{space_display_name}' restored successfully!")
            success_count += 1
        else:
            print_error(f"Import failed for {space_display_name}")
            failed_spaces.append(space_display_name)

    # Summary
    print()
    print_header("Restore Summary")
    if success_count:
        print_success(f"Restored: {success_count} space(s)")
    if failed_spaces:
        print_error(f"Failed: {len(failed_spaces)} space(s)")
        for s in failed_spaces:
            print(f"  - {s}")

    return len(failed_spaces) == 0


def find_space_folders(backup_folder: Path) -> List[Path]:
    """Find space subdirectories in a backup folder (folders containing .md files)."""
    if not backup_folder.exists():
        return []
    spaces = []
    for item in backup_folder.iterdir():
        if item.is_dir():
            # Check if folder contains .md files (indicates it's a space)
            md_files = list(item.rglob("*.md"))
            if md_files:
                spaces.append(item)
    return spaces


def select_spaces_to_backup(spaces: List[Dict]) -> List[Dict]:
    """Let user select which spaces to back up. Supports multiple selection."""
    print_header(f"Available Spaces ({len(spaces)} found)")

    for i, space in enumerate(spaces):
        space_name = space.get("name", space["id"])
        print(f"  [{i + 1}] {space_name}")

    print()
    print_info("Select spaces to back up:")
    print_info("  - Press Enter for ALL")
    print_info("  - Type numbers separated by commas (e.g., 1,3,5)")
    print_info("  - Type 'all' for all spaces")
    choice = input("Selection: ").strip().lower()

    if not choice or choice == "all":
        return spaces  # Back up all

    # Parse comma-separated numbers
    try:
        indices = [int(x.strip()) - 1 for x in choice.split(",")]
        selected = []
        for idx in indices:
            if 0 <= idx < len(spaces):
                selected.append(spaces[idx])
            else:
                print_error(f"Invalid selection: {idx + 1} (max: {len(spaces)})")
                return []
        return selected
    except ValueError:
        print_error("Invalid input. Use comma-separated numbers (e.g., 1,3,5)")
        return []


def select_spaces_to_restore(space_folders: List[Path]) -> List[Path]:
    """Let user select which spaces to restore. Supports multiple selection."""
    print_header(f"Spaces in Backup ({len(space_folders)} found)")

    for i, folder in enumerate(space_folders):
        # Count .md files for info
        md_count = len(list(folder.rglob("*.md")))
        print(f"  [{i + 1}] {folder.name}  ({Colors.GRAY}{md_count} markdown files{Colors.RESET})")

    print()
    print_info("Select spaces to restore:")
    print_info("  - Press Enter for ALL")
    print_info("  - Type numbers separated by commas (e.g., 1,3,5)")
    print_info("  - Type 'all' for all spaces")
    choice = input("Selection: ").strip().lower()

    if not choice or choice == "all":
        return space_folders  # Restore all

    # Parse comma-separated numbers
    try:
        indices = [int(x.strip()) - 1 for x in choice.split(",")]
        selected = []
        for idx in indices:
            if 0 <= idx < len(space_folders):
                selected.append(space_folders[idx])
            else:
                print_error(f"Invalid selection: {idx + 1} (max: {len(space_folders)})")
                return []
        return selected
    except ValueError:
        print_error("Invalid input. Use comma-separated numbers (e.g., 1,3,5)")
        return []


def find_backup_folders(backup_dir: Path) -> List[Path]:
    """Find all docmost-backup-* folders in backup directory, sorted newest first."""
    if not backup_dir.exists():
        return []
    folders = []
    for item in backup_dir.iterdir():
        if item.is_dir() and item.name.startswith("docmost-backup-"):
            folders.append(item)
    # Sort by modification time, newest first
    folders.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return folders


# ─── Main Entry Point ─────────────────────────────────────────────

COMMANDS = {
    "run": (cmd_run, "Run backup"),
    "config": (cmd_config, "Configure Docmost connection and backup folder"),
    "test": (cmd_test, "Test connection to Docmost"),
    "spaces": (cmd_spaces, "List available spaces"),
    "version": (cmd_version, "Show version info"),
    "reset": (cmd_reset, "Reset all configuration and credentials"),
    "restore": (cmd_restore, "Restore a space from local backup folder"),
}

class CustomHelpFormatter(argparse.HelpFormatter):
    def format_help(self):
        # Build custom help output (description now in logo)
        lines = []

        # Commands section
        lines.append("Commands:")
        for cmd, (_, desc) in COMMANDS.items():
            lines.append(f"  {cmd:<10} {desc}")
        lines.append("")

        # Examples section
        lines.append("Examples:")
        for cmd in COMMANDS.keys():
            lines.append(f"  docmost-backup {cmd}")
        lines.append("")

        # Options section
        lines.append("options:")
        lines.append("  -h, --help            show this help message and exit")
        lines.append(f"  -v, --version         show program's version number and exit")

        return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docmost-backup",
        description="",  # We handle description in custom formatter
        formatter_class=CustomHelpFormatter,
        add_help=True,
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=list(COMMANDS.keys()),
        help=argparse.SUPPRESS,  # Hide from default help
    )
    # Restore-specific arguments
    parser.add_argument(
        "--path",
        help="Path to backup folder (for restore command)",
    )
    parser.add_argument(
        "--space-name",
        help="Space name for restore (defaults to folder name)",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    return parser


def main():
    enable_vt_mode()
    print_logo()

    # Handle --no-deps before argparse sees it
    if "--no-deps" in sys.argv:
        sys.argv.remove("--no-deps")
    else:
        ensure_deps()

    parser = build_parser()
    args = parser.parse_args()

    # If no command provided, show help/menu and exit
    if not args.command:
        parser.print_help()
        return

    # Store restore args for cmd_restore to access
    if args.command == "restore":
        sys._restore_path = args.path
        sys._restore_space_name = args.space_name

    # Load config (may not exist yet for config/reset commands)
    config = load_config() or {}

    try:
        cmd_func, _ = COMMANDS[args.command]
        success = cmd_func(config)

        if success:
            if args.command != "version":
                print(f"\n{Colors.GREEN}{Colors.BOLD}+ Done{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}x Failed{Colors.RESET}")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Cancelled by user.{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}{Colors.BOLD}x Unexpected error:{Colors.RESET}")
        print(f"{Colors.RED}{e}{Colors.RESET}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()