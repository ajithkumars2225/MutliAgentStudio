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
    Enterprise Codebase RAG Vector Engine (v2)
    Provides AST Parent-Child Context Enriched Chunking, Reciprocal Rank Fusion (RRF) Reranking,
    and Incremental Delta Indexing for production multi-agent workflows.
    """

    @staticmethod
    def chunk_file_content(filepath: str, content: str) -> List[Dict[str, Any]]:
        """
        RAG v2 Parent-Child Context Enriched Chunker.
        Prepends AST metadata headers to chunks to preserve semantic context.
        """
        chunks = []
        syms = EnterpriseASTEngine.parse_polyglot_symbols(filepath, content)
        lines = content.splitlines()

        funcs = syms.get("functions", [])
        classes = syms.get("classes", [])

        if funcs or classes:
            for f in funcs:
                name = f.get("name")
                line_no = f.get("line", 1)
                start = max(0, line_no - 1)
                end = min(len(lines), start + 25)
                body = "\n".join(lines[start:end])
                if body.strip():
                    # Parent-Child AST Context Header
                    header = f"# Context: File={filepath} | Function={name} | Params={f.get('params', [])}\n"
                    chunks.append({
                        "filepath": filepath,
                        "symbol_name": f"func:{name}",
                        "chunk_text": header + body
                    })
            for c in classes:
                name = c.get("name")
                line_no = c.get("line", 1)
                start = max(0, line_no - 1)
                end = min(len(lines), start + 30)
                body = "\n".join(lines[start:end])
                if body.strip():
                    header = f"# Context: File={filepath} | Class={name} | Methods={c.get('methods', [])}\n"
                    chunks.append({
                        "filepath": filepath,
                        "symbol_name": f"class:{name}",
                        "chunk_text": header + body
                    })

        # Fallback sliding window chunking with context header
        if not chunks:
            chunk_size = 600
            overlap = 100
            step = chunk_size - overlap
            for i in range(0, len(content), step):
                chunk_body = content[i:i + chunk_size]
                if chunk_body.strip():
                    header = f"# Context: File={filepath} | Offset={i}\n"
                    chunks.append({
                        "filepath": filepath,
                        "symbol_name": f"window:{i//step}",
                        "chunk_text": header + chunk_body
                    })

        return chunks

    @classmethod
    def index_workspace(cls, workspace_directory: str, provider: str = "google") -> int:
        """
        Indexes workspace files into Codebase RAG Database with AST Context Headers.
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

        # Generate embedding vectors
        for chunk in all_chunks:
            vector = get_embedding_vector(chunk["chunk_text"][:500], provider=provider)
            chunk["embedding"] = json.dumps(vector) if vector else None

        database.save_rag_chunks(str(base), all_chunks)
        print(f"[Codebase RAG Engine] Successfully indexed {len(all_chunks)} code chunks into vector database.")
        return len(all_chunks)

    @classmethod
    def apply_rrf_reranking(cls, vector_matches: List[Dict[str, Any]], lexical_matches: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
        """
        RAG v2 Reciprocal Rank Fusion (RRF) Reranker.
        Combines Dense Vector Ranks and Sparse Lexical Ranks into unified relevance scores.
        RRF_Score(d) = (1 / (k + rank_vector)) + (1 / (k + rank_lexical))
        """
        scores = {}
        chunks_map = {}

        # 1. Process Vector ranks
        for rank, item in enumerate(vector_matches, 1):
            cid = f"{item['filepath']}::{item.get('symbol_name')}"
            chunks_map[cid] = item
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank))

        # 2. Process Lexical ranks
        for rank, item in enumerate(lexical_matches, 1):
            cid = f"{item['filepath']}::{item.get('symbol_name')}"
            chunks_map[cid] = item
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank))

        reranked = []
        for cid, score in scores.items():
            item = chunks_map[cid].copy()
            item["rrf_score"] = round(score, 6)
            reranked.append(item)

        reranked.sort(key=lambda x: x["rrf_score"], reverse=True)
        return reranked

    @classmethod
    def search_codebase_rag(cls, workspace_directory: str, prompt: str, top_k: int = 4, provider: str = "google") -> List[Dict[str, Any]]:
        """
        Performs Hybrid Dense-Sparse RRF Semantic Reranking Search over codebase chunks.
        """
        base = str(Path(workspace_directory).resolve())
        chunks = database.get_rag_chunks(base)
        
        if not chunks:
            count = cls.index_workspace(base, provider=provider)
            if count == 0:
                return []
            chunks = database.get_rag_chunks(base)

        prompt_vector = get_embedding_vector(prompt, provider=provider)
        vector_candidates = []
        lexical_candidates = []

        for c in chunks:
            sim = 0.0
            chunk_vec_str = c.get("embedding")
            
            if prompt_vector and chunk_vec_str:
                try:
                    chunk_vec = json.loads(chunk_vec_str)
                    if isinstance(chunk_vec, list) and len(chunk_vec) == len(prompt_vector):
                        sim = get_vector_similarity(prompt_vector, chunk_vec)
                except Exception:
                    pass

            lexical_sim = get_lexical_similarity(prompt, c["chunk_text"])

            candidate = {
                "filepath": c["filepath"],
                "symbol_name": c.get("symbol_name"),
                "score": round(max(sim, lexical_sim), 4),
                "snippet": c["chunk_text"]
            }

            if sim > 0.01:
                vector_candidates.append((sim, candidate))
            if lexical_sim > 0.01:
                lexical_candidates.append((lexical_sim, candidate))

        # Sort individual candidate lists to compute RRF ranks
        vector_candidates.sort(key=lambda x: x[0], reverse=True)
        lexical_candidates.sort(key=lambda x: x[0], reverse=True)

        vec_list = [c[1] for c in vector_candidates[:20]]
        lex_list = [c[1] for c in lexical_candidates[:20]]

        if vec_list or lex_list:
            final_reranked = cls.apply_rrf_reranking(vec_list, lex_list)
            return final_reranked[:top_k]

        return []
