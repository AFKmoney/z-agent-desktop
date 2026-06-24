"""
File Manager module - organize, move, rename, search, read, write files.
"""
import os
import shutil
import glob
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.security import get_guard
from utils.config import get_data_dir

log = get_logger("files")


def register(executor, config: dict):
    mod = FileManagerModule(config)
    
    executor.register_handler("files.list", mod.list_files)
    executor.register_handler("files.move", mod.move_files)
    executor.register_handler("files.copy", mod.copy_files)
    executor.register_handler("files.rename", mod.rename_file)
    executor.register_handler("files.delete", mod.delete_file)
    executor.register_handler("files.organize", mod.organize_folder)
    executor.register_handler("files.search", mod.search_files)
    executor.register_handler("files.read", mod.read_file)
    executor.register_handler("files.write", mod.write_file)
    executor.register_handler("files.create_dir", mod.create_dir)


class FileManagerModule:
    
    def __init__(self, config: dict):
        self.config = config.get("files", {})
        self.guard = get_guard()
        self.watch_folders = [
            os.path.expandvars(os.path.expanduser(f))
            for f in self.config.get("watch_folders", [])
        ]
        self.rules = self.config.get("auto_organize", {}).get("rules", {})
        self.safe_delete = self.config.get("safe_delete", True)
    
    def _expand(self, path: str) -> str:
        return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
    
    async def list_files(self, path: str = None, pattern: str = "*",
                          include_hidden: bool = False, **kwargs) -> Dict[str, Any]:
        """List files in a directory."""
        if path is None:
            path = self.watch_folders[0] if self.watch_folders else os.path.expanduser("~")
        target = self._expand(path)
        
        if not self.guard.check_path_access(target, "list"):
            return {"success": False, "error": "Access denied"}
        
        if not os.path.exists(target):
            return {"success": False, "error": f"Path not found: {target}"}
        
        items = []
        try:
            for entry in sorted(Path(target).glob(pattern)):
                if not include_hidden and entry.name.startswith("."):
                    continue
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "extension": entry.suffix.lower(),
                })
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        return {"success": True, "path": target, "items": items, "count": len(items)}
    
    async def move_files(self, sources: List[str], destination: str, **kwargs) -> Dict[str, Any]:
        """Move files to a destination."""
        dest = self._expand(destination)
        if not self.guard.check_path_access(dest, "move"):
            return {"success": False, "error": "Access denied to destination"}
        
        os.makedirs(dest, exist_ok=True)
        moved = []
        errors = []
        
        for src in sources:
            src_path = self._expand(src)
            if not self.guard.check_path_access(src_path, "move"):
                errors.append({"source": src, "error": "protected"})
                continue
            try:
                target = os.path.join(dest, os.path.basename(src_path))
                shutil.move(src_path, target)
                moved.append({"from": src_path, "to": target})
                log.info(f"Moved: {src_path} -> {target}")
            except Exception as e:
                errors.append({"source": src, "error": str(e)})
        
        return {"success": len(errors) == 0, "moved": moved, "errors": errors}
    
    async def copy_files(self, sources: List[str], destination: str, **kwargs) -> Dict[str, Any]:
        """Copy files to a destination."""
        dest = self._expand(destination)
        if not self.guard.check_path_access(dest, "copy"):
            return {"success": False, "error": "Access denied"}
        
        os.makedirs(dest, exist_ok=True)
        copied = []
        errors = []
        
        for src in sources:
            src_path = self._expand(src)
            if not self.guard.check_path_access(src_path, "copy"):
                errors.append({"source": src, "error": "protected"})
                continue
            try:
                target = os.path.join(dest, os.path.basename(src_path))
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, target)
                else:
                    shutil.copy2(src_path, target)
                copied.append({"from": src_path, "to": target})
            except Exception as e:
                errors.append({"source": src, "error": str(e)})
        
        return {"success": len(errors) == 0, "copied": copied, "errors": errors}
    
    async def rename_file(self, path: str, new_name: str, **kwargs) -> Dict[str, Any]:
        """Rename a file or directory."""
        src = self._expand(path)
        if not self.guard.check_path_access(src, "rename"):
            return {"success": False, "error": "Access denied"}
        
        new_path = os.path.join(os.path.dirname(src), new_name)
        try:
            os.rename(src, new_path)
            return {"success": True, "from": src, "to": new_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_file(self, path: str, permanent: bool = False, **kwargs) -> Dict[str, Any]:
        """Delete a file (move to trash by default)."""
        target = self._expand(path)
        if not self.guard.check_path_access(target, "delete"):
            return {"success": False, "error": "Access denied to protected path"}
        
        if permanent:
            try:
                if os.path.isdir(target):
                    shutil.rmtree(target)
                else:
                    os.remove(target)
                log.info(f"Permanently deleted: {target}")
                return {"success": True, "path": target, "permanent": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            success = self.guard.safe_delete(target)
            return {"success": success, "path": target}
    
    async def organize_folder(self, path: str = None, dry_run: bool = False, **kwargs) -> Dict[str, Any]:
        """Auto-organize a folder by file extension."""
        target = self._expand(path) if path else (self.watch_folders[0] if self.watch_folders else None)
        if not target:
            return {"success": False, "error": "No folder specified"}
        
        if not self.guard.check_path_access(target, "organize"):
            return {"success": False, "error": "Access denied"}
        
        if not os.path.exists(target):
            return {"success": False, "error": f"Folder not found: {target}"}
        
        organized = {"by_category": {}, "skipped": [], "errors": []}
        
        for entry in Path(target).iterdir():
            if entry.is_dir() or entry.name.startswith("."):
                continue
            
            ext = entry.suffix.lower()
            category = None
            for cat, exts in self.rules.items():
                if ext in exts:
                    category = cat
                    break
            
            if category is None:
                organized["skipped"].append(entry.name)
                continue
            
            dest_dir = os.path.join(target, category)
            dest_path = os.path.join(dest_dir, entry.name)
            
            if dry_run:
                organized["by_category"].setdefault(category, []).append(entry.name)
                continue
            
            try:
                os.makedirs(dest_dir, exist_ok=True)
                # Handle name conflicts
                if os.path.exists(dest_path):
                    base, ext2 = os.path.splitext(entry.name)
                    dest_path = os.path.join(dest_dir, f"{base}_{int(__import__('time').time())}{ext2}")
                shutil.move(str(entry), dest_path)
                organized["by_category"].setdefault(category, []).append(entry.name)
                log.info(f"Organized: {entry.name} -> {category}/")
            except Exception as e:
                organized["errors"].append({"file": entry.name, "error": str(e)})
        
        return {"success": True, "result": organized, "dry_run": dry_run, "path": target}
    
    async def search_files(self, path: str = None, pattern: str = "*",
                            content_query: Optional[str] = None,
                            max_results: int = 100, **kwargs) -> Dict[str, Any]:
        """Search files by name pattern or content."""
        target = self._expand(path) if path else os.path.expanduser("~")
        if not self.guard.check_path_access(target, "search"):
            return {"success": False, "error": "Access denied"}
        
        results = []
        try:
            for entry in Path(target).rglob(pattern):
                if len(results) >= max_results:
                    break
                if not self.guard.check_path_access(str(entry), "search"):
                    continue
                if entry.is_file():
                    # If content query, search inside file (only text files)
                    if content_query:
                        try:
                            if entry.stat().st_size > 1024 * 1024:  # Skip files > 1MB
                                continue
                            with open(entry, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                if content_query.lower() in content.lower():
                                    results.append({
                                        "path": str(entry),
                                        "name": entry.name,
                                        "size": entry.stat().st_size,
                                    })
                        except Exception:
                            continue
                    else:
                        results.append({
                            "path": str(entry),
                            "name": entry.name,
                            "size": entry.stat().st_size,
                        })
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        return {"success": True, "results": results, "count": len(results)}
    
    async def read_file(self, path: str, max_size: int = 1024 * 1024, **kwargs) -> Dict[str, Any]:
        """Read text file content."""
        target = self._expand(path)
        if not self.guard.check_path_access(target, "read"):
            return {"success": False, "error": "Access denied"}
        if not self.guard.check_file_size(target):
            return {"success": False, "error": "File too large"}
        
        try:
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(max_size)
            return {"success": True, "path": target, "content": content, "truncated": len(content) >= max_size}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def write_file(self, path: str, content: str, append: bool = False, **kwargs) -> Dict[str, Any]:
        """Write text to a file."""
        target = self._expand(path)
        if not self.guard.check_path_access(target, "write"):
            return {"success": False, "error": "Access denied"}
        
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            mode = "a" if append else "w"
            with open(target, mode, encoding="utf-8") as f:
                f.write(content)
            log.info(f"Written {len(content)} chars to {target}")
            return {"success": True, "path": target, "bytes": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_dir(self, path: str, **kwargs) -> Dict[str, Any]:
        """Create a directory."""
        target = self._expand(path)
        if not self.guard.check_path_access(target, "mkdir"):
            return {"success": False, "error": "Access denied"}
        try:
            os.makedirs(target, exist_ok=True)
            return {"success": True, "path": target}
        except Exception as e:
            return {"success": False, "error": str(e)}
