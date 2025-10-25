# Astra — Notion v1-lite

Purpose

This document describes the v1-lite Notion integration for Astra. The v1-lite setup uses three Notion databases with a small relation model and is designed to be idempotent: repeated runs of the init script should not create duplicate databases or relations.

High-level design (v1-lite)

- Three Notion databases:
  1. Chronicle (primary records)
  2. LinkChecks (link validation results)
  3. RunLog (automation run metadata)
- Minimal relation(s): Chronicle <-> LinkChecks (one-to-many) via a relation property on LinkChecks back to Chronicle.

Fixed option dictionaries

Copy these option dictionaries as-is into any create-schema calls or templates.

Emotion (options)

```
- Calm
- Curious
- Concerned
- Excited
```

Intent (options)

```
- Observe
- Explore
- Act
- Archive
```

Status (Enriched)

```
- New
- Enriched
- Ready for Pulse
- Archived
```

Status (Ingestion)

```
- New
- Parsed
- Error
```

Status (Archived)

```
- Archived
```

Init script expectations

The init script (not included here) should expect the following environment variables:

- NOTION_TOKEN — the Notion integration token
- PARENT_PAGE_ID — the Notion page under which the databases will be created
- NOTION_VERSION — set to `2025-09-03` (recommended for consistent API behavior)

Preflight checklist

- Ensure NOTION_TOKEN is valid and has the required scopes.
- Confirm the PARENT_PAGE_ID exists and the integration has been invited/shared to that page.
- Confirm NOTION_VERSION is set in the environment (recommended default: `2025-09-03`).

Idempotency rules (recommended implemention)

- Search by title for each database; if found, reuse the existing database.
- If a database is missing, create it.
- For relation properties, patch the target database to add the relation only if the relation property is absent.
- Avoid destructive operations: do not delete databases or wipe properties during init.

Rollback note

- The init flow is additive by design. Changes are non-destructive and intended to be safe to re-run.
- If manual rollback is required, remove the added databases or revert the schema via the Notion UI; the script will not perform destructive cleanup automatically.
