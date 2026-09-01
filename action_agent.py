from services.ai_service import run_llm_completion, parse_json_safely
from typing import Any
import json

def generate_action_plan(parsed_circular: str, affected_policies: list[Any]) -> str:
    """Generate a comprehensive, structured compliance action plan."""
    print("[ACTION] Generating compliance action plan...")

    # Format affected policies for the AI
    if isinstance(affected_policies, list) and affected_policies:
        if isinstance(affected_policies[0], dict):
            policies_text = "\n".join(
                f"  {i+1}. [{p['policy_name']}] (Dept: {p['department']}) — Regulatory Ref: {p['regulatory_reference']}\n"
                f"     Current Version: v{p['version']} | Last Updated: {p['last_updated']}\n"
                f"     Content: {p['matched_content'][:200]}"
                for i, p in enumerate(affected_policies)
            )
        else:
            policies_text = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(affected_policies))
    else:
        policies_text = str(affected_policies)

    prompt = f"""You are the Chief Compliance Officer at an Indian fintech/NBFC company. A new RBI regulation has been issued and you must create an ACTIONABLE compliance response.

## New RBI Regulation:
{parsed_circular}

## Company Policies Affected:
{policies_text}

Generate a COMPREHENSIVE compliance action plan in the following exact format. Be specific, reference actual policy names, and provide realistic deadlines.

---

## 📊 COMPLIANCE GAP ANALYSIS

For each affected policy, identify:
- **Current State**: What the existing policy says
- **Required State**: What the new regulation demands
- **Gap**: Specific differences that need to be addressed
- **Risk Level**: 🔴 High / 🟡 Medium / 🟢 Low

---

## ⚡ IMMEDIATE ACTIONS (Within 7 Days)

| # | Action Item | Owner | Deadline | Priority |
|---|------------|-------|----------|----------|
| 1 | [specific task] | [Engineering/Legal/Compliance/Product/Operations] | [date] | 🔴/🟡/🟢 |

List 4-5 specific, actionable tasks.

---

## 📝 POLICY AMENDMENTS REQUIRED

For each affected policy, draft the specific amendments:
- **Policy Name**: [name]
- **Section to Amend**: [specific section]
- **Current Wording**: [what it says now]
- **Proposed Wording**: [what it should say]

---

## 🎫 AUTO-GENERATED COMPLIANCE TASKS

Create JIRA-style tickets:

**Ticket 1**: [POLICY-ID] — [Task Title]
- **Assignee**: [Team]
- **Sprint**: Current / Next
- **Story Points**: [1-8]
- **Acceptance Criteria**: [specific criteria]

Create 4-5 tickets.

---

## 📧 STAKEHOLDER NOTIFICATIONS

Draft notification emails for affected teams:
- **To**: [Team/Department]
- **Subject**: [Compliance Alert subject line]
- **Key Message**: [2-3 sentence summary of what they need to do]

---

## ⏰ COMPLIANCE TIMELINE

| Phase | Action | Deadline | Status |
|-------|--------|----------|--------|
| Phase 1 | [Immediate Assessment] | [Week 1] | 🔲 Pending |
| Phase 2 | [Policy Drafting] | [Week 2-3] | 🔲 Pending |
| Phase 3 | [Implementation] | [Week 4-8] | 🔲 Pending |
| Phase 4 | [Testing & Audit] | [Week 8-10] | 🔲 Pending |
| Phase 5 | [Go-Live & Reporting] | [by deadline] | 🔲 Pending |

---

## ⚠️ RISK ASSESSMENT

- **Penalty if non-compliant**: [specific RBI penalty]
- **Reputational risk**: [impact assessment]
- **Operational risk**: [business continuity impact]
- **Recommended board escalation**: Yes/No with justification

Be practical, specific to Indian fintech/NBFC operations, and reference real RBI guidelines.
Use markdown formatting throughout."""

    return run_llm_completion(prompt, system_prompt="You are a Chief Compliance Officer preparing board plans.", temperature=0.2)


def generate_gap_analysis(regulation_text: str, policy_text: str) -> str:
    """Generate a focused gap analysis between a regulation and a specific policy."""
    print("[ACTION] Generating gap analysis...")

    reg_snippet = regulation_text[:2000]
    pol_snippet = policy_text[:2000]

    prompt = f"""Compare this new RBI regulation with the existing company policy and identify compliance gaps.

New Regulation: {reg_snippet}

Existing Policy: {pol_snippet}

List each gap as:
1. **Gap**: [description]
   - **Current**: [what policy says]
   - **Required**: [what regulation requires]
   - **Action**: [what to do]
   - **Risk**: 🔴 High / 🟡 Medium / 🟢 Low

Be specific and practical."""

    return run_llm_completion(prompt, system_prompt="You are a Gap Analyst.", temperature=0.1)


def generate_compliance_alert(circular_info: dict[str, Any], comparison: dict[str, Any], company_profile: dict[str, Any]) -> str:
    """Generate a full compliance alert combining circular info, comparison results, and company profile."""
    print("[ACTION] Generating compliance alert...")

    prompt = f"""You are the Chief Compliance Officer at an Indian fintech/NBFC company. Generate a COMPREHENSIVE compliance alert based on the following analysis.

## Company: {company_profile.get('company_name', 'Unknown')}
- Type: {company_profile.get('company_type', 'Fintech')}
- Services: {', '.join(company_profile.get('services', []))}

## Circular: {circular_info.get('title', 'Unknown')}
Date: {circular_info.get('date', 'N/A')}
Content: {circular_info.get('content', '')[:3000]}

## Impact Analysis:
- Impact Level: {comparison.get('impact_level', 'Unknown')}
- Applicable: {comparison.get('is_applicable', False)}
- Reason: {comparison.get('applicability_reason', '')}
- Affected Services: {', '.join(comparison.get('affected_services', []))}
- Compliance Gaps: {json.dumps(comparison.get('compliance_gaps', []), indent=2)[:1500]}

Generate a detailed compliance alert in markdown with:
1. **Executive Summary** — 2-3 sentence overview
2. **Impact Assessment** — What this means for the company
3. **Compliance Gaps** — Specific gaps identified with risk levels
4. **Immediate Actions Required** — Numbered action items with owners and deadlines
5. **Policy Amendments Needed** — Which internal policies must be updated
6. **Compliance Timeline** — Phase-wise implementation plan
7. **Risk Assessment** — Penalties, reputational risk, operational risk

Be specific, practical, and reference actual company services and policies.
Use markdown formatting throughout with appropriate emojis."""

    return run_llm_completion(prompt, system_prompt="You are a Chief Compliance Officer writing high-urgency memos.", temperature=0.2)


def generate_quick_scan(circulars: list[dict[str, Any]], company_profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Quick scan all circulars for relevance to the company profile."""
    print(f"[ACTION] Quick scanning {len(circulars)} circulars...")

    circulars_text = "\n".join(
        f"{i+1}. [{c.get('category', 'RBI')}] {c['title']} — {c.get('summary', '')[:150]}"
        for i, c in enumerate(circulars)
    )

    prompt = f"""You are an RBI compliance expert. Quickly assess the relevance of each circular to this company.

## Company Profile:
- Name: {company_profile.get('company_name', 'Unknown')}
- Type: {company_profile.get('company_type', 'Fintech')}
- Services: {', '.join(company_profile.get('services', []))}
- Regulatory Domains: {', '.join(company_profile.get('regulatory_domains', []))}
- Risk Areas: {', '.join(company_profile.get('risk_areas', []))}

## Circulars to Scan:
{circulars_text}

Return ONLY a valid JSON array (no markdown, no extra text). For each circular (in order), return:
[
    {{
        "is_relevant": true or false,
        "impact_level": "High" or "Medium" or "Low" or "Not Applicable",
        "relevance_reason": "one sentence explaining why it is or isn't relevant",
        "urgency": "Immediate" or "This Quarter" or "Informational"
    }},
    ...
]

Return exactly {len(circulars)} objects in the array, one per circular, in the same order."""

    response_text = run_llm_completion(prompt, system_prompt="You are a scanning auditor returning strict JSON arrays.", temperature=0.2)
    
    default_fallback = [
        {
            "is_relevant": True,
            "impact_level": "Medium",
            "relevance_reason": "Could not auto-assess — manual review needed",
            "urgency": "This Quarter"
        }
        for _ in circulars
    ]
    
    return parse_json_safely(response_text, default_fallback)