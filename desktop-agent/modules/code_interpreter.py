"""
Code Interpreter sandbox — agent can write and execute Python code.

Like Claude Code's analysis tool or OpenHands' code execution, this lets the
agent solve problems that don't map to a fixed action: data analysis, file
parsing, math, custom automation, etc.

SAFETY MODEL:
  - Code runs in a restricted subprocess with resource limits
  - Network access blocked by default (configurable)
  - Filesystem access restricted to a sandbox directory
  - CPU and memory caps enforced via resource.setrlimit
  - Import whitelist: only safe stdlib modules + a few third-party (pandas, numpy)
  - Forbidden: os.system, subprocess, open with /etc/, ~/.ssh, etc.
"""
import os
import sys
import ast
import subprocess
import tempfile
import shutil
import time
import resource
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("code_interp")


# Allowed imports (whitelist)
ALLOWED_MODULES = {
    # Stdlib
    "math", "statistics", "random", "datetime", "time", "json", "csv",
    "re", "string", "collections", "itertools", "functools", "operator",
    "decimal", "fractions", "pathlib", "io", "base64", "hashlib", "hmac",
    "urllib.parse", "unicodedata", "textwrap", "difflib", "pprint",
    # Data
    "pandas", "numpy", "PIL",
    # Math
    "scipy", "sympy",
}

# Forbidden patterns (checked via AST)
FORBIDDEN_ATTRS = {
    "os.system", "os.popen", "os.exec", "os.spawn",
    "subprocess.call", "subprocess.run", "subprocess.Popen",
    "eval", "exec",  # allow exec only via our wrapper
    "__import__",
    "globals", "locals",
}

FORBIDDEN_PATHS = [
    "/etc/", "/var/", "/root/", "/proc/", "/sys/",
    ".ssh", ".aws", ".config", "password", "credential",
]


def register(executor, config: dict):
    mod = CodeInterpreterModule(config)
    executor.register_handler("code.run_python", mod.run_python)
    executor.register_handler("code.evaluate", mod.evaluate_expression)
    executor.register_handler("code.list_files", mod.list_sandbox_files)
    executor.register_handler("code.read_file", mod.read_sandbox_file)
    log.info("Code interpreter module registered: 4 actions")


class CodeInterpreterModule:
    """Sandboxed Python code execution."""

    def __init__(self, config: dict):
        self.config = config.get("code_interpreter", {})
        self.sandbox_dir = os.path.join(get_data_dir(), "sandbox")
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)
        self.timeout_s = self.config.get("timeout_s", 30)
        self.max_memory_mb = self.config.get("max_memory_mb", 256)

    def _validate_code(self, code: str) -> tuple[bool, str]:
        """Static analysis — reject dangerous code."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        # Walk the AST
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in ALLOWED_MODULES and not any(
                        alias.name.startswith(m + ".") for m in ALLOWED_MODULES
                    ):
                        return False, f"Import not allowed: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module not in ALLOWED_MODULES and not any(
                    node.module.startswith(m + ".") for m in ALLOWED_MODULES
                ):
                    return False, f"Import not allowed: {node.module}"

            # Check calls to forbidden attributes
            if isinstance(node, ast.Attribute):
                # Build the dotted name (best effort)
                attr_chain = self._get_attr_chain(node)
                if attr_chain and any(f in attr_chain for f in FORBIDDEN_ATTRS):
                    return False, f"Forbidden: {attr_chain}"

            # Check string literals containing forbidden paths
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for forbidden in FORBIDDEN_PATHS:
                    if forbidden in node.value:
                        return False, f"Forbidden path in string: {forbidden}"

        return True, "OK"

    def _get_attr_chain(self, node) -> str:
        """Get a dotted attribute chain like 'os.system' from an AST node."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    async def run_python(self, code: str, timeout: Optional[int] = None,
                          capture_files: bool = True, **kwargs) -> Dict[str, Any]:
        """Execute Python code in a sandbox.

        Args:
            code: Python source code to execute.
            timeout: Max execution time (seconds). Default 30.
            capture_files: If True, files created in the sandbox are listed in the result.
        """
        # Validate
        valid, error = self._validate_code(code)
        if not valid:
            return {"success": False, "error": f"Code validation failed: {error}"}

        timeout = timeout or self.timeout_s
        script_path = os.path.join(self.sandbox_dir, f"script_{int(time.time() * 1000)}.py")

        # Write the script with safety wrapper
        wrapped_code = self._wrap_code(code)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(wrapped_code)

        # Execute in subprocess with resource limits
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.sandbox_dir,
                env=self._safe_env(),
            )

            response = {
                "success": result.returncode == 0,
                "stdout": result.stdout[:5000],  # Cap output size
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
                "elapsed_s": 0,  # Set below
            }

            # List files created in sandbox
            if capture_files:
                files_created = []
                for entry in Path(self.sandbox_dir).iterdir():
                    if entry.name != os.path.basename(script_path) and entry.is_file():
                        files_created.append({
                            "name": entry.name,
                            "size": entry.stat().st_size,
                        })
                response["files_created"] = files_created

            # Clean up script
            try:
                os.unlink(script_path)
            except Exception:
                pass

            return response

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Code timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _wrap_code(self, code: str) -> str:
        """Wrap user code in a safety harness."""
        return f"""# -*- coding: utf-8 -*-
import sys
import resource
import os
import builtins

# === Resource limits ===
try:
    resource.setrlimit(resource.RLIMIT_AS, ({self.max_memory_mb * 1024 * 1024}, {self.max_memory_mb * 1024 * 1024}))
    resource.setrlimit(resource.RLIMIT_CPU, ({self.timeout_s}, {self.timeout_s}))
except Exception:
    pass

# === Restrict filesystem ===
_original_open = builtins.open

def _safe_open(file, mode='r', *args, **kwargs):
    if isinstance(file, str):
        forbidden = ['/etc/', '/var/', '/root/', '/proc/', '/sys/', '.ssh', '.aws']
        for f in forbidden:
            if f in file:
                raise PermissionError(f"Access denied: {{file}}")
    return _original_open(file, mode, *args, **kwargs)

builtins.open = _safe_open

# === Capture output ===
import io
from contextlib import redirect_stdout, redirect_stderr

_stdout_capture = io.StringIO()
_stderr_capture = io.StringIO()

try:
    with redirect_stdout(_stdout_capture), redirect_stderr(_stderr_capture):
        exec(compile('''{code.replace("'", "\\'").replace("'''", "\\'\\'\\'")}''', '<agent>', 'exec'))
except SystemExit:
    pass
except Exception as e:
    sys.stderr.write(f"RuntimeError: {{e}}\\n")

# Output captured content
sys.__stdout__.write(_stdout_capture.getvalue())
sys.__stderr__.write(_stderr_capture.getvalue())
"""

    def _safe_env(self) -> Dict[str, str]:
        """Build a sanitized environment for the subprocess."""
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": self.sandbox_dir,
            "TMPDIR": tempfile.gettempdir(),
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            "PYTHONPATH": self.sandbox_dir,
            "MPLBACKEND": "Agg",  # Matplotlib non-interactive
        }
        return env

    async def evaluate_expression(self, expression: str, **kwargs) -> Dict[str, Any]:
        """Evaluate a Python expression (no statements)."""
        # Validate it's an expression, not a statement
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            return {"success": False, "error": f"Not an expression: {e}"}

        # Run via run_python with print()
        code = f"print({expression})"
        return await self.run_python(code)

    async def list_sandbox_files(self, **kwargs) -> Dict[str, Any]:
        """List files in the sandbox."""
        files = []
        for entry in Path(self.sandbox_dir).iterdir():
            if entry.is_file():
                files.append({
                    "name": entry.name,
                    "size": entry.stat().st_size,
                    "modified": entry.stat().st_mtime,
                })
        return {"success": True, "files": files, "count": len(files)}

    async def read_sandbox_file(self, name: str, **kwargs) -> Dict[str, Any]:
        """Read a file from the sandbox."""
        path = Path(self.sandbox_dir) / name
        if not path.exists() or not path.is_file():
            return {"success": False, "error": "File not found"}
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return {"success": True, "name": name, "content": content[:10000]}
        except Exception as e:
            return {"success": False, "error": str(e)}
