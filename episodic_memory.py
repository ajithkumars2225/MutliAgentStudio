import sqlite3
import json
import os
import time
from typing import Dict, List, Any
import database
from semantic_cache_engine import get_embedding_vector, get_vector_similarity, get_lexical_similarity

class EpisodicMemoryEngine:
    """
    Enterprise Episodic & Long-Term Preference Memory Engine.
    Stores and retrieves past architectural decisions, user preferences, and bug resolutions
    across sessions using vector embeddings and similarity search.
    """

    @staticmethod
    def init_memory_db():
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key_concept TEXT NOT NULL,
            memory_value TEXT NOT NULL,
            embedding TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()

    @classmethod
    def store_memory(cls, category: str, key_concept: str, memory_value: str, provider: str = "google"):
        """
        Stores a long-term memory entry with its vector embedding.
        """
        cls.init_memory_db()
        vec = get_embedding_vector(f"{key_concept}: {memory_value}", provider=provider)
        vec_json = json.dumps(vec) if vec else None

        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO episodic_memory (category, key_concept, memory_value, embedding)
        VALUES (?, ?, ?, ?)
        """, (category, key_concept, memory_value, vec_json))
        conn.commit()
        conn.close()
        print(f"[Episodic Memory] Saved memory under category '{category}': {key_concept}")

    @classmethod
    def recall_relevant_memories(cls, query: str, top_k: int = 3, provider: str = "google") -> List[Dict[str, Any]]:
        """
        Recalls top-k relevant long-term memories matching the user prompt.
        """
        cls.init_memory_db()
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM episodic_memory")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if not rows:
            return []

        query_vec = get_embedding_vector(query, provider=provider)
        scored = []

        for r in rows:
            sim = 0.0
            vec_str = r.get("embedding")
            if query_vec and vec_str:
                try:
                    vec = json.loads(vec_str)
                    if len(vec) == len(query_vec):
                        sim = get_vector_similarity(query_vec, vec)
                except Exception:
                    pass

            lex_sim = get_lexical_similarity(query, f"{r['key_concept']} {r['memory_value']}")
            score = max(sim, lex_sim)

            if score > 0.1:
                scored.append({
                    "id": r["id"],
                    "category": r["category"],
                    "concept": r["key_concept"],
                    "value": r["memory_value"],
                    "score": round(score, 4)
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    @classmethod
    def get_all_memories(cls) -> List[Dict[str, Any]]:
        """
        Returns all stored episodic memories for management in UI.
        """
        cls.init_memory_db()
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, category, key_concept, memory_value, created_at FROM episodic_memory ORDER BY id DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @classmethod
    def delete_memory(cls, memory_id: int):
        """
        Deletes a specific memory entry by ID.
        """
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM episodic_memory WHERE id = ?", (memory_id,))
        conn.commit()
        conn.close()
        print(f"[Episodic Memory] Deleted memory entry #{memory_id}")

