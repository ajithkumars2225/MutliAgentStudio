import os
import json
import math
import re
import requests
from collections import Counter
from typing import List, Optional

# Pure-Python Term-Frequency Cosine Similarity (100% Offline Fallback)
def get_lexical_similarity(text1: str, text2: str) -> float:
    words1 = re.findall(r'\w+', text1.lower())
    words2 = re.findall(r'\w+', text2.lower())
    
    if not words1 or not words2:
        return 0.0
        
    vec1 = Counter(words1)
    vec2 = Counter(words2)
    
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])
    
    sum1 = sum([vec1[x]**2 for x in vec1.keys()])
    sum2 = sum([vec2[x]**2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    
    if not denominator:
        return 0.0
    return float(numerator) / denominator

def get_vector_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    numerator = sum(a * b for a, b in zip(vec1, vec2))
    sum1 = sum(a**2 for a in vec1)
    sum2 = sum(b**2 for b in vec2)
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    if not denominator:
        return 0.0
    return float(numerator) / denominator

def get_embedding_vector(text: str, provider: str) -> Optional[List[float]]:
    """
    Fetches embedding vector from active API provider.
    Returns None if provider is unsupported or API request fails.
    """
    try:
        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return None
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
            payload = {
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": text}]}
            }
            r = requests.post(url, json=payload, timeout=5)
            if r.status_code == 200:
                return r.json().get("embedding", {}).get("values")
                
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            url = "https://api.openai.com/v1/embeddings"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "input": text,
                "model": "text-embedding-3-small"
            }
            r = requests.post(url, json=payload, headers=headers, timeout=5)
            if r.status_code == 200:
                return r.json().get("data", [{}])[0].get("embedding")
                
        elif provider == "ollama":
            model = os.getenv("OLLAMA_MODEL", "llama3")
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            url = f"{base_url.rstrip('/')}/api/embeddings"
            payload = {
                "model": model,
                "prompt": text
            }
            r = requests.post(url, json=payload, timeout=5)
            if r.status_code == 200:
                return r.json().get("embedding")
                
    except Exception as e:
        print(f"[Semantic Cache Warning] Embedding API fetch failed: {str(e)}")
        
    return None

def check_cache_hit(prompt: str, provider: str, model: str) -> Optional[str]:
    """
    Checks the local SQLite semantic_cache for similarities.
    Returns cached response if similarity >= 0.90, else None.
    """
    import database
    records = database.get_semantic_cache(provider, model)
    if not records:
        return None
        
    # Attempt to fetch embedding for new prompt
    new_vector = get_embedding_vector(prompt, provider)
    
    best_similarity = 0.0
    best_response = None
    is_best_vector = False
    
    for rec in records:
        rec_prompt = rec["prompt"]
        rec_vector_str = rec["embedding"]
        rec_response = rec["response"]
        
        # If we successfully retrieved an API vector, and the record has a vector, check vector similarity
        if new_vector and rec_vector_str:
            try:
                rec_vector = json.loads(rec_vector_str)
                if isinstance(rec_vector, list) and len(rec_vector) == len(new_vector):
                    sim = get_vector_similarity(new_vector, rec_vector)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_response = rec_response
                        is_best_vector = True
                    continue
            except Exception:
                pass
                
        # Lexical cosine fallback
        sim = get_lexical_similarity(prompt, rec_prompt)
        if sim > best_similarity:
            best_similarity = sim
            best_response = rec_response
            is_best_vector = False
            
    # Match threshold check: 0.90 for vectors, 0.70 for lexical backup
    threshold = 0.90 if is_best_vector else 0.70
    if best_similarity >= threshold:
        match_type = "vector" if is_best_vector else "lexical"
        print(f"\n[Semantic Cache Hit] Found {match_type} match with similarity {best_similarity:.2f}. Bypassing LLM call.")
        return best_response
        
    return None

def save_cache_entry(prompt: str, provider: str, model: str, response: str):
    """
    Saves a query prompt and response details into semantic_cache.
    """
    import database
    vector = get_embedding_vector(prompt, provider)
    vector_json = json.dumps(vector) if vector else None
    
    try:
        database.add_semantic_cache(provider, model, prompt, vector_json, response)
    except Exception as e:
        print(f"[Semantic Cache Warning] Failed to write cache entry: {str(e)}")
