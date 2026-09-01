import pypdf
from services.ai_service import run_llm_completion, parse_json_safely

def parse_rbi_circular(pdf_path):
    print("[PARSER] Reading PDF...")
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    except Exception as e:
        print(f"[PARSER] PDF reading error: {e}")
        return "{}"

    print("[PARSER] Sending to LLM for analysis...")

    prompt = f"""You are an RBI regulatory compliance expert.

Analyze this RBI circular and return ONLY a valid JSON object (no markdown code blocks, no extra text):
{{
    "title": "title of the circular",
    "main_change": "what regulation changed in simple words",
    "deadline": "compliance deadline or Not specified",
    "affected_domains": ["Data Protection", "Cybersecurity", "Financial Rules", "Reporting", "Third-Party Risk"],
    "severity": "High or Medium or Low",
    "action_required": "one sentence on what companies must do"
}}

Circular text:
{text[:4000]}"""

    response = run_llm_completion(prompt, system_prompt="You are an RBI compliance parser.", temperature=0.1)
    return response