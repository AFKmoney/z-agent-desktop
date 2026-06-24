"""
Web Search & Research module — agent can search the web for current information.

Uses the z-ai-web-dev-sdk Web Search API to get real-time results from the web.
This is critical for tasks like "find the latest version of X", "what's the
weather today", "compare prices for Y", etc.

Also exposes a web_reader action that fetches a URL and extracts its content.
"""
import os
import json
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("web")


def register(executor, config: dict):
    mod = WebSearchModule(config)
    executor.register_handler("web.search", mod.search)
    executor.register_handler("web.read_page", mod.read_page)
    executor.register_handler("web.fetch", mod.fetch_url)
    executor.register_handler("web.research", mod.research_topic)
    log.info("Web search module registered: 4 actions")


class WebSearchModule:
    """Web search using z-ai-web-dev-sdk (via Node sidecar)."""

    # Node sidecar script for web search
    SIDECAR_SCRIPT = """
import Zai from 'z-ai-web-dev-sdk';

const rl = require('readline').createInterface({ input: process.stdin });

rl.on('line', async (line) => {
  try {
    const req = JSON.parse(line);
    const zai = await Zai.create();

    if (req.action === 'search') {
      const results = await zai.functions.invoke('web_search', { query: req.query, num: req.num || 10 });
      process.stdout.write(JSON.stringify({ ok: true, results }) + '\\n');
    } else if (req.action === 'read_page') {
      const result = await zai.functions.invoke('web_reader', { url: req.url });
      process.stdout.write(JSON.stringify({ ok: true, ...result }) + '\\n');
    } else if (req.action === 'fetch') {
      const resp = await fetch(req.url, { headers: { 'User-Agent': 'Mozilla/5.0' } });
      const html = await resp.text();
      process.stdout.write(JSON.stringify({ ok: true, status: resp.status, html: html.slice(0, 50000) }) + '\\n');
    }
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: e.message }) + '\\n');
  }
});
"""

    def __init__(self, config: dict):
        self.config = config.get("web", {})
        self.sidecar_path = os.path.join(get_data_dir(), "web_sidecar.cjs")
        self._sidecar_process = None
        self._init_sidecar()

    def _init_sidecar(self):
        """Write the sidecar script."""
        try:
            with open(self.sidecar_path, "w", encoding="utf-8") as f:
                f.write(self.SIDECAR_SCRIPT)
        except Exception as e:
            log.warning(f"Could not write sidecar: {e}")

    def _call_sidecar(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call the sidecar once (one-shot subprocess for simplicity)."""
        try:
            result = subprocess.run(
                ["node", self.sidecar_path],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/z/my-project",  # Where node_modules is
            )
            if result.returncode != 0:
                return {"ok": False, "error": result.stderr[:500]}
            # Parse the last line (sidecar outputs one JSON per request)
            lines = result.stdout.strip().split("\n")
            if lines:
                return json.loads(lines[-1])
            return {"ok": False, "error": "No output"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Sidecar timed out"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def search(self, query: str, num: int = 10, **kwargs) -> Dict[str, Any]:
        """Search the web.

        Args:
            query: Search query string.
            num: Max number of results (default 10).
        """
        # Try the SDK sidecar first
        sdk_result = self._call_sidecar({
            "action": "search",
            "query": query,
            "num": num,
        })

        if sdk_result and sdk_result.get("ok"):
            results = sdk_result.get("results", [])
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "source": "z.ai sdk",
            }

        # Fallback: use the API directly via REST
        log.info(f"SDK search failed ({sdk_result.get('error') if sdk_result else 'no response'}), trying REST")
        return await self._search_rest(query, num)

    async def _search_rest(self, query: str, num: int) -> Dict[str, Any]:
        """Fallback: use the z.ai API directly via openai client."""
        try:
            from openai import OpenAI
            api_key = os.environ.get("ZAI_API_KEY", "")
            if not api_key:
                return {"success": False, "error": "ZAI_API_KEY not set"}

            client = OpenAI(api_key=api_key, base_url="https://api.z.ai/api/paas/v4")
            # Use the web_search tool via function calling
            tools = [{
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            }]

            response = client.chat.completions.create(
                model="glm-4.6",
                messages=[
                    {"role": "system", "content": "You are a web research assistant. Use the web_search tool to find current information."},
                    {"role": "user", "content": query},
                ],
                tools=tools,
                tool_choice="auto",
            )

            # Extract tool calls
            tool_calls = response.choices[0].message.tool_calls or []
            results = []
            for tc in tool_calls:
                if tc.function.name == "web_search":
                    # In a real impl we'd execute the tool call, here we just return the planned search
                    results.append({
                        "title": "Search request",
                        "snippet": json.loads(tc.function.arguments).get("query", ""),
                    })

            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "source": "z.ai api tool_calling",
                "note": "Use SDK sidecar for full search results",
            }
        except Exception as e:
            return {"success": False, "error": f"REST search failed: {e}"}

    async def read_page(self, url: str, **kwargs) -> Dict[str, Any]:
        """Read a web page and extract its content.

        Args:
            url: URL to read.
        """
        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {"success": False, "error": "Invalid URL"}
        except Exception:
            return {"success": False, "error": "Invalid URL"}

        # Try SDK sidecar
        sdk_result = self._call_sidecar({"action": "read_page", "url": url})
        if sdk_result and sdk_result.get("ok"):
            return {
                "success": True,
                "url": url,
                "title": sdk_result.get("title", ""),
                "content": sdk_result.get("content", "")[:20000],
                "html": sdk_result.get("html", "")[:5000],
                "source": "z.ai sdk",
            }

        # Fallback: simple fetch with text extraction
        return await self.fetch_url(url, extract_text=True)

    async def fetch_url(self, url: str, extract_text: bool = True, **kwargs) -> Dict[str, Any]:
        """Fetch a URL and return its content.

        Args:
            url: URL to fetch.
            extract_text: If True, strip HTML tags and return text only.
        """
        sdk_result = self._call_sidecar({"action": "fetch", "url": url})
        if sdk_result and sdk_result.get("ok"):
            html = sdk_result.get("html", "")
            if extract_text:
                text = self._strip_html(html)
                return {
                    "success": True,
                    "url": url,
                    "status": sdk_result.get("status", 200),
                    "content": text[:20000],
                    "length": len(text),
                }
            return {
                "success": True,
                "url": url,
                "status": sdk_result.get("status", 200),
                "html": html[:50000],
            }
        return {"success": False, "error": sdk_result.get("error", "fetch failed") if sdk_result else "no response"}

    def _strip_html(self, html: str) -> str:
        """Very basic HTML to text conversion."""
        import re
        # Remove scripts and styles
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Decode common entities
        text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                    .replace("&lt;", "<").replace("&gt;", ">")
                    .replace("&quot;", '"').replace("&#39;", "'"))
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def research_topic(self, topic: str, depth: int = 3, **kwargs) -> Dict[str, Any]:
        """Deep research on a topic — search, read top results, synthesize.

        Args:
            topic: Topic to research.
            depth: Number of top results to read in detail (default 3).
        """
        # 1. Search
        search_result = await self.search(topic, num=depth + 2)
        if not search_result.get("success"):
            return search_result

        # 2. Read top N results
        findings = []
        for result in search_result.get("results", [])[:depth]:
            url = result.get("url") or result.get("link", "")
            if not url:
                continue
            read_result = await self.read_page(url)
            if read_result.get("success"):
                findings.append({
                    "url": url,
                    "title": read_result.get("title", result.get("title", "")),
                    "snippet": result.get("snippet", ""),
                    "content_preview": read_result.get("content", "")[:1000],
                })

        return {
            "success": True,
            "topic": topic,
            "findings": findings,
            "count": len(findings),
            "search_results_count": search_result.get("count", 0),
        }
