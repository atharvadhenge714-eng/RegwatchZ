import json
from services.ai_service import run_llm_completion, parse_json_safely

def compare_regulatory_documents(old_text: str, new_text: str, company_profile: dict = None) -> dict:
    """Compare two versions of a regulatory document using Groq and extract differences."""
    company_name = company_profile.get("company_name", "the company") if company_profile else "a typical fintech/NBFC"
    
    prompt = f"""You are a regulatory compliance engineer and diff analyst. Compare the following two versions of a regulatory circular, guideline, or policy.
    
    OLD VERSION:
    {old_text[:3000]}
    
    NEW VERSION:
    {new_text[:3000]}
    
    Target Company Profile: {json.dumps(company_profile or {{}})}
    
    Identify all changes. Do not invent differences. Every detected change must be based on actual document contents.
    
    Return ONLY a valid JSON object (no markdown blocks, no extra characters) with this exact structure:
    {{
        "change_severity": "LOW / MEDIUM / HIGH / CRITICAL",
        "effective_date": "effective date mentioned, or 'Immediate' or 'Not specified'",
        "why_this_matters": "A concise, grounded explanation of what this update represents and why it is important.",
        "company_impact_summary": "Explanation of how this change specifically impacts {company_name}.",
        "added_sections": [
            {{
                "title": "Topic or Section Title",
                "text": "Exact text or brief summary of the added section",
                "obligations": "What new obligation this introduces"
            }}
        ],
        "removed_sections": [
            {{
                "title": "Topic or Section Title",
                "text": "Exact text or brief summary of what was removed"
            }}
        ],
        "modified_requirements": [
            {{
                "item": "Requirement name (e.g. Reporting Deadline, Penalty, Minimum Capital)",
                "old_val": "Original threshold/value/obligation (e.g. 30 days)",
                "new_val": "New threshold/value/obligation (e.g. 7 days)",
                "change_type": "Wording / Deadline / Penalty / Obligation / Threshold",
                "impact_level": "LOW / MEDIUM / HIGH / CRITICAL"
            }}
        ],
        "affected_entities": ["list of entities affected (e.g. Banks, NBFCs, Payment Gateways)"],
        "recommended_actions": [
            {{
                "action": "Description of recommended action",
                "priority": "HIGH / MEDIUM / LOW",
                "team": "Engineering / Compliance / Product / Legal"
            }}
        ]
    }}
    
    Return ONLY the raw JSON object."""

    system_prompt = "You are a precise, logical regulatory auditor that performs document diff comparisons without hallucinating."
    
    response_text = run_llm_completion(prompt, system_prompt=system_prompt, temperature=0.1)
    
    default_fallback = {
        "change_severity": "MEDIUM",
        "effective_date": "Not specified",
        "why_this_matters": "A comparative analysis could not be parsed correctly.",
        "company_impact_summary": "Manual review of the differences is recommended.",
        "added_sections": [],
        "removed_sections": [],
        "modified_requirements": [],
        "affected_entities": [],
        "recommended_actions": []
    }
    
    return parse_json_safely(response_text, default_fallback)
