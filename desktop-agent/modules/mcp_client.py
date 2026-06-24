"""
MCP (Model Context Protocol) integration — connect external tool servers.

MCP is Anthropic's open protocol for connecting AI models to external tools,
data sources, and services. With this module, the agent can:
  - Connect to MCP servers (filesystem, GitHub, Slack, database, etc.)
  - Discover tools exposed by each server
  - Call MCP tools from the ReAct loop
  - Aggregate tools from multiple servers

This effectively turns Z.AGENT into an MCP client that can use any
MCP-compatible tool server, dramatically extending its capabilities.

Popular MCP servers include:
  - @modelcontextprotocol/server-filesystem (file system access)
  - @modelcontextprotocol/server-github (GitHub API)
  - @modelcontextprotocol/server-postgres (PostgreSQL)
  - @modelcontextprotocol/server-slack (Slack API)
  - @modelcontextprotocol/server-puppeteer (browser automation)
  - And many more: https://github.com/modelcontextprotocol/servers

Each MCP server is configured in config.yaml under 'mcp.servers'.
"""
import os
import json
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("mcp")


def register(executor, config: dict):
    mod = McpClient(config)
    executor.register_handler("mcp.list_servers", mod.list_servers_action)
    executor.register_handler("mcp.list_tools", mod.list_tools_action)
    executor.register_handler("mcp.call_tool", mod.call_tool_action)
    executor.register_handler("mcp.connect", mod.connect_server_action)
    executor.register_handler("mcp.disconnect", mod.disconnect_server_action)
    log.info(f"MCP module registered: 5 actions ({len(mod.servers)} servers configured)")


class McpServer:
    """Represents an MCP server connection."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.command = config.get("command", "")
        self.args = config.get("args", [])
        self.env = config.get("env", {})
        self.enabled = config.get("enabled", True)
        self._process: Optional[subprocess.Popen] = None
        self._tools: List[Dict[str, Any]] = []

    def start(self) -> bool:
        """Start the MCP server process."""
        if self._process and self._process.poll() is None:
            return True  # Already running

        if not self.command:
            log.warning(f"MCP server '{self.name}' has no command")
            return False

        try:
            env = {**os.environ, **self.env}
            self._process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
            )
            log.info(f"MCP server '{self.name}' started (PID {self._process.pid})")
            return True
        except Exception as e:
            log.error(f"Failed to start MCP server '{self.name}': {e}")
            return False

    def stop(self):
        """Stop the MCP server process."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            self._process = None
            log.info(f"MCP server '{self.name}' stopped")

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request to the server and read one response."""
        if not self.is_running():
            return None
        try:
            self._process.stdin.write(json.dumps(request) + "\n")
            self._process.stdin.flush()
            line = self._process.stdout.readline()
            if not line:
                return None
            return json.loads(line)
        except Exception as e:
            log.error(f"MCP request to '{self.name}' failed: {e}")
            return None

    def list_tools(self) -> List[Dict[str, Any]]:
        """Discover tools exposed by this server."""
        if not self.is_running() and not self.start():
            return []

        response = self.send_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
        })
        if response and "result" in response:
            self._tools = response["result"].get("tools", [])
            return self._tools
        return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on this server."""
        if not self.is_running() and not self.start():
            return {"error": "Server not running"}

        response = self.send_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        })

        if response and "result" in response:
            return response["result"]
        elif response and "error" in response:
            return {"error": response["error"].get("message", "Unknown error")}
        return {"error": "No response from server"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "enabled": self.enabled,
            "running": self.is_running(),
            "tool_count": len(self._tools),
            "tools": [t.get("name") for t in self._tools],
        }


class McpClient:
    """MCP client — manages multiple MCP server connections."""

    def __init__(self, config: dict):
        mcp_cfg = config.get("mcp") or {}
        self.config = mcp_cfg
        self.servers: Dict[str, McpServer] = {}
        servers = self.config.get("servers") or {}
        for name, server_cfg in servers.items():
            self.servers[name] = McpServer(name, server_cfg)

    async def list_servers_action(self, **kwargs) -> Dict[str, Any]:
        """List configured MCP servers."""
        return {
            "success": True,
            "servers": [s.to_dict() for s in self.servers.values()],
            "count": len(self.servers),
        }

    async def list_tools_action(self, server_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """List tools from one or all MCP servers."""
        if server_name:
            if server_name not in self.servers:
                return {"success": False, "error": f"Server '{server_name}' not found"}
            tools = self.servers[server_name].list_tools()
            return {
                "success": True,
                "server": server_name,
                "tools": tools,
                "count": len(tools),
            }
        else:
            # All servers
            all_tools = {}
            for name, server in self.servers.items():
                if server.enabled:
                    all_tools[name] = server.list_tools()
            return {
                "success": True,
                "servers": all_tools,
                "total_count": sum(len(t) for t in all_tools.values()),
            }

    async def call_tool_action(
        self,
        server_name: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call a tool on an MCP server.

        Args:
            server_name: Name of the MCP server (configured in config.yaml).
            tool_name: Tool name (discoverable via mcp.list_tools).
            arguments: Tool arguments as a dict.
        """
        if server_name not in self.servers:
            return {"success": False, "error": f"Server '{server_name}' not found"}

        server = self.servers[server_name]
        if not server.enabled:
            return {"success": False, "error": f"Server '{server_name}' is disabled"}

        result = server.call_tool(tool_name, arguments or {})
        return {
            "success": "error" not in result,
            "server": server_name,
            "tool": tool_name,
            "result": result,
        }

    async def connect_server_action(self, server_name: str, **kwargs) -> Dict[str, Any]:
        """Manually start/connect an MCP server."""
        if server_name not in self.servers:
            return {"success": False, "error": "Server not configured"}
        ok = self.servers[server_name].start()
        return {"success": ok, "server": server_name}

    async def disconnect_server_action(self, server_name: str, **kwargs) -> Dict[str, Any]:
        """Disconnect an MCP server."""
        if server_name not in self.servers:
            return {"success": False, "error": "Server not configured"}
        self.servers[server_name].stop()
        return {"success": True, "server": server_name}

    def get_all_tools_for_planner(self) -> List[str]:
        """Get all tool names from all servers (for planner context)."""
        tool_names = []
        for server in self.servers.values():
            if server.enabled:
                for tool in server._tools:
                    name = tool.get("name", "")
                    if name:
                        tool_names.append(f"mcp.{server.name}.{name}")
        return tool_names

    def stop_all(self):
        """Stop all MCP servers (on agent shutdown)."""
        for server in self.servers.values():
            server.stop()
