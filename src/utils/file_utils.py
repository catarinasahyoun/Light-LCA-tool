"""File handling utilities."""

import base64
import zipfile
import logging
from pathlib import Path
from typing import Optional
from ..config.paths import GUIDES

logger = logging.getLogger(__name__)

try:
    from docx import Document
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

class FileUtils:
    """Utilities for file operations."""
    
    @staticmethod
    def load_logo_bytes(logo_candidates: list) -> Optional[bytes]:
        """Load logo bytes from the first available candidate path."""
        for path in logo_candidates:
            if isinstance(path, str):
                path = Path(path)
            if path.exists():
                try:
                    return path.read_bytes()
                except Exception:
                    continue
        return None
    
    @staticmethod
    def create_logo_tag(logo_bytes: Optional[bytes], height: int = 86) -> str:
        """Create an HTML img tag for the logo."""
        if not logo_bytes:
            return ""
        
        b64 = base64.b64encode(logo_bytes).decode()
        return f"<img src='data:image/png;base64,{b64}' alt='TCHAI' style='height:{height}px'/>"
    
    @staticmethod
    def embed_font_css(fonts_dir: Path) -> str:
        """Create CSS for embedding custom fonts."""
        font_regular = fonts_dir / "PPNeueMontreal-Regular.woff2"
        font_medium = fonts_dir / "PPNeueMontreal-Medium.woff2"
        
        def create_font_face(font_path: Path, weight: int) -> str:
            if not font_path.exists():
                return ""
            try:
                font_bytes = font_path.read_bytes()
                b64 = base64.b64encode(font_bytes).decode()
                return f"""
                @font-face {{
                    font-family: 'PP Neue Montreal';
                    src: url('data:font/woff2;base64,{b64}') format('woff2');
                    font-weight: {weight};
                    font-style: normal;
                    font-display: swap;
                }}
                """
            except Exception:
                return ""
        
        return create_font_face(font_regular, 400) + create_font_face(font_medium, 500)
    
    @staticmethod
    def find_template(template_candidates: list) -> Optional[Path]:
        """Find the first available template from candidates."""
        for candidate in template_candidates:
            if isinstance(candidate, str):
                candidate = Path(candidate)
            if candidate.exists():
                return candidate
        return None