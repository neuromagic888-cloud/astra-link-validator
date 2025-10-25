# SLO Monitoring — Astra Notion v1-lite

Table schema (Notion table columns)

- Date (date)
- Total Requests (number)
- Success % (number, percentage)
- Avg Duration (ms) (number)
- Top Error Codes (multi-select or text)
- Notes (text)

How to append daily "heartbeat" rows

- Manual: Open the SLO monitoring database in Notion and add a new row with the day's metrics.
- Automated (future): schedule a job that writes a new row via the Notion API once per day.

Basic SLO targets (examples)

- Success rate: >= 98%
- p95 latency: < 1500 ms

Weekly review ritual

- Each week, review the SLO table and:
  - Inspect top-5 error codes and their sources.
  - Flag any days below the success target for deeper investigation.
  - Summarize trends and post a short note in the team channel.
