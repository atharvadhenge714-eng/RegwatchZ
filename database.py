from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.id import ID
from dotenv import load_dotenv
import os

load_dotenv()

client = Client()
client.set_endpoint(os.getenv("APPWRITE_ENDPOINT", ""))
client.set_project(os.getenv("APPWRITE_PROJECT_ID", ""))
client.set_key(os.getenv("APPWRITE_API_KEY", ""))

databases = Databases(client)

def save_report(circular_name: str, parsed_result: str, action_plan: str) -> None:
    try:
        database_id = os.getenv("APPWRITE_DATABASE_ID", "")
        collection_id = os.getenv("APPWRITE_TABLE_ID", "")

        circular_str = str(circular_name)
        parsed_str = str(parsed_result)
        action_str = str(action_plan)

        databases.create_document(
            database_id=database_id,
            collection_id=collection_id,
            document_id=ID.unique(),
            data={
                "circular_name": circular_str,
                "parsed_result": parsed_str,
                "action_plan": action_str,
                "date_analyzed": "2025-03-06"
            }
        )
        print("✅ Saved to Appwrite!")
    except Exception as e:
        print(f"❌ Save failed: {e}")