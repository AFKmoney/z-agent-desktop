"""
Backup & Restore — export and import all agent data.

Creates a single backup file containing:
  - Memory (facts, preferences, shortcuts)
  - Conversation history
  - Skills (learned + auto-created)
  - Prompt templates
  - Scheduled tasks
  - Watch rules
  - Webhooks
  - Cost records
  - Audit log
  - Activity data
  - Vector memories

Backups can be:
  - Manual (via dashboard button)
  - Scheduled (daily/weekly)
  - Triggered by webhook

Restore:
  - Selective (only certain data types)
  - Full (everything)
"""
import os
import json
import time
import zipfile
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("backup")


class BackupManager:
    """Creates and restores backups."""

    def __init__(self):
        self.data_dir = Path(get_data_dir())
        self.backups_dir = self.data_dir / "backups"
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, include_screenshots: bool = False) -> Dict[str, Any]:
        """Create a full backup. Returns backup file path + metadata."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"zagent_backup_{timestamp}"
        backup_path = self.backups_dir / f"{backup_name}.zip"

        metadata = {
            "version": 1,
            "created_at": time.time(),
            "created_at_human": time.strftime("%Y-%m-%d %H:%M:%S"),
            "files": [],
            "total_size": 0,
        }

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # JSON data files
            json_files = [
                "memory.json",
                "conversations.json",
                "skills_index.json",
                "prompt_templates.json",
                "scheduled_tasks.json",
                "watch_rules.json",
                "webhooks.json",
                "costs.json",
                "activity.json",
                "skill_patterns.json",
                "suggestions.json",
            ]
            for fname in json_files:
                fpath = self.data_dir / fname
                if fpath.exists():
                    zf.write(fpath, fname)
                    metadata["files"].append({
                        "name": fname,
                        "size": fpath.stat().st_size,
                    })
                    metadata["total_size"] += fpath.stat().st_size

            # Vector memory (JSON + NPY)
            vm_dir = self.data_dir / "vector_memory"
            if vm_dir.exists():
                for f in vm_dir.iterdir():
                    if f.is_file():
                        arcname = f"vector_memory/{f.name}"
                        zf.write(f, arcname)
                        metadata["files"].append({
                            "name": arcname,
                            "size": f.stat().st_size,
                        })
                        metadata["total_size"] += f.stat().st_size

            # Knowledge base
            kb_dir = self.data_dir / "knowledge_base"
            if kb_dir.exists():
                for f in kb_dir.iterdir():
                    if f.is_file():
                        arcname = f"knowledge_base/{f.name}"
                        zf.write(f, arcname)
                        metadata["files"].append({
                            "name": arcname,
                            "size": f.stat().st_size,
                        })
                        metadata["total_size"] += f.stat().st_size

            # Audit log (JSONL)
            audit_file = self.data_dir / "audit_log.jsonl"
            if audit_file.exists():
                zf.write(audit_file, "audit_log.jsonl")
                metadata["files"].append({
                    "name": "audit_log.jsonl",
                    "size": audit_file.stat().st_size,
                })
                metadata["total_size"] += audit_file.stat().st_size

            # Optionally include screenshots (can be large)
            if include_screenshots:
                ss_dir = self.data_dir / "screenshots"
                if ss_dir.exists():
                    for f in ss_dir.iterdir():
                        if f.is_file() and f.stat().st_size < 5 * 1024 * 1024:  # skip >5MB
                            arcname = f"screenshots/{f.name}"
                            zf.write(f, arcname)
                            metadata["files"].append({
                                "name": arcname,
                                "size": f.stat().st_size,
                            })
                            metadata["total_size"] += f.stat().st_size

            # Write metadata into the backup
            zf.writestr("_backup_metadata.json", json.dumps(metadata, indent=2))

        backup_size = backup_path.stat().st_size
        log.info(f"Backup created: {backup_path.name} ({backup_size / 1024:.1f} KB)")

        return {
            "success": True,
            "path": str(backup_path),
            "name": backup_path.name,
            "size_bytes": backup_size,
            "size_kb": round(backup_size / 1024, 1),
            "file_count": len(metadata["files"]),
            "metadata": metadata,
        }

    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        for f in sorted(self.backups_dir.glob("zagent_backup_*.zip"), reverse=True):
            try:
                with zipfile.ZipFile(f, "r") as zf:
                    meta_data = zf.read("_backup_metadata.json").decode()
                    meta = json.loads(meta_data)
                backups.append({
                    "name": f.name,
                    "path": str(f),
                    "size_bytes": f.stat().st_size,
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "created_at": meta.get("created_at"),
                    "created_at_human": meta.get("created_at_human"),
                    "file_count": len(meta.get("files", [])),
                })
            except Exception:
                continue
        return backups

    def restore_backup(self, backup_path: str, selective: Optional[List[str]] = None) -> Dict[str, Any]:
        """Restore from a backup file.

        Args:
            backup_path: Path to the backup zip.
            selective: List of file names to restore (None = all).
        """
        if not os.path.exists(backup_path):
            return {"success": False, "error": "Backup file not found"}

        restored = []
        errors = []

        try:
            with zipfile.ZipFile(backup_path, "r") as zf:
                for info in zf.namelist():
                    if info == "_backup_metadata.json":
                        continue

                    # Selective restore
                    if selective and not any(s in info for s in selective):
                        continue

                    # Determine target path
                    if "/" in info:
                        # Subdirectory file
                        parts = info.split("/")
                        target = self.data_dir / Path(*parts)
                    else:
                        target = self.data_dir / info

                    # Create parent dirs
                    target.parent.mkdir(parents=True, exist_ok=True)

                    # Extract
                    try:
                        with zf.open(info) as src, open(target, "wb") as dst:
                            dst.write(src.read())
                        restored.append(info)
                    except Exception as e:
                        errors.append({"file": info, "error": str(e)})

            log.info(f"Backup restored: {len(restored)} files, {len(errors)} errors")
            return {
                "success": len(errors) == 0,
                "restored_files": restored,
                "restored_count": len(restored),
                "errors": errors,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_backup(self, backup_name: str) -> Dict[str, Any]:
        """Delete a backup file."""
        path = self.backups_dir / backup_name
        if not path.exists():
            return {"success": False, "error": "Backup not found"}
        try:
            path.unlink()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get backup statistics."""
        backups = self.list_backups()
        total_size = sum(b["size_bytes"] for b in backups)
        return {
            "backup_count": len(backups),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_backup": backups[-1]["created_at_human"] if backups else None,
            "newest_backup": backups[0]["created_at_human"] if backups else None,
        }


# Global instance
_backup: Optional[BackupManager] = None


def init_backup_manager() -> BackupManager:
    global _backup
    _backup = BackupManager()
    return _backup


def get_backup_manager() -> Optional[BackupManager]:
    if _backup is None:
        return init_backup_manager()
    return _backup
