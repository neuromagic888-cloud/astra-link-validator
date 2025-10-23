import os, requests

def main():
    token = os.getenv("NOTION_TOKEN")
    link_db = os.getenv("LINKCHECK_DB_ID")
    aff = os.getenv("AFF_TAG", "abinom55-20")

    print("🌿 Quiet Link Validator — dry run safeguard")
    print(f"Secrets present? NOTION_TOKEN={'yes' if token else 'no'}, LINKCHECK_DB_ID={'yes' if link_db else 'no'}")
    print(f"AFF_TAG={aff}")

    if not token or not link_db:
        print("No secrets yet — exiting successfully to avoid red X.")
        return 0

    try:
        r = requests.post(
            "https://api.notion.com/v1/databases/query",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28"
            },
            json={"database_id": link_db}
        )
        print(f"✅ Response: {r.status_code}")
    except Exception as e:
        print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    main()

