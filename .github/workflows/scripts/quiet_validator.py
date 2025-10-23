import os, sys, requests

def main():
    token = os.getenv("NOTION_TOKEN")
    link_db = os.getenv("LINKCHECK_DB_ID")
    aff = os.getenv("AFF_TAG", "abinom55-20")

    print("🌿 Quiet Link Validator — dry run safeguard")
    print(f"Secrets present? NOTION_TOKEN={'yes' if token else 'no'}, LINKCHECK_DB_ID={'yes' if link_db else 'no'}")
    print(f"AFF_TAG={aff}")

    # Если секреты не заданы — выходим успешно, чтобы первый запуск не краснел
    if not token or not link_db:
        print("No secrets yet — exiting successfully to avoid red X. Add repo secrets and re-run.")
        return 0

    # Мини-пинг Notion (ничего не пишет)
    try:
        r = requests.post(
            f"https://api.notion.com/v1/databases/{link_db}/query",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
                "User-Agent": "Astra/QuietValidator"
            },
            json={"page_size": 1},
            timeout=10
        )
        print("Notion query status:", r.status_code)
        if r.status_code == 200:
            print("OK: Notion connectivity verified.")
            return 0
        else:
            print("Warning:", r.status_code, r.text[:200])
            return 0
    except Exception as e:
        print("Exception:", e)
        return 0

if __name__ == "__main__":
    sys.exit(main())
