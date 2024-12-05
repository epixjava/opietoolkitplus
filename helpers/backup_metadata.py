import json
from pathlib import Path
from datetime import datetime

class BackupMetadata:
    def __init__(self, backup_dir):
        self.metadata_file = Path(backup_dir) / "backup_metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self):
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def update_backup_metadata(self, backup_name, metadata):
        """Update metadata for a specific backup"""
        self.metadata[backup_name] = metadata
        self._save_metadata()

    def get_backup_metadata(self, backup_name):
        """Get metadata for a specific backup"""
        return self.metadata.get(backup_name, {})

    def _save_metadata(self):
        """Save metadata to disk"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save backup metadata: {e}")