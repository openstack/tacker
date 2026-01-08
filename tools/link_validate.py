# Copyright (C) 2026 NEC, Corp.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

#!/usr/bin/env python3

import os
import sys
import re
import requests
import configparser
from urllib.parse import urljoin, urldefrag
from collections import deque
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

# ------------------------------------------------------------
# Load Configuration
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "link_validate_config.conf")

config = configparser.ConfigParser()
if not config.read(CONFIG_FILE):
    print(f"[ERROR] Config file not found: {CONFIG_FILE}")
    sys.exit(2)

BASE_URL = config.get("general", "base_url")
ALLOWED_DOMAIN = config.get("general", "allowed_domain")
TIMEOUT = config.getint("general", "timeout")
VERIFY_SSL = config.getboolean("general", "verify_ssl")

SKIP_EXT = tuple(x.strip() for x in config.get("skip", "extensions").split(","))
SKIP_PATTERNS = [x.strip() for x in config.get("skip", "patterns").split(",")]

# ------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------
def is_valid_doc_link(url):
    """Allow only OpenStack documentation URLs."""
    return url.startswith(ALLOWED_DOMAIN)

def is_placeholder_or_invalid(url):
    """Filter malformed or placeholder links."""
    if re.match(r"^https:[^/]", url):  # malformed https:10.0.0.1
        return True
    for pattern in SKIP_PATTERNS:
        if pattern in url:
            return True
    return False

def validate_url(url):
    """Check if a URL is reachable."""
    try:
        resp = requests.head(
            url,
            allow_redirects=True,
            timeout=TIMEOUT,
            verify=VERIFY_SSL,
        )
        if resp.status_code >= 400:
            resp = requests.get(url, timeout=TIMEOUT, verify=VERIFY_SSL)
        return resp.status_code < 400
    except RequestException:
        return False

# ------------------------------------------------------------
# Crawl Logic
# ------------------------------------------------------------
def crawl(base_url):
    """
    Crawl documentation pages starting from the given base URL
    and validate the links found on those pages.

    The crawler performs the following behavior:
    - Recursively visits pages under BASE_URL (Tacker documentation).
    - Extracts all hyperlinks from those pages.
    - Validates links that belong to the allowed OpenStack documentation domain.
    - External OpenStack documentation links are validated but not recursively crawled.
    - Skips URLs with unwanted extensions or placeholder patterns.
    - The crawl stops when there are no more pages to visit.

    Args:
        base_url (str): The starting documentation page.

    Returns:
        list: A list of tuples containing (url, "PASS" or "FAIL")
        based on the link validation result.
    """
    visited = set()
    to_visit = deque([base_url])
    checked_external_docs = set()
    results = []

    while to_visit:
        url = to_visit.popleft()
        url, _ = urldefrag(url)

        if url in visited or url.endswith(SKIP_EXT):
            continue

        if is_placeholder_or_invalid(url):
            print(f"[SKIP] Placeholder or invalid URL: {url}")
            continue

        visited.add(url)

        is_tacker_doc = url.startswith(BASE_URL)
        label = "Tacker doc page" if is_tacker_doc else "Referenced OpenStack doc"

        print(f"[INFO] Checking {label}: {url}")
        ok = validate_url(url)
        results.append((url, "PASS" if ok else "FAIL"))

        if not ok:
            continue

        # Only recurse inside Tacker documentation
        if not is_tacker_doc:
            continue

        try:
            resp = requests.get(url, timeout=TIMEOUT, verify=VERIFY_SSL)
            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"]
                new_url = urljoin(url, href)
                new_url, _ = urldefrag(new_url)

                if new_url.endswith(SKIP_EXT):
                    continue
                if is_placeholder_or_invalid(new_url):
                    continue
                if not is_valid_doc_link(new_url):
                    continue

                if new_url.startswith(BASE_URL):
                    if new_url not in visited:
                        to_visit.append(new_url)
                else:
                    # Referenced OpenStack project doc (non-recursive)
                    if new_url not in checked_external_docs:
                        print(f"  ↳ Found referenced doc: {new_url}")
                        ok_ref = validate_url(new_url)
                        results.append((new_url, "PASS" if ok_ref else "FAIL"))
                        checked_external_docs.add(new_url)

        except Exception as exc:
            print(f"[WARN] Failed to parse page {url}: {exc}")

    return results

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    results = crawl(BASE_URL)

    total = len(results)
    passed = sum(1 for _, r in results if r == "PASS")
    failed_urls = [u for u, r in results if r == "FAIL"]

    print("\n==== Link Validation Summary ====")
    print(f"Total Checked : {total}")
    print(f"Passed        : {passed}")
    print(f"Failed        : {len(failed_urls)}")

    if failed_urls:
        print("\n Broken documentation links detected:\n")
        for url in failed_urls:
            print(f"  - {url}")

        print("\n[ERROR] Documentation link validation failed.")
        sys.exit(1)

    print("\n All documentation links are valid.")
    sys.exit(0)

if __name__ == "__main__":
    main()

