import os
import re
import sys
import json
import itertools
from groq import Groq
from dotenv import load_dotenv

# Ensure safe UTF-8 output across all consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv()

# Collect all available API keys
RAW_KEYS = []
for k in ["GROQ_API_KEY", "GROQ_API_KEY_TERTIARY", "GROQ_API_KEY_SECONDARY"]:
    val = os.getenv(k)
    if val and val.strip() and val.strip() not in RAW_KEYS:
        RAW_KEYS.append(val.strip())

# Hardcode fallback keys (valid ones)
VALID_FALLBACK_KEYS = [
    "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",
    "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"
]

KEYS_POOL = list(dict.fromkeys(RAW_KEYS + VALID_FALLBACK_KEYS))
# Remove known invalid keys if present
KNOWN_BAD_KEYS = {"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"}
KEYS_POOL = [k for k in KEYS_POOL if k not in KNOWN_BAD_KEYS]

if not KEYS_POOL:
    KEYS_POOL = VALID_FALLBACK_KEYS.copy()

key_cycle = itertools.cycle(KEYS_POOL)

def get_next_client():
    """Retrieve the next Groq client in round-robin order."""
    api_key = next(key_cycle)
    return Groq(api_key=api_key), api_key

def clean_json_response(text: str) -> str:
    """Extract clean JSON string from LLM response, stripping thinking blocks and markdown notation."""
    if not text:
        return "{}"
    # Strip <think>...</think> reasoning tags
    text_clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
    # Strip markdown code blocks
    if "```json" in text_clean:
        text_clean = text_clean.split("```json")[1].split("```")[0].strip()
    elif "```" in text_clean:
        text_clean = text_clean.split("```")[1].split("```")[0].strip()
        
    return text_clean

def parse_json_safely(text: str, default_val: dict) -> dict:
    """Parse JSON string cleanly, with robust fallback to default value."""
    if not text:
        return default_val
    try:
        cleaned = clean_json_response(text)
        val = json.loads(cleaned)
        if isinstance(val, dict):
            if "error" in val and "Rate limit" in str(val.get("error")):
                return default_val
            return val
        elif isinstance(val, list) and isinstance(default_val, dict):
            return default_val
        return default_val
    except Exception:
        # Try extracting outermost JSON object with regex
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                val = json.loads(match.group(0))
                if isinstance(val, dict):
                    return val
        except Exception:
            pass
    return default_val

# Active verified Groq models for compliance workflows
VERIFIED_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound-mini",
    "qwen/qwen3.6-27b",
    "allam-2-7b",
    "groq/compound",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]

def run_llm_completion(prompt: str, system_prompt: str = "You are an expert regulatory compliance analyst.", temperature: float = 0.2, response_format_json: bool = False) -> str:
    """Run an LLM completion load balanced across the API key pool.
    
    Automatically handles rate limits, 404/401 errors, and rotates models/keys.
    """
    last_exception = None
    
    for model in VERIFIED_MODELS:
        for attempt in range(max(len(KEYS_POOL), 1)):
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
                content = response.choices[0].message.content
                if content:
                    return content.strip()
                
            except Exception as e:
                err_msg = str(e)
                # If key is invalid (401), remove from pool if possible
                if "401" in err_msg or "invalid_api_key" in err_msg:
                    if key_used in KEYS_POOL and len(KEYS_POOL) > 1:
                        KEYS_POOL.remove(key_used)
                last_exception = e
                continue
                
    # If all keys and models failed, return an emergency graceful fallback string
    print(f"[AI] Model completion fallback invoked. Last exception: {last_exception}")
    return json.dumps({
        "error": "Rate limit or connection issue on AI provider.",
        "change_severity": "MEDIUM",
        "why_this_matters": "Fallback data generated.",
        "company_impact_summary": "System generated fallback due to network timeout.",
        "added_sections": [],
        "removed_sections": [],
        "modified_requirements": [],
        "affected_entities": [],
        "recommended_actions": []
    })

