"""Path configuration for the TCHAI LCA application."""

from datetime import datetime
from pathlib import Path

def ensure_dir(p: Path):
    """Ensure directory exists, handling conflicts by renaming existing files."""
    if p.exists() and not p.is_dir():
        backup = p.with_name(f"{p.name}.conflict.{datetime.now().strftime('%Y%m%d%H%M%S')}")
        p.rename(backup)
    p.mkdir(parents=True, exist_ok=True)

# Base directories
APP_DIR = Path.cwd()
ASSETS = APP_DIR / "assets"
ensure_dir(ASSETS)

# Asset subdirectories
DB_ROOT = ASSETS / "databases"
ensure_dir(DB_ROOT)

GUIDES = ASSETS / "guides"
ensure_dir(GUIDES)

FONTS = ASSETS / "fonts"
ensure_dir(FONTS)

LOGS_DIR = ASSETS / "logs"
ensure_dir(LOGS_DIR)

LANG_FILE_DIR = ASSETS / "i18n"
ensure_dir(LANG_FILE_DIR)

# Key files
USERS_FILE = ASSETS / "users.json"
ACTIVE_DB_FILE = DB_ROOT / "active.json"

# Logo candidates
LOGO_CANDIDATES = [
    ASSETS / "tchai_logo.png", 
    Path("tchai_logo.png"), 
    Path("/mnt/data/tchai_logo.png")
]

# Template candidates
TEMPLATE = GUIDES / "report_template.docx"       