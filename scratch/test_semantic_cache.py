import os
import sys

# Append parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
import semantic_cache_engine

def run_test():
    print("Initializing Database...")
    database.init_db()
    
    print("Clearing Semantic Cache...")
    database.clear_semantic_cache()
    
    provider = "gemini"
    model = "gemini-2.5-flash"
    
    # 1. First prompt (cache miss)
    prompt1 = "Create a login form in HTML with validation"
    response1 = "<html><body><form>Login Form Content</form></body></html>"
    
    print(f"Checking cache for: '{prompt1}'")
    hit1 = semantic_cache_engine.check_cache_hit(prompt1, provider, model)
    assert hit1 is None, "Cache should have missed!"
    print("Cache Miss confirmed.")
    
    print(f"Saving response to cache...")
    semantic_cache_engine.save_cache_entry(prompt1, provider, model, response1)
    
    # 2. Conceptually identical prompt (cache hit)
    prompt2 = "Create an HTML sign-in form with validation"
    print(f"Checking cache for conceptually similar: '{prompt2}'")
    hit2 = semantic_cache_engine.check_cache_hit(prompt2, provider, model)
    
    assert hit2 is not None, "Cache should have HIT!"
    assert hit2 == response1, "Response content does not match cached response!"
    print("Cache HIT confirmed!")
    print(f"Returned Response: {hit2[:50]}...")
    
    # 3. Different prompt (cache miss)
    prompt3 = "Write a python script to calculate fibonacci numbers"
    print(f"Checking cache for different topic: '{prompt3}'")
    hit3 = semantic_cache_engine.check_cache_hit(prompt3, provider, model)
    assert hit3 is None, "Cache should have missed for different topic!"
    print("Cache Miss for different topic confirmed.")
    
    print("\nAll Semantic Cache engine tests passed successfully!")

if __name__ == "__main__":
    run_test()
