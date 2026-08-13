import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

LOCAL_DB_FILE = "local_db.json"

# Try setting up Appwrite if environment variables are set
APPWRITE_SUPPORTED = False
try:
    from appwrite.client import Client
    from appwrite.services.databases import Databases
    from appwrite.id import ID
    
    endpoint = os.getenv("APPWRITE_ENDPOINT", "")
    project_id = os.getenv("APPWRITE_PROJECT_ID", "")
    api_key = os.getenv("APPWRITE_API_KEY", "")
    
    if endpoint and project_id and api_key:
        client = Client()
        client.set_endpoint(endpoint)
        client.set_project(project_id)
        client.set_key(api_key)
        databases_client = Databases(client)
        APPWRITE_SUPPORTED = True
        print("[DB] Appwrite database initialized successfully.")
except Exception as e:
    print(f"[DB] Appwrite initialization skipped or failed: {e}. Falling back to local JSON database.")

def init_local_db():
    """Ensure the local database file exists and is populated."""
    if not os.path.exists(LOCAL_DB_FILE):
        with open(LOCAL_DB_FILE, "w") as f:
            json.dump({
                "companies": {},
                "reports": [],
                "diff_history": [],
                "global_matrices": {},
                "agent_runs": [],
                "saved_profiles": []
            }, f, indent=4)

# Initialize on import
init_local_db()

def get_local_data() -> dict:
    init_local_db()
    try:
        with open(LOCAL_DB_FILE, "r") as f:
            data = json.load(f)
            if "saved_profiles" not in data:
                data["saved_profiles"] = []
            return data
    except Exception as e:
        print(f"[DB] Error reading local db: {e}")
        return {"companies": {}, "reports": [], "diff_history": [], "global_matrices": {}, "agent_runs": [], "saved_profiles": []}

def save_local_data(data: dict):
    try:
        with open(LOCAL_DB_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[DB] Error writing local db: {e}")

# ================= PERSISTENT SAVED PROFILES & SCAN HISTORY =================

def generate_next_profile_id() -> str:
    """Generate a unique scan/profile ID such as RW-2026-0001."""
    data = get_local_data()
    saved = data.get("saved_profiles", [])
    current_year = datetime.datetime.now().year
    
    max_seq = 0
    for s in saved:
        pid = s.get("profile_id", "")
        if pid.startswith(f"RW-{current_year}-"):
            try:
                seq = int(pid.split("-")[-1])
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                pass
                
    new_seq = max_seq + 1
    return f"RW-{current_year}-{new_seq:04d}"


def save_full_compliance_profile(company_profile: dict, discovery_results: dict, applicability_results: dict, compliance_results: dict, risk_results: dict, action_results: dict, report_results: dict = None) -> str:
    """Save complete current compliance analysis as a persistent record with versioning."""
    data = get_local_data()
    profile_id = generate_next_profile_id()
    
    now = datetime.datetime.now()
    # Format e.g.: 13 Aug 2026, 10:05 PM
    created_at_str = now.strftime("%d %b %Y, %I:%M %p")
    
    # Calculate counts & score
    company_name = company_profile.get("company_name", "Unknown")
    primary_country = company_profile.get("primary_country", "India")
    operating_countries = company_profile.get("operating_countries", [primary_country])
    company_type = company_profile.get("company_type", "Fintech")
    industry = company_profile.get("industry", "Payments")
    
    compliance_score = risk_results.get("exposure", {}).get("risk_score", 90) if risk_results else 90
    gaps = compliance_results.get("gaps", []) if compliance_results else []
    alerts_count = len(gaps)
    
    # Calculate regulations count across ecosystems
    regulations_count = 0
    if discovery_results and "ecosystem" in discovery_results:
        for eco in discovery_results["ecosystem"].values():
            regulations_count += len(eco.get("regulations", []))
            
    saved_record = {
        "profile_id": profile_id,
        "company_name": company_name,
        "primary_country": primary_country,
        "operating_countries": operating_countries,
        "company_type": company_type,
        "industry": industry,
        "compliance_score": compliance_score,
        "alerts_count": alerts_count,
        "regulations_count": max(regulations_count, len(applicability_results.get("applicable", [])) if applicability_results else 12),
        "created_at": created_at_str,
        "timestamp_iso": now.isoformat(),
        
        # Structured Payload
        "company_profile": company_profile,
        "discovery_results": discovery_results,
        "applicability_results": applicability_results,
        "compliance_results": compliance_results,
        "risk_results": risk_results,
        "action_results": action_results,
        "report_results": report_results or {}
    }
    
    # Append new scan version (historical analyses preserved)
    data["saved_profiles"].append(saved_record)
    save_local_data(data)
    print(f"[DB] Saved persistent compliance profile {profile_id} for {company_name}.")
    
    # Optional push to Appwrite
    if APPWRITE_SUPPORTED:
        try:
            db_id = os.getenv("APPWRITE_DATABASE_ID", "")
            collection_id = os.getenv("APPWRITE_TABLE_ID", "")
            if db_id and collection_id:
                databases_client.create_document(
                    database_id=db_id,
                    collection_id=collection_id,
                    document_id=ID.unique(),
                    data={
                        "circular_name": f"{profile_id} - {company_name}"[:255],
                        "parsed_result": json.dumps(compliance_results)[:2000] if compliance_results else "{}",
                        "action_plan": json.dumps(action_results)[:2000] if action_results else "{}",
                        "date_analyzed": now.strftime("%Y-%m-%d")
                    }
                )
                print(f"[DB] Saved profile {profile_id} pushed to Appwrite.")
        except Exception as e:
            print(f"[DB] Appwrite push error: {e}")
            
    return profile_id


def get_saved_profiles() -> list:
    """Retrieve all saved profiles sorted by creation date descending."""
    data = get_local_data()
    profiles = data.get("saved_profiles", [])
    profiles.sort(key=lambda x: x.get("timestamp_iso", ""), reverse=True)
    return profiles


def get_saved_profile_by_id(profile_id: str) -> dict:
    """Retrieve a specific saved profile by profile_id."""
    data = get_local_data()
    for p in data.get("saved_profiles", []):
        if p.get("profile_id") == profile_id:
            return p
    return {}


def get_company_scan_history(company_name: str) -> list:
    """Get all historical scans for a company sorted by timestamp descending."""
    data = get_local_data()
    c_name_lower = company_name.lower().strip()
    history = [
        p for p in data.get("saved_profiles", [])
        if p.get("company_name", "").lower().strip() == c_name_lower
    ]
    history.sort(key=lambda x: x.get("timestamp_iso", ""), reverse=True)
    return history


def delete_saved_profile(profile_id: str) -> bool:
    """Permanently remove a saved profile by profile_id."""
    data = get_local_data()
    initial_count = len(data.get("saved_profiles", []))
    data["saved_profiles"] = [
        p for p in data.get("saved_profiles", [])
        if p.get("profile_id") != profile_id
    ]
    if len(data["saved_profiles"]) < initial_count:
        save_local_data(data)
        print(f"[DB] Deleted profile {profile_id} from database.")
        return True
    return False

# ================= LEGACY / AUXILIARY FUNCTIONS =================

def save_company_profile(company_name: str, country: str, profile: dict):
    data = get_local_data()
    data["companies"][company_name.lower().strip()] = {
        "profile": profile,
        "country": country,
        "updated_at": datetime.datetime.now().isoformat()
    }
    save_local_data(data)

def get_company_profile(company_name: str) -> dict:
    data = get_local_data()
    entry = data["companies"].get(company_name.lower().strip())
    if entry:
        return entry["profile"]
    return {}

def save_compliance_report(company_name: str, report_title: str, comparison_result: dict, alert_content: str):
    data = get_local_data()
    data["reports"].append({
        "company_name": company_name,
        "title": report_title,
        "comparison_result": comparison_result,
        "alert_content": alert_content,
        "timestamp": datetime.datetime.now().isoformat()
    })
    save_local_data(data)

def save_global_matrix(company_name: str, matrix_data: dict):
    data = get_local_data()
    data["global_matrices"][company_name.lower().strip()] = {
        "matrix": matrix_data,
        "timestamp": datetime.datetime.now().isoformat()
    }
    save_local_data(data)

def get_global_matrix(company_name: str) -> dict:
    data = get_local_data()
    entry = data["global_matrices"].get(company_name.lower().strip())
    if entry:
        return entry["matrix"]
    return {}

def save_diff_result(doc1_title: str, doc2_title: str, diff_results: dict):
    data = get_local_data()
    data["diff_history"].append({
        "doc1_title": doc1_title,
        "doc2_title": doc2_title,
        "diff": diff_results,
        "timestamp": datetime.datetime.now().isoformat()
    })
    save_local_data(data)

def get_diff_history() -> list:
    data = get_local_data()
    return data.get("diff_history", [])

def save_agent_run(company_name: str, pipeline_results: dict):
    data = get_local_data()
    data["agent_runs"].append({
        "company_name": company_name,
        "pipeline": pipeline_results,
        "timestamp": datetime.datetime.now().isoformat()
    })
    save_local_data(data)
