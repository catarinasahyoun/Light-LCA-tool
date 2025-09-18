"""User data model."""

from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    """User model for authentication."""
    email: str
    password_hash: str
    salt: str
    name: Optional[str] = None
    
    def get_initials(self) -> str:
        """Get user initials from email or name."""
        import re
        name_to_use = self.name or self.email
        parts = [p for p in re.split(r"\s+|_+|\.+|@", name_to_use) if p]
        return ((parts[0][0] if parts else "U") + (parts[1][0] if len(parts) > 1 else "")).upper()