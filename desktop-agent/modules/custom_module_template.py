"""
CUSTOM MODULE TEMPLATE — copy this file to create your own module.

This template shows the minimal structure required to add a new capability
to Z.AGENT. Every module follows the same 3-part pattern:

1. register(executor, config)  — called by the agent at startup
2. Module class with handlers   — one method per action
3. register_handler() calls     — wire actions to handlers

See existing modules (file_manager.py, email_client.py, slack_notifier.py)
for complete examples.

────────────────────────────────────────────────────────────────────────
QUICK START — to add a new module called "my_module":

1. Copy this file:
     cp modules/custom_module_template.py modules/my_module.py

2. Edit it: replace "MyModule" with your class name, implement your
   actions as async methods, register them in register().

3. Register your module in core/agent.py — find the module_registry list
   and add:
       ("my_module", "modules.my_module"),

4. Add the prompt description in core/planner.py PLANNER_SYSTEM so the
   planner knows about your new actions:
       - my_module.action_name: short description (params: ...)

5. Restart the agent. Done — your actions are now available to the planner
   and can be triggered from Telegram / dashboard / CLI.
"""
import os
from typing import Dict, Any, Optional
from utils.logger import get_logger

log = get_logger("my_module")


# === Optional dependency detection pattern ===
# If your module depends on an external library, detect it here so the
# agent can skip your module gracefully if the dep is missing.
try:
    import some_library  # type: ignore
    LIBRARY_AVAILABLE = True
except ImportError:
    LIBRARY_AVAILABLE = False
    log.info("some_library not installed - my_module disabled (pip install some_library)")


def register(executor, config: dict):
    """Register all actions exposed by this module.

    Called by Agent.initialize() during startup.
    Pattern: executor.register_handler("namespace.action", handler_method)
    """
    if not LIBRARY_AVAILABLE:
        log.info("my_module not registered — install some_library to enable")
        return

    # Instantiate the module with config
    mod = MyModule(config)

    # Wire actions to handler methods
    executor.register_handler("my_module.do_something", mod.do_something)
    executor.register_handler("my_module.get_status", mod.get_status)

    log.info("my_module registered: 2 actions available")


class MyModule:
    """Your module logic goes here.

    Each public async method becomes an action handler.
    Method parameters become action params (used by the planner).
    Each method MUST return a dict with at minimum {"success": bool}.
    """

    def __init__(self, config: dict):
        # Read your section from config.yaml
        self.config = config.get("my_module", {})
        self.api_key = os.environ.get(
            "MY_MODULE_API_KEY",
            self.config.get("api_key", "")
        )

    async def do_something(
        self,
        param1: str,
        param2: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Short description of what this action does.

        Args:
            param1: Description of param1 (required).
            param2: Description of param2 (optional, default None).

        Returns:
            Dict with success status and result data.
        """
        if not self.api_key:
            return {"success": False, "error": "MY_MODULE_API_KEY not set"}

        try:
            # Your logic here
            result = f"Processed {param1} with param2={param2}"
            log.info(f"my_module.do_something: {result}")
            return {
                "success": True,
                "result": result,
                "param1": param1,
                "param2": param2,
            }
        except Exception as e:
            log.error(f"my_module.do_something failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_status(self, **kwargs) -> Dict[str, Any]:
        """Return module status — useful for diagnostics."""
        return {
            "success": True,
            "status": "operational" if self.api_key else "no_api_key",
            "configured": bool(self.api_key),
        }


# ─────────────────────────────────────────────────────────────────────
# DON'T FORGET — to make your actions visible to the planner, add them
# to the PLANNER_SYSTEM prompt in core/planner.py. Example:
#
#   - my_module.do_something: do a thing (params: param1, param2?)
#   - my_module.get_status: get module status
#
# Without this, the planner won't know your actions exist and will
# never use them.
# ─────────────────────────────────────────────────────────────────────
