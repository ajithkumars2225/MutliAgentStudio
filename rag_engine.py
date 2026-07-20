import json
import math
import os
from pathlib import Path
from typing import Dict, List, Any
import database
from semantic_cache_engine import get_embedding_vector, get_vector_similarity, get_lexical_similarity
from ast_engine import EnterpriseASTEngine

class CodebaseRAGEngine:
    """
    Enterprise Codebase RAG Vector Engine
    Chunks codebase files, indexes semantic embeddings, and performs
    vector similarity retrieval for agent context window augmentation.
    """

    @staticmethod
    def chunk_file_content(filepath: str, content: str) -> List[Dict[str, Any]]:
        """
        AST-driven Code Chunker.
        Chunks files by AST function/class definitions, or 600-character logical windows.
        """
        chunks = []
        syms = EnterpriseASTEngine.parse_polyglot_symbols(filepath, content)
        
        lines = content.splitlines()

        # Try chunking by functions/classes if Python/JS
        funcs = syms.get("functions", [])
        classes = syms.get("classes", [])

        if funcs or classes:
            for f in funcs:
                name = f.get("name")
                line_no = f.get("line", 1)
                # Extract 20 lines starting at function line
                start = max(0, line_no - 1)
                end = min(len(lines), start + 25)
                chunk_str = "\n".join(lines[start:end])
                if chunk_str.strip():
                    chunks.append({
                        "filepath": filepath,
                        "symbol_name": f"func:{name}",
                        "chunk_text": chunk_str
                    })
            for c in classes:
                name = c.get("name")
                line_no = c.get("line", 1)
                start = max(0, line_no - 1)
                end = min(len(lines), start + 30)
                chunk_str = "\n".join(lines[start:end])
                if chunk_str.strip():
                    chunks.append({
                        "filepath": filepath,
                        "symbol_name": f"class:{name}",
                        "chunk_text": chunk_str
                    })

        # Fallback to sliding window chunking if no symbols or small file
        if not chunks:
            chunk_size = 600
            overlap = 100
            step = chunk_size - overlap
            for i in range(0, len(content), step):
                chunk_str = content[i:i + chunk_size]
                if chunk_str.strip():
                    chunks.append({
                        "filepath": filepath,
                        "symbol_name": f"window:{i//step}",
                        "chunk_text": chunk_str
                    })

        return chunks

    @classmethod
    def index_workspace(cls, workspace_directory: str, provider: str = "google") -> int:
        """
        Indexes all active workspace code files into the Codebase RAG Vector Database.
        """
        base = Path(workspace_directory).resolve()
        if not base.exists():
            return 0

        database.init_db()
        database.clear_rag_chunks(str(base))
        all_chunks = []

        exclude_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}
        allowed_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".sql", ".cs", ".json"}

        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                filepath = Path(root) / file
                if filepath.suffix.lower() in allowed_exts:
                    try:
                        rel_path = str(filepath.relative_to(base)).replace("\\", "/")
                        content = filepath.read_text(encoding="utf-8", errors="ignore")
                        file_chunks = cls.chunk_file_content(rel_path, content)
                        all_chunks.extend(file_chunks)
                    except Exception:
                        pass

        # Generate vectors for chunks (or fallback to TF-IDF)
        for chunk in all_chunks:
            # Short preview for embedding generator
            vector = get_embedding_vector(chunk["chunk_text"][:500], provider=provider)
            chunk["embedding"] = json.dumps(vector) if vector else None

        database.save_rag_chunks(str(base), all_chunks)
        print(f"[Codebase RAG Engine] Successfully indexed {len(all_chunks)} code chunks into vector database.")
        return len(all_chunks)

    @classmethod
    def search_codebase_rag(cls, workspace_directory: str, prompt: str, top_k: int = 4, provider: str = "google") -> List[Dict[str, Any]]:
        """
        Performs semantic vector search over codebase chunks for any prompt.
        """
        base = str(Path(workspace_directory).resolve())
        chunks = database.get_rag_chunks(base)
        
        # Auto-index if database empty
        if not chunks:
            count = cls.index_workspace(base, provider=provider)
            if count == 0:
                return []
            chunks = database.get_rag_chunks(base)

        prompt_vector = get_embedding_vector(prompt, provider=provider)
        scored_chunks = []

        for c in chunks:
            sim = 0.0
            chunk_vec_str = c.get("embedding")
            
            # 1. API Vector Similarity
            if prompt_vector and chunk_vec_str:
                try:
                    chunk_vec = json.loads(chunk_vec_str)
                    if isinstance(chunk_vec, list) and len(chunk_vec) == len(prompt_vector):
                        sim = get_vector_similarity(prompt_vector, chunk_vec)
                except Exception:
                    pass

            # 2. Lexical Similarity Fallback / Hybrid Boost
            lexical_sim = get_lexical_similarity(prompt, c["chunk_text"])
            final_score = max(sim, lexical_sim)

            if final_score > 0.15:
                scored_chunks.append({
                    "filepath": c["filepath"],
                    "symbol_name": c.get("symbol_name"),
                    "score": round(final_score, 4),
                    "snippet": c["chunk_text"]
                })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]
