#!/usr/bin/env python3
# astra_notion_init.py — v1-lite
"""Astra Notion v1-lite initializer

- Idempotent creation of three Notion databases: Chronicle, LinkChecks, RunLog
- Adds a Relation from LinkChecks -> Chronicle if absent
- Inserts a smoke-test page+link to verify setup
- Compatible with NOTION_VERSION=2025-09-03
- Uses environment variables: NOTION_TOKEN, PARENT_PAGE_ID, NOTION_VERSION
- Verbose logging (--verbose) and optional log file (--log-file)
- Uses requests only (requirements listed in scripts/requirements.txt)
"""
from __future__ import annotations
import argparse
import base64
import json
import logging
import os
import sys
import time
import uuid
from typing import Dict, List, Optional

import requests

API_BASE = "https://api.notion.com/v1"
DEFAULT_NOTION_VERSION = "2025-09-03"

# Minimal retry/backoff configuration
MAX_ATTEMPTS = 6
BACKOFF_BASE = 1.0


def setup_logger(verbose: bool, log_file: Optional[str]):
    logger = logging.getLogger("astra_init")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


def notion_request_with_backoff(method: str, path: str, token: str, notion_version: str, **kwargs) -> requests.Response:
    url = API_BASE + path
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {token}",
        "Notion-Version": notion_version,
        "Content-Type": "application/json",
    })
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.request(method, url, headers=headers, timeout=15, **kwargs)
            if resp.status_code in (429, 500, 502, 503, 504):
                # Transient error -> consider retry
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    sleep = float(retry_after)
                else:
                    sleep = BACKOFF_BASE * (2 ** (attempt - 1))
                    if sleep > 10:
                        sleep = 10
                if attempt >= MAX_ATTEMPTS:
                    resp.raise_for_status()
                time.sleep(sleep)
                continue
            return resp
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt >= MAX_ATTEMPTS:
                raise
            sleep = BACKOFF_BASE * (2 ** (attempt - 1))
            time.sleep(sleep)


def search_database_by_title(title: str, token: str, notion_version: str) -> Optional[Dict]:
    # Notion search for object type database
    payload = {"query": title, "filter": {"property": "object", "value": "database"}}
    resp = notion_request_with_backoff("POST", "/search", token, notion_version, json=payload)
    resp.raise_for_status()
    data = resp.json()
    for r in data.get("results", []):
        prop_title = None
        # extract title if available
        if "title" in r:
            # r is a database object
            t = r.get("title", [])
            if t and isinstance(t, list):
                prop_title = "".join([x.get("plain_text", "") for x in t])
        if prop_title and prop_title == title:
            return r
    return None


def create_database(title: str, parent_page_id: str, properties: Dict[str, Dict], token: str, notion_version: str) -> Dict:
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": properties,
    }
    resp = notion_request_with_backoff("POST", "/databases", token, notion_version, json=payload)
    resp.raise_for_status()
    return resp.json()


def patch_database_add_property(database_id: str, property_name: str, prop_schema: Dict, token: str, notion_version: str) -> Dict:
    payload = {"properties": {property_name: prop_schema}}
    resp = notion_request_with_backoff("PATCH", f"/databases/{database_id}", token, notion_version, json=payload)
    resp.raise_for_status()
    return resp.json()


def create_page(database_id: str, properties: Dict[str, Dict], token: str, notion_version: str) -> Dict:
    payload = {"parent": {"database_id": database_id}, "properties": properties}
    resp = notion_request_with_backoff("POST", "/pages", token, notion_version, json=payload)
    resp.raise_for_status()
    return resp.json()


def ensure_select_options(property_def: Dict, options: List[str]) -> Dict:
    # property_def is a select property schema
    return {
        "select": {
            "options": [{"name": opt} for opt in options]
        }
    }


def make_select_property(name: str, options: List[str]) -> Dict:
    return {"name": name, "select": {"options": [{"name": o} for o in options]}}


def main():
    parser = argparse.ArgumentParser(description="Astra Notion v1-lite initializer")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--log-file", type=str, default=None, help="Optional log file")
    args = parser.parse_args()

    token = os.getenv("NOTION_TOKEN")
    parent_page = os.getenv("PARENT_PAGE_ID")
    notion_version = os.getenv("NOTION_VERSION", DEFAULT_NOTION_VERSION)

    logger = setup_logger(args.verbose, args.log_file)

    if not token or not parent_page:
        logger.error("NOTION_TOKEN and PARENT_PAGE_ID must be set in environment")
        sys.exit(2)

    logger.info("Starting Astra Notion v1-lite init")

    # Define DB titles
    CHRONICLE_TITLE = "Chronicle"
    LINKCHECKS_TITLE = "LinkChecks"
    RUNLOG_TITLE = "RunLog"

    # Fixed option dictionaries
    EMOTION_OPTS = ["Calm", "Curious", "Concerned", "Excited"]
    INTENT_OPTS = ["Observe", "Explore", "Act", "Archive"]
    STATUS_ENRICHED = ["New", "Enriched", "Ready for Pulse", "Archived"]
    STATUS_INGESTION = ["New", "Parsed", "Error"]
    STATUS_ARCHIVED = ["Archived"]

    # Ensure Chronicle exists
    try:
        chron = search_database_by_title(CHRONICLE_TITLE, token, notion_version)
        if chron:
            chron_id = chron.get("id")
            logger.info(f"✅ found existing DB: {CHRONICLE_TITLE} ({chron_id})")
        else:
            # Chronicle properties (example)
            chron_props = {
                "Title": {"title": {}},
                "Emotion": {"select": {"options": [{"name": o} for o in EMOTION_OPTS]}},
                "Intent": {"select": {"options": [{"name": o} for o in INTENT_OPTS]}},
                "Status (Enriched)": {"select": {"options": [{"name": o} for o in STATUS_ENRICHED]}},
            }
            new_chron = create_database(CHRONICLE_TITLE, parent_page, chron_props, token, notion_version)
            chron_id = new_chron.get("id")
            logger.info(f"✅ created DB: {CHRONICLE_TITLE} ({chron_id})")
    except Exception as exc:
        logger.exception("Failed to ensure Chronicle DB")
        sys.exit(1)

    # Ensure LinkChecks exists and has relation to Chronicle
    try:
        link = search_database_by_title(LINKCHECKS_TITLE, token, notion_version)
        if link:
            link_id = link.get("id")
            logger.info(f"✅ found existing DB: {LINKCHECKS_TITLE} ({link_id})")
        else:
            link_props = {
                "Title": {"title": {}},
                "URL": {"url": {}},
                "Status (Ingestion)": {"select": {"options": [{"name": o} for o in STATUS_INGESTION]}},
                # Relation will be patched in if necessary
            }
            new_link = create_database(LINKCHECKS_TITLE, parent_page, link_props, token, notion_version)
            link_id = new_link.get("id")
            logger.info(f"✅ created DB: {LINKCHECKS_TITLE} ({link_id})")

        # Check for relation property to Chronicle, add if absent
        link_db = requests.get(f"{API_BASE}/databases/{link_id}", headers={
            "Authorization": f"Bearer {token}", "Notion-Version": notion_version
        })
        link_db.raise_for_status()
        link_schema = link_db.json().get("properties", {})
        if "Chronicle" not in link_schema:
            # add relation property
            rel_prop = {"relation": {"database_id": chron_id}}
            patch_database_add_property(link_id, "Chronicle", rel_prop, token, notion_version)
            logger.info(f"✅ relation added: {LINKCHECKS_TITLE}.Chronicle -> {CHRONICLE_TITLE}")
        else:
            logger.info(f"✅ relation exists on {LINKCHECKS_TITLE}")
    except Exception as exc:
        logger.exception("Failed to ensure LinkChecks DB and relation")
        sys.exit(1)

    # Ensure RunLog exists
    try:
        runlog = search_database_by_title(RUNLOG_TITLE, token, notion_version)
        if runlog:
            runlog_id = runlog.get("id")
            logger.info(f"✅ found existing DB: {RUNLOG_TITLE} ({runlog_id})")
        else:
            runlog_props = {
                "Title": {"title": {}},
                "RunDate": {"date": {}},
                "Status": {"select": {"options": [{"name": "OK"}, {"name": "Fail"}]}}
            }
            new_runlog = create_database(RUNLOG_TITLE, parent_page, runlog_props, token, notion_version)
            runlog_id = new_runlog.get("id")
            logger.info(f"✅ created DB: {RUNLOG_TITLE} ({runlog_id})")
    except Exception as exc:
        logger.exception("Failed to ensure RunLog DB")
        sys.exit(1)

    # Smoke test: insert a page into Chronicle and a linked LinkChecks record
    try:
        test_title = f"astra-init-test-{uuid.uuid4().hex[:8]}"
        page_props = {
            "Title": {"title": [{"text": {"content": test_title}}]},
            "Emotion": {"select": {"name": EMOTION_OPTS[0]}},
            "Intent": {"select": {"name": INTENT_OPTS[0]}},
            "Status (Enriched)": {"select": {"name": STATUS_ENRICHED[0]}},
        }
        created_page = create_page(chron_id, page_props, token, notion_version)
        page_id = created_page.get("id")
        logger.info(f"✅ page inserted into {CHRONICLE_TITLE}: {test_title} ({page_id})")

        # Create LinkChecks entry linking to the Chronicle page
        link_props = {
            "Title": {"title": [{"text": {"content": f"link-{test_title}"}}]},
            "URL": {"url": "https://example.invalid/"},
            "Status (Ingestion)": {"select": {"name": STATUS_INGESTION[0]}},
            "Chronicle": {"relation": [{"id": page_id}]}
        }
        created_lc = create_page(link_id, link_props, token, notion_version)
        logger.info(f"✅ link record inserted into {LINKCHECKS_TITLE} and linked to Chronicle")

    except Exception as exc:
        logger.exception("Smoke test failed")
        sys.exit(1)

    logger.info("🎉 v1-lite setup complete!")


if __name__ == "__main__":
    main()
