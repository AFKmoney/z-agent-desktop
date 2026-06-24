"""
Persistent Vector Memory — long-term semantic memory using embeddings.

Unlike the regular Memory class (which stores key-value facts), this module
stores SEMANTIC memories: the agent can recall "what did I learn about X"
without knowing the exact key.

Use cases:
  - "What do I know about the user's preferences?"
  - "What did I learn from past email tasks?"
  - "How did I solve a similar problem before?"

Each memory is:
  - text content (the actual memory)
  - embedding (vector for semantic search)
  - metadata (type, tags, source, timestamp)
  - importance score (decays over time, boosted when recalled)

Implemented as a simple local vector store (numpy + JSON).
"""
import os
import json
import time
import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("vector_memory")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class VectorMemory:
    """Long-term semantic memory with embeddings."""

    def __init__(self, config: dict):
        self.config = config.get("vector_memory", {})
        self.enabled = self.config.get("enabled", True) and NUMPY_AVAILABLE
        if not self.enabled:
            log.info("Vector memory disabled (numpy missing or config disabled)")
            return

        self.data_dir = Path(get_data_dir()) / "vector_memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memories_file = self.data_dir / "memories.json"
        self.embeddings_file = self.data_dir / "embeddings.npy"

        self.memories: List[Dict[str, Any]] = self._load_memories()
        self.embeddings: Optional[List[List[float]]] = self._load_embeddings()
        self._subscribers: List[callable] = []

    def _load_memories(self) -> List[Dict[str, Any]]:
        if not self.memories_file.exists():
            return []
        try:
            with open(self.memories_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _load_embeddings(self) -> Optional[List[List[float]]]:
        if not self.embeddings_file.exists():
            return None
        try:
            return np.load(self.embeddings_file).tolist()
        except Exception:
            return None

    def _save(self):
        try:
            with open(self.memories_file, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, indent=2, ensure_ascii=False)
            if self.embeddings:
                arr = np.array(self.embeddings, dtype=np.float32)
                np.save(self.embeddings_file, arr)
        except Exception as e:
            log.error(f"Could not save vector memory: {e}")

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding via the multi-LLM provider (falls back to hash)."""
        try:
            from core.llm_provider import get_llm_provider
            provider = get_llm_provider()
            if provider:
                # Try z.ai embeddings first
                import os
                api_key = os.environ.get("ZAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
                if api_key:
                    from openai import OpenAI
                    base_url = "https://api.z.ai/api/paas/v4" if os.environ.get("ZAI_API_KEY") else "https://api.openai.com/v1"
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    response = client.embeddings.create(model="embedding-3", input=text[:8000])
                    return response.data[0].embedding
        except Exception:
            pass
        # Fallback: hash-based fake embedding
        return self._fake_embedding(text)

    def _fake_embedding(self, text: str) -> List[float]:
        """Deterministic fake embedding for offline mode."""
        h = hashlib.sha256(text.encode()).digest()
        vec = [(b - 128) / 128 for b in h]
        while len(vec) < 256:
            h = hashlib.sha256(h).digest()
            vec.extend([(b - 128) / 128 for b in h])
        return vec[:256]

    async def remember(
        self,
        text: str,
        memory_type: str = "fact",
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        source: str = "agent",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store a new semantic memory."""
        if not self.enabled:
            return {"success": False, "error": "Vector memory disabled"}

        embedding = await self._get_embedding(text)

        memory = {
            "id": f"mem_{int(time.time() * 1000)}_{hashlib.md5(text.encode()).hexdigest()[:8]}",
            "text": text,
            "type": memory_type,
            "tags": tags or [],
            "importance": importance,
            "source": source,
            "metadata": metadata or {},
            "created_at": time.time(),
            "last_recalled": None,
            "recall_count": 0,
        }

        self.memories.append(memory)
        if self.embeddings is None:
            self.embeddings = []
        self.embeddings.append(embedding)
        self._save()

        # Notify subscribers
        for cb in self._subscribers:
            try:
                cb(memory)
            except Exception:
                pass

        log.debug(f"Memory stored: {text[:60]}... (type={memory_type})")
        return {"success": True, "memory_id": memory["id"]}

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_importance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Recall relevant memories semantically."""
        if not self.enabled or not self.memories or not self.embeddings:
            return []

        query_emb = await self._get_embedding(query)

        query_arr = np.array(query_emb, dtype=np.float32)
        emb_arr = np.array(self.embeddings, dtype=np.float32)

        query_norm = query_arr / (np.linalg.norm(query_arr) + 1e-8)
        emb_norms = emb_arr / (np.linalg.norm(emb_arr, axis=1, keepdims=True) + 1e-8)
        similarities = np.dot(emb_norms, query_norm)

        # Boost recent + frequently recalled memories
        now = time.time()
        scores = []
        for i, mem in enumerate(self.memories):
            sim = float(similarities[i])
            # Importance boost
            imp_boost = mem.get("importance", 0.5) * 0.2
            # Recency boost (memories from last 7 days get a small boost)
            age_days = (now - mem.get("created_at", now)) / 86400
            recency_boost = max(0, 0.1 - age_days * 0.014)  # 0.1 at 0 days, 0 at 7 days
            # Recall frequency boost (memories often recalled are more relevant)
            freq_boost = min(0.1, mem.get("recall_count", 0) * 0.02)

            # Filters
            if memory_type and mem.get("type") != memory_type:
                continue
            if tags and not any(t in mem.get("tags", []) for t in tags):
                continue
            if mem.get("importance", 0.5) < min_importance:
                continue

            scores.append((sim + imp_boost + recency_boost + freq_boost, i))

        scores.sort(reverse=True)
        results = []
        for score, idx in scores[:top_k]:
            mem = self.memories[idx].copy()
            mem["score"] = score
            # Update recall stats
            self.memories[idx]["last_recalled"] = now
            self.memories[idx]["recall_count"] = self.memories[idx].get("recall_count", 0) + 1
            results.append(mem)

        self._save()
        return results

    def list_memories(
        self,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List memories with optional filters."""
        results = self.memories
        if memory_type:
            results = [m for m in results if m.get("type") == memory_type]
        if tags:
            results = [m for m in results if any(t in m.get("tags", []) for t in tags)]
        return results[-limit:]

    def forget(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        for i, m in enumerate(self.memories):
            if m["id"] == memory_id:
                self.memories.pop(i)
                if self.embeddings and i < len(self.embeddings):
                    self.embeddings.pop(i)
                self._save()
                return True
        return False

    def forget_all(self, memory_type: Optional[str] = None):
        """Clear all memories (optionally of a specific type)."""
        if memory_type:
            keep = [(m, e) for m, e in zip(self.memories, self.embeddings or [])
                    if m.get("type") != memory_type]
            self.memories = [k[0] for k in keep]
            self.embeddings = [k[1] for k in keep] if keep else None
        else:
            self.memories = []
            self.embeddings = None
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        type_counts: Dict[str, int] = {}
        for m in self.memories:
            t = m.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_memories": len(self.memories),
            "by_type": type_counts,
            "embedding_dim": len(self.embeddings[0]) if self.embeddings else 0,
            "oldest_memory": min((m["created_at"] for m in self.memories), default=None),
            "most_recalled": max(self.memories, key=lambda m: m.get("recall_count", 0), default=None),
        }

    def get_context_for_planner(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Get relevant memories to include in the planner's context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return []
        except RuntimeError:
            pass

        try:
            memories = asyncio.run(self.recall(query, top_k=top_k))
            return [
                {
                    "text": m["text"],
                    "type": m.get("type"),
                    "score": m.get("score"),
                    "tags": m.get("tags", []),
                }
                for m in memories
            ]
        except Exception as e:
            log.warning(f"Memory recall failed: {e}")
            return []


# Global instance
_vector_memory: Optional[VectorMemory] = None


def init_vector_memory(config: dict) -> VectorMemory:
    global _vector_memory
    _vector_memory = VectorMemory(config)
    return _vector_memory


def get_vector_memory() -> Optional[VectorMemory]:
    return _vector_memory
