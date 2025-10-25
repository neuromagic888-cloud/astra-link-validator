# Runbook — Degradation (Astra Notion v1-lite)

Symptoms

- Automation runs failing to create or update Notion pages
- Frequent 403/404 responses when hitting parent page or database
- Sudden spike in 429 rate-limit responses

Quick checks

- Confirm NOTION_TOKEN is set and valid.
- Check whether the parent page ID responds (403/404 indicates permission issues).
- Check integration is invited/shared to the parent page.

Retry policy

- Respect Retry-After header when present.
- Exponential backoff schedule (seconds): 1, 2, 4, 8, 10
- Max attempts: 6

Escalation

- If retries fail, convert the issue into a discussion and tag the owner or on-call.
- Provide the logs (non-sensitive) and approximate timestamps for troubleshooting.
