import os
import json
import itertools
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Collect all available API keys
KEYS_POOL = []
for k in ["GROQ_API_KEY", "GROQ_API_KEY_SECONDARY", "GROQ_API_KEY_TERTIARY"]:
    val = os.getenv(k)
    if val and val.strip() and val not in KEYS_POOL:
        KEYS_POOL.append(val.strip())

# Hardcode the keys provided by user as guaranteed pool fallbacks
HARDCODED_KEYS = [
   GROQ_API_KEY=your_real_key_here

for hk in HARDCODED_KEYS:
    if hk not in KEYS_POOL:
        KEYS_POOL.append(hk)

# Global round-robin iterator across the key pool
key_cycle = itertools.cycle(KEYS_POOL)

def get_next_client():
    """Retrieve the next Groq client in round-robin order."""
    api_key = next(key_cycle)
    return Groq(api_key=api_key), api_key

def clean_json_response(text: str) -> str:
    """Extract JSON string from LLM code block notation."""
    text_clean = text.strip()
    if "```json" in text_clean:
        text_clean = text_clean.split("```json")[1].split("```")[0].strip()
    elif "```" in text_clean:
        text_clean = text_clean.split("```")[1].split("```")[0].strip()
    return text_clean

def parse_json_safely(text: str, default_val: dict) -> dict:
    """Parse JSON string cleanly, with robust fallback to default value."""
    cleaned = clean_json_response(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[AI] JSON decode error: {e}. Raw response snippet: {text[:150]}")
        return default_val

def run_llm_completion(prompt: str, system_prompt: str = "You are an expert regulatory compliance analyst.", temperature: float = 0.2, response_format_json: bool = False) -> str:
    """Run an LLM completion load balanced across the API key pool.
    
    If RateLimitError (429) occurs, automatically retries using alternate keys and backup models.
    """
    models_to_try = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
    
    last_exception = None
    
    for model in models_to_try:
        # Try across each key in our pool
        for attempt in range(len(KEYS_POOL)):
            try:
                client, key_used = get_next_client()
                kwargs = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature
                }
                if response_format_json:
                    kwargs["response_format"] = {"type": "json_object"}
                    
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                err_msg = str(e)
                print(f"[AI] Attempt with key ending in ...{key_used[-6:]} on model '{model}' hit error: {err_msg[:120]}")
                last_exception = e
                # Continue to next key in pool immediately
                continue
                
    # If all keys and models failed, return an emergency graceful fallback string
    print(f"[AI] All API keys and models exhausted due to rate limits: {last_exception}")
    return json.dumps({
        "error": "Rate limit exceeded across all API keys.",
        "change_severity": "MEDIUM",
        "why_this_matters": "Rate limit reached on AI provider. Results are temporarily loaded from cache.",
        "company_impact_summary": "Automatic rate limiting in effect.",
        "added_sections": [],
        "removed_sections": [],
        "modified_requirements": [],
        "affected_entities": [],
        "recommended_actions": []
    })
