"""
Knowledge Base / RAG — embed documents for semantic search.

Lets the agent reference the user's documents when answering:
  - "What does our security policy say about X?"
  - "Find the meeting notes where we discussed Y"
  - "Summarize the contract from /Documents/contract.pdf"

Implementation:
  - Documents are chunked (1000 chars, 200 overlap)
  - Chunks are embedded via z.ai embeddings API (or local sentence-transformers)
  - Embeddings stored in a local vector store (simple JSON file with numpy)
  - Semantic search via cosine similarity
  - Top-K chunks injected into the planner's context

Supported formats:
  - .txt, .md (plain text)
  - .pdf (via PyPDF2)
  - .docx (via python-docx)
  - .csv, .json (structured)
"""
import os
import json
import time
import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("knowledge")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    log.warning("numpy not installed — knowledge base disabled")


def register(executor, config: dict):
    if not NUMPY_AVAILABLE:
        log.info("Knowledge base module not registered — install numpy")
        return

    mod = KnowledgeBase(config)
    executor.register_handler("kb.add_document", mod.add_document_action)
    executor.register_handler("kb.search", mod.search_action)
    executor.register_handler("kb.list_documents", mod.list_documents_action)
    executor.register_handler("kb.delete_document", mod.delete_document_action)
    executor.register_handler("kb.get_stats", mod.get_stats_action)
    log.info("Knowledge base module registered: 5 actions")


class KnowledgeBase:
    """RAG knowledge base with local vector store."""

    def __init__(self, config: dict):
        self.config = config.get("knowledge_base", {})
        self.chunk_size = self.config.get("chunk_size", 1000)
        self.chunk_overlap = self.config.get("chunk_overlap", 200)
        self.top_k = self.config.get("top_k", 5)
        self.data_dir = Path(get_data_dir()) / "knowledge_base"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.store_file = self.data_dir / "store.json"
        self.embeddings_file = self.data_dir / "embeddings.npy"
        self.documents: Dict[str, Dict[str, Any]] = self._load_store()
        self.embeddings: Optional[List[List[float]]] = self._load_embeddings()
        self.chunk_index: List[Dict[str, Any]] = self._build_chunk_index()

    def _load_store(self) -> Dict[str, Dict[str, Any]]:
        if not self.store_file.exists():
            return {}
        try:
            with open(self.store_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_embeddings(self) -> Optional[List[List[float]]]:
        if not self.embeddings_file.exists():
            return None
        try:
            arr = np.load(self.embeddings_file)
            return arr.tolist()
        except Exception:
            return None

    def _save_store(self):
        with open(self.store_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)

    def _save_embeddings(self):
        if self.embeddings:
            arr = np.array(self.embeddings, dtype=np.float32)
            np.save(self.embeddings_file, arr)

    def _build_chunk_index(self) -> List[Dict[str, Any]]:
        """Flatten documents into a chunk index."""
        index = []
        for doc_id, doc in self.documents.items():
            for i, chunk in enumerate(doc.get("chunks", [])):
                index.append({
                    "doc_id": doc_id,
                    "chunk_idx": i,
                    "text": chunk["text"],
                    "page": chunk.get("page"),
                    "embedding_idx": chunk.get("embedding_idx"),
                })
        return index

    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"text": chunk_text, "page": None})
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        return chunks

    def _extract_text(self, file_path: str) -> str:
        """Extract text from a file based on its extension."""
        ext = Path(file_path).suffix.lower()

        if ext in {".txt", ".md", ".log", ".csv", ".json", ".yaml", ".yml"}:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        if ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                return "\n\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                return f"[PDF parsing requires pypdf: pip install pypdf] ({file_path})"

        if ext == ".docx":
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                return f"[DOCX parsing requires python-docx] ({file_path})"

        # Fallback: try as text
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for a text via z.ai API."""
        try:
            from openai import OpenAI
            api_key = os.environ.get("ZAI_API_KEY", "")
            if not api_key:
                # Return a simple hash-based fake embedding (for testing only)
                return self._fake_embedding(text)

            client = OpenAI(api_key=api_key, base_url="https://api.z.ai/api/paas/v4")
            response = client.embeddings.create(
                model="embedding-3",
                input=text[:8000],  # Truncate to API limit
            )
            return response.data[0].embedding
        except Exception as e:
            log.warning(f"Embedding API failed: {e}, using fake embedding")
            return self._fake_embedding(text)

    def _fake_embedding(self, text: str) -> List[float]:
        """Generate a deterministic fake embedding (for offline testing)."""
        # Simple hash-based 256-dim embedding
        h = hashlib.sha256(text.encode()).digest()
        vec = [(b - 128) / 128 for b in h]
        # Pad to 256
        while len(vec) < 256:
            h = hashlib.sha256(h).digest()
            vec.extend([(b - 128) / 128 for b in h])
        return vec[:256]

    async def add_document(
        self,
        file_path: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a document to the knowledge base."""
        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found"}

        text = self._extract_text(file_path)
        if not text.strip():
            return {"success": False, "error": "Could not extract text"}

        chunks = self._chunk_text(text)
        if not chunks:
            return {"success": False, "error": "No chunks generated"}

        # Generate embeddings for each chunk
        doc_id = f"doc_{int(time.time() * 1000)}"
        doc_name = name or Path(file_path).name

        log.info(f"Embedding {len(chunks)} chunks for '{doc_name}'...")
        embeddings = []
        for i, chunk in enumerate(chunks):
            emb = await self._get_embedding(chunk["text"])
            embeddings.append(emb)
            chunk["embedding_idx"] = len(self.embeddings or []) + i
            if (i + 1) % 10 == 0:
                log.debug(f"  Embedded {i + 1}/{len(chunks)}")

        # Update global embeddings
        if self.embeddings is None:
            self.embeddings = []
        self.embeddings.extend(embeddings)

        # Store document
        self.documents[doc_id] = {
            "id": doc_id,
            "name": doc_name,
            "path": file_path,
            "size": os.path.getsize(file_path),
            "chunk_count": len(chunks),
            "chunks": chunks,
            "metadata": metadata or {},
            "added_at": time.time(),
        }
        self._save_store()
        self._save_embeddings()
        self.chunk_index = self._build_chunk_index()

        log.info(f"Document added: {doc_name} ({len(chunks)} chunks)")
        return {
            "success": True,
            "doc_id": doc_id,
            "name": doc_name,
            "chunks": len(chunks),
        }

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Semantic search across the knowledge base."""
        if not self.embeddings or not self.chunk_index:
            return {"success": True, "results": [], "count": 0}

        # Embed the query
        query_emb = await self._get_embedding(query)

        # Cosine similarity
        query_arr = np.array(query_emb, dtype=np.float32)
        emb_arr = np.array(self.embeddings, dtype=np.float32)

        # Normalize
        query_norm = query_arr / (np.linalg.norm(query_arr) + 1e-8)
        emb_norms = emb_arr / (np.linalg.norm(emb_arr, axis=1, keepdims=True) + 1e-8)

        similarities = np.dot(emb_norms, query_norm)

        # Top-K
        k = top_k or self.top_k
        top_indices = np.argsort(similarities)[-k:][::-1]

        results = []
        for idx in top_indices:
            if idx < len(self.chunk_index):
                chunk = self.chunk_index[idx]
                doc = self.documents.get(chunk["doc_id"], {})
                results.append({
                    "doc_id": chunk["doc_id"],
                    "doc_name": doc.get("name", "unknown"),
                    "text": chunk["text"][:500],
                    "score": float(similarities[idx]),
                    "chunk_idx": chunk["chunk_idx"],
                })

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
        }

    def list_documents(self) -> Dict[str, Any]:
        """List all documents in the knowledge base."""
        docs = [
            {
                "id": d["id"],
                "name": d["name"],
                "size": d["size"],
                "chunks": d["chunk_count"],
                "added_at": d["added_at"],
                "metadata": d.get("metadata", {}),
            }
            for d in self.documents.values()
        ]
        return {"success": True, "documents": docs, "count": len(docs)}

    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """Delete a document from the knowledge base."""
        if doc_id not in self.documents:
            return {"success": False, "error": "Document not found"}

        doc = self.documents[doc_id]
        # Remove embeddings for this doc's chunks
        chunks_to_remove = [c["embedding_idx"] for c in doc.get("chunks", []) if c.get("embedding_idx") is not None]
        chunks_to_remove.sort(reverse=True)
        if self.embeddings:
            for idx in chunks_to_remove:
                if idx < len(self.embeddings):
                    self.embeddings.pop(idx)

        del self.documents[doc_id]
        self._save_store()
        self._save_embeddings()
        self.chunk_index = self._build_chunk_index()

        return {"success": True, "doc_id": doc_id}

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        total_chunks = sum(d["chunk_count"] for d in self.documents.values())
        total_size = sum(d["size"] for d in self.documents.values())
        return {
            "success": True,
            "document_count": len(self.documents),
            "total_chunks": total_chunks,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "embedding_dim": len(self.embeddings[0]) if self.embeddings else 0,
        }

    def get_context_for_planner(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Get relevant context for the planner (synchronous wrapper)."""
        # Run the async search in a sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context — can't easily call async from sync
                # Return empty for now (the planner should call kb.search directly)
                return []
        except RuntimeError:
            pass

        try:
            result = asyncio.run(self.search(query, top_k=top_k))
            return result.get("results", [])
        except Exception as e:
            log.warning(f"Knowledge base context retrieval failed: {e}")
            return []

    # === Async wrappers for executor ===
    async def add_document_action(self, file_path: str, name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        return await self.add_document(file_path, name)

    async def search_action(self, query: str, top_k: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        return await self.search(query, top_k)

    async def list_documents_action(self, **kwargs) -> Dict[str, Any]:
        return self.list_documents()

    async def delete_document_action(self, doc_id: str, **kwargs) -> Dict[str, Any]:
        return self.delete_document(doc_id)

    async def get_stats_action(self, **kwargs) -> Dict[str, Any]:
        return self.get_stats()
