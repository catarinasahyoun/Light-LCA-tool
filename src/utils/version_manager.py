"""Version management for LCA assessments."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from ..config.paths import ensure_dir

class VersionManager:
    """Manages saving, loading, and organizing LCA assessment versions."""
    
    def __init__(self, storage_dir: str = "lca_versions"):
        """Initialize version manager with storage directory."""
        self.dir = Path(storage_dir)
        ensure_dir(self.dir)
        self.meta = self.dir / "lca_versions_metadata.json"
    
    def _load_metadata(self) -> Dict:
        """Load version metadata from JSON file."""
        if self.meta.exists():
            try:
                return json.loads(self.meta.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}
    
    def _save_metadata(self, metadata: Dict):
        """Save version metadata to JSON file."""
        self.meta.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    def save(self, name: str, data: Dict, description: str = "") -> Tuple[bool, str]:
        """
        Save a new version.
        
        Args:
            name: Version name (must be unique and safe for filesystem)
            data: Assessment data to save
            description: Optional description
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate name
        SAFE_NAME = re.compile(r"^[A-Za-z0-9._ -]{1,64}$")
        metadata = self._load_metadata()
        
        name = (name or "").strip()
        if not name:
            return False, "Enter a name."
        
        if not SAFE_NAME.match(name):
            return False, "Only letters/numbers/space/dot/dash/underscore (max 64)."
        
        if name in metadata:
            return False, "Name exists."
        
        # Create file path and validate it's within our directory
        file_path = (self.dir / f"{name}.json").resolve()
        if self.dir.resolve() not in file_path.parents:
            return False, "Invalid name."
        
        try:
            # Create version payload
            payload = {
                "assessment_data": data,
                "timestamp": datetime.now().isoformat(),
                "description": description.strip()
            }
            
            # Save version file
            file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            
            # Update metadata
            metadata[name] = {
                "filename": file_path.name,
                "description": description.strip(),
                "created_at": datetime.now().isoformat(),
                "materials_count": len(data.get('selected_materials', [])),
                "total_co2": data.get('overall_co2', 0)
            }
            
            self._save_metadata(metadata)
            return True, "Saved successfully!"
            
        except Exception as e:
            return False, f"Save failed: {str(e)}"
    
    def list_versions(self) -> Dict:
        """List all saved versions with metadata."""
        return self._load_metadata()
    
    def load(self, name: str) -> Tuple[Optional[Dict], str]:
        """
        Load a version by name.
        
        Args:
            name: Version name to load
        
        Returns:
            Tuple of (data: Dict or None, message: str)
        """
        metadata = self._load_metadata()
        
        if name not in metadata:
            return None, "Version not found."
        
        file_path = self.dir / metadata[name]["filename"]
        if not file_path.exists():
            return None, "Version file missing."
        
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            return payload.get("assessment_data", {}), "Loaded successfully!"
        except Exception as e:
            return None, f"Load failed: {str(e)}"
    
    def delete(self, name: str) -> Tuple[bool, str]:
        """
        Delete a version.
        
        Args:
            name: Version name to delete
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        metadata = self._load_metadata()
        
        if name not in metadata:
            return False, "Version not found."
        
        try:
            # Remove file
            file_path = self.dir / metadata[name]["filename"]
            if file_path.exists():
                file_path.unlink()
            
            # Remove from metadata
            del metadata[name]
            self._save_metadata(metadata)
            
            return True, "Deleted successfully!"
            
        except Exception as e:
            return False, f"Delete failed: {str(e)}"
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics about saved versions."""
        metadata = self._load_metadata()
        
        if not metadata:
            return {
                "total_versions": 0,
                "latest_version": None,
                "total_materials": 0,
                "avg_co2": 0
            }
        
        total_versions = len(metadata)
        latest_version = max(metadata.items(), key=lambda x: x[1]["created_at"])
        total_materials = sum(info.get("materials_count", 0) for info in metadata.values())
        avg_co2 = sum(info.get("total_co2", 0) for info in metadata.values()) / total_versions
        
        return {
            "total_versions": total_versions,
            "latest_version": latest_version[0] if latest_version else None,
            "total_materials": total_materials,
            "avg_co2": avg_co2
        }