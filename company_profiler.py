import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import json
from services.ai_service import run_llm_completion, parse_json_safely
from services.search_service import web_search

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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

def search_company(company_name, country="India"):
    """Search for a company and find its website URL."""
    print(f"[PROFILER] Searching for '{company_name}' in {country}...")

    # For known companies, return direct URLs
    known_companies = {
        "paytm": "https://paytm.com",
        "phonepe": "https://www.phonepe.com",
        "razorpay": "https://razorpay.com",
        "cred": "https://cred.club",
        "groww": "https://groww.in",
        "zerodha": "https://zerodha.com",
        "bajaj finserv": "https://www.bajajfinserv.in",
        "hdfc bank": "https://www.hdfcbank.com",
        "icici bank": "https://www.icicibank.com",
        "sbi": "https://www.sbi.co.in",
        "axis bank": "https://www.axisbank.com",
        "kotak mahindra": "https://www.kotak.com",
        "muthoot finance": "https://www.muthootfinance.com",
        "bajaj finance": "https://www.bajajfinserv.in",
        "mobikwik": "https://www.mobikwik.com",
        "slice": "https://www.sliceit.com",
        "jupiter": "https://jupiter.money",
        "fi money": "https://fi.money",
        "niyo": "https://www.goniyo.com",
        "lendingkart": "https://www.lendingkart.com",
        "zestmoney": "https://www.zestmoney.in",
        "rupeek": "https://www.rupeek.com",
        "navi": "https://navi.com",
        "policybazaar": "https://www.policybazaar.com",
    }

    name_lower = company_name.lower().strip()
    for key, url in known_companies.items():
        if key in name_lower or name_lower in key:
            print(f"[PROFILER] Found: {url}")
            return url

    # Try live web search
    try:
        results = web_search(f"{company_name} official website home page", max_results=1)
        if results and results[0].get("url"):
            print(f"[PROFILER] Discovered URL via search: {results[0]['url']}")
            return results[0]['url']
    except Exception as e:
        print(f"[PROFILER] Search notice: {e}")

    # Try constructing URL from company name
    clean_name = company_name.lower().replace(" ", "").replace(".", "")
    guessed_url = f"https://www.{clean_name}.com"
    print(f"[PROFILER] Trying: {guessed_url}")
    return guessed_url


def scrape_company_website(url):
    """Scrape company website to extract text content."""
    if not url or url.startswith("Uploaded"):
        return "No website content."
        
    print(f"[PROFILER] Scraping {url}...")
    all_text = ""

    # Pages to scrape
    pages = [
        url,
        url.rstrip("/") + "/about",
        url.rstrip("/") + "/about-us",
        url.rstrip("/") + "/products",
        url.rstrip("/") + "/services",
    ]

    for page_url in pages:
        try:
            response = requests.get(page_url, headers=HEADERS, timeout=8, allow_redirects=True)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # Remove scripts, styles, nav, footer
                for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript"]):
                    tag.decompose()

                text = soup.get_text(separator=" ", strip=True)

                # Clean up
                lines = [line.strip() for line in text.split("\n") if line.strip() and len(line.strip()) > 10]
                page_text = " ".join(lines)

                if page_text:
                    all_text += f"\n[PAGE: {page_url}]\n{page_text[:1500]}\n"
                    print(f"  [OK] Scraped: {page_url} ({len(page_text)} chars)")
        except Exception as e:
            print(f"  [SKIP] {page_url} ({e})")
            continue

    if not all_text:
        print("[PROFILER] Could not scrape website, will use company name for AI analysis")
        all_text = f"Company: {url}"

    return all_text[:6000]


def build_compliance_profile(company_name, website_text, primary_country="India"):
    """Use AI to build a structured compliance profile from website content."""
    print("[PROFILER] Building compliance profile with AI...")

    prompt = f"""You are a corporate risk and compliance analyst. Analyze this company's website content and build a compliance profile.

Company Name: {company_name}
Primary Country: {primary_country}
Website Content:
{website_text[:4000]}

Return ONLY a valid JSON object (no extra text, no markdown block notation) with this exact structure:
{{
    "company_name": "{company_name}",
    "company_type": "one of: Bank / NBFC / Fintech / Payment Aggregator / Microfinance / Broker / Insurance / Tech Provider",
    "industry": "e.g. Payments, Digital Lending, WealthTech, InsurTech, NeoBanking",
    "rbi_registration": "type of license likely held (e.g. NBFC, PA License, Banking License, PPI License, or 'None/Not regulated')",
    "services": ["list of specific customer services offered"],
    "regulatory_domains": ["list of compliance areas, e.g. Data Protection, Cybersecurity, Financial Rules, Reporting, Third-Party Risk"],
    "applicable_rbi_guidelines": ["list of regulations or guidelines likely applicable"],
    "risk_areas": ["list of key risk areas"],
    "data_handling": "description of customer data handled",
    "compliance_summary": "2-3 sentence summary of compliance requirements"
}}

Return ONLY the JSON."""

    response_text = run_llm_completion(prompt, system_prompt="You are a precise corporate analyst outputting strict JSON.", temperature=0.2)
    
    default_profile = {
        "company_name": company_name,
        "company_type": "Fintech",
        "industry": "Payments",
        "rbi_registration": "Unknown",
        "services": ["Digital payments", "Financial services"],
        "regulatory_domains": ["Data Protection", "Cybersecurity", "Financial Rules", "Reporting", "Third-Party Risk"],
        "applicable_rbi_guidelines": ["General Payment Guidelines"],
        "risk_areas": ["KYC compliance", "Data privacy"],
        "data_handling": "Customer transaction details and KYC data",
        "compliance_summary": "Standard fintech company operating in payments."
    }

    return parse_json_safely(response_text, default_profile)


def profile_company(company_name, country="India"):
    """Full pipeline: search → scrape → build profile."""
    print(f"\n[PROFILER] Building Compliance Profile: {company_name} ({country})")

    # Step 1: Find website
    url = search_company(company_name, country)

    # Step 2: Scrape website
    website_text = scrape_company_website(url)

    # Step 3: Build profile with AI
    profile = build_compliance_profile(company_name, website_text, country)
    profile["website_url"] = url
    profile["primary_country"] = country
    profile["operating_countries"] = [country]

    return profile
