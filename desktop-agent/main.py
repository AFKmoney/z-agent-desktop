#!/usr/bin/env python3
"""
Z.AI Desktop Agent - Main entry point.

Usage:
    python main.py                 # Start agent (Telegram + Web API)
    python main.py --cli           # Interactive CLI mode
    python main.py --task "..."    # Run a single task
    python main.py --check         # Check configuration and exit

Environment variables:
    ZAI_API_KEY           - Required, get at https://z.ai/
    TELEGRAM_BOT_TOKEN    - Optional, for Telegram interface
    EMAIL_USER            - Optional, for email module
    EMAIL_APP_PASSWORD    - Optional, for email module

Config: config/config.yaml (override values with ZDA_ prefix env vars)
"""
import argparse
import asyncio
import os
import sys
import signal
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import load_config
from utils.logger import AgentLogger, get_logger
from utils.security import init_security
from core.agent import init_agent, get_agent
from core.zai_client import init_zai

# Optional interfaces — gracefully degrade if deps missing
try:
    from interfaces.telegram_bot import init_telegram
except ImportError as e:
    init_telegram = lambda config: None  # noqa: E731
    print(f"[warn] Telegram interface disabled: {e.name}")

try:
    from interfaces.web_api import app as web_app
except ImportError as e:
    web_app = None
    print(f"[warn] Web API disabled: {e.name}")

try:
    from interfaces.scheduler import init_scheduler
except ImportError as e:
    init_scheduler = None
    print(f"[warn] Scheduler disabled: {e.name}")


def parse_args():
    p = argparse.ArgumentParser(description="Z.AI Desktop Agent")
    p.add_argument("--cli", action="store_true", help="Interactive CLI mode")
    p.add_argument("--task", type=str, help="Run a single task and exit")
    p.add_argument("--check", action="store_true", help="Check configuration")
    p.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    p.add_argument("--host", type=str, default=None, help="Web API host override")
    p.add_argument("--port", type=int, default=None, help="Web API port override")
    return p.parse_args()


async def run_server(args):
    """Run the full agent: Telegram + Web API + Scheduler."""
    config = load_config(args.config)
    AgentLogger.setup(config)
    log = get_logger("main")
    
    log.info("=" * 60)
    log.info("Z.AI Desktop Agent - Starting")
    log.info("=" * 60)
    
    # Init security
    init_security(config)
    
    # Init agent
    agent = init_agent(config)
    await agent.initialize()
    
    # Start scheduler (optional)
    scheduler = None
    if init_scheduler is not None:
        try:
            scheduler = init_scheduler(config)
            await scheduler.start()
        except Exception as e:
            log.warning(f"Scheduler could not start: {e}")

    # Start Telegram (if configured)
    telegram = init_telegram(config)
    if telegram:
        await telegram.start()
        log.info("Telegram interface started")
    else:
        log.warning("Telegram interface disabled (no token)")

    # Start Web API
    server = None
    if web_app is not None:
        try:
            import uvicorn
            dash_cfg = config.get("dashboard", {})
            host = args.host or dash_cfg.get("host", "127.0.0.1")
            port = args.port or dash_cfg.get("port", 8765)

            config_uvicorn = uvicorn.Config(
                web_app,
                host=host,
                port=port,
                log_level="info",
                access_log=False,
            )
            server = uvicorn.Server(config_uvicorn)
        except ImportError:
            log.warning("uvicorn not installed - Web API disabled")

    # Start agent loop
    await agent.start()

    if server:
        log.info(f"Web API on http://{host}:{port}")
        log.info(f"Dashboard: open the Next.js app and connect to this API")
    log.info("Agent is running. Press Ctrl+C to stop.")

    # Run web server (blocks)
    if server:
        try:
            await server.serve()
        except asyncio.CancelledError:
            pass
        finally:
            log.info("Shutting down...")
            if telegram:
                await telegram.stop()
            if scheduler:
                await scheduler.stop()
            await agent.stop()
    else:
        # No web server — keep the process alive
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            log.info("Shutting down...")
            if telegram:
                await telegram.stop()
            if scheduler:
                await scheduler.stop()
            await agent.stop()


async def run_cli(args):
    """Interactive CLI mode."""
    config = load_config(args.config)
    AgentLogger.setup(config)
    log = get_logger("main")
    
    init_security(config)
    agent = init_agent(config)
    await agent.initialize()
    await agent.start()
    
    print("\n🤖 Z.AGENT - CLI mode")
    print("Tape ta demande en langage naturel, ou 'quit' pour quitter.\n")
    
    while True:
        try:
            user_input = input("👤> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Au revoir!")
            break
        
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue
        
        task_id = await agent.submit_task(user_input, source="cli")
        print(f"✅ Tâche {task_id} soumise, traitement...")
        
        # Wait for completion (simple: poll)
        while agent.current_task and agent.current_task.get("id") == task_id:
            await asyncio.sleep(0.5)
        
        # Show result from memory
        memory = __import__("core.memory", fromlist=["get_memory"]).get_memory()
        tasks = memory.get_recent_tasks(1)
        if tasks:
            t = tasks[0]
            print(f"\n📊 Résultat: {'✅' if t.get('success') else '❌'}")
            result = t.get("result", {})
            print(f"   Étapes: {result.get('succeeded', 0)}/{result.get('total_steps', 0)}")
            for r in result.get("results", []):
                status = "✅" if r.get("success") else "❌"
                print(f"   {status} {r.get('action')} - {r.get('elapsed_s', 0):.1f}s")
        print()
    
    await agent.stop()


async def run_single_task(args):
    """Run a single task and exit."""
    config = load_config(args.config)
    AgentLogger.setup(config)

    init_security(config)
    agent = init_agent(config)
    await agent.initialize()
    await agent.start()

    task_id = await agent.submit_task(args.task, source="cli")
    print(f"⏳ Task {task_id} submitted, waiting for completion...")

    # Wait for completion: poll memory until task_id appears in history
    memory = __import__("core.memory", fromlist=["get_memory"]).get_memory()
    deadline = asyncio.get_event_loop().time() + 120  # 2 min timeout
    while asyncio.get_event_loop().time() < deadline:
        recent = memory.get_recent_tasks(5)
        if any(t.get("task_id") == task_id for t in recent):
            break
        await asyncio.sleep(0.5)
    else:
        print("⏱️ Task timed out after 120s")

    # Show result
    tasks = memory.get_recent_tasks(5)
    task = next((t for t in tasks if t.get("task_id") == task_id), None)
    if task:
        success = task.get("success", False)
        print(f"\n{'✅' if success else '❌'} Task: {task.get('request')}")
        result = task.get("result", {})
        if result:
            print(f"Steps: {result.get('succeeded', 0)}/{result.get('total_steps', 0)}")
            for r in result.get("results", []):
                status = "✅" if r.get("success") else "❌"
                err = r.get("error", "")
                print(f"  {status} {r.get('action')}" + (f": {err[:100]}" if err else ""))
        else:
            print(f"Error: {task.get('error', 'unknown')}")
    else:
        print("⚠️ Task not found in history")

    await agent.stop()


def check_config(args):
    """Check configuration and exit."""
    print("Checking configuration...")
    try:
        config = load_config(args.config)
        print("✅ Config file loaded")
    except Exception as e:
        print(f"❌ Config error: {e}")
        sys.exit(1)
    
    # Check API key
    zai_key = os.environ.get("ZAI_API_KEY", "")
    if zai_key:
        print(f"✅ ZAI_API_KEY: {zai_key[:8]}...")
    else:
        print("⚠️  ZAI_API_KEY not set (get one at https://z.ai/)")
    
    # Telegram
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("✅ TELEGRAM_BOT_TOKEN: set")
    else:
        print("⚠️  TELEGRAM_BOT_TOKEN not set (Telegram will be disabled)")
    
    # Email
    if os.environ.get("EMAIL_USER"):
        print("✅ EMAIL_USER: set")
    else:
        print("⚠️  EMAIL_USER not set (email module will be limited)")
    
    # Python deps
    deps = ["pyautogui", "mss", "PIL", "psutil", "telegram", "fastapi", "uvicorn",
            "apscheduler", "yaml", "playwright"]
    print("\nPython dependencies:")
    for dep in deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ❌ {dep} (run: pip install -r requirements.txt)")
    
    print("\n✅ Configuration check complete")


def main():
    args = parse_args()
    
    if args.check:
        check_config(args)
        return
    
    try:
        if args.cli:
            asyncio.run(run_cli(args))
        elif args.task:
            asyncio.run(run_single_task(args))
        else:
            asyncio.run(run_server(args))
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")


if __name__ == "__main__":
    main()
