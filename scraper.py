#!/usr/bin/env python3
"""
Scrapes Goodreads genre shelves for well-rated, recent books, then checks each
candidate against Amazon Australia to see if it's included in Kindle Unlimited.
Writes the result to data.json for the static frontend (index.html) to read.

Run this whenever you want fresh data:
    python3 scraper.py
Then commit + push data.json to publish the update (see README.md).

No third-party packages required (stdlib only).
"""

import html
import json
import random
import re
import subprocess
import time
import urllib.parse
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config — tweak these as your taste evolves.
# ---------------------------------------------------------------------------

MIN_RATING = 4.0
YEARS_BACK = 8  # only keep books published in the last N years

# Goodreads "shelf" tags to pull candidates from, grouped under the genre
# label shown in the app. A book can legitimately appear under multiple tags
# or multiple genres — it just gets merged.
GENRE_SHELF_TAGS = {
    "Romance": [
        "romance",
        "romance-novels",
        "contemporary-romance",
        "romantic-comedy",
        "chick-lit",
        "new-adult-romance",
    ],
    "Comedy": [
        "humor",
        "humorous",
        "humorous-fiction",
        "funny",
        "comedy",
        "satire",
    ],
    "Fantasy": [
        "epic-fantasy",
        "humorous-fantasy",
        "humourous-fantasy",
        "fantasy",
        "high-fantasy",
    ],
    "Rom-Com": [
        "rom-com",
    ],
}

AMAZON_DOMAIN = "amazon.com.au"  # change if you're on a different KU marketplace

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

OUTPUT_FILE = "data.json"

# ---------------------------------------------------------------------------
# Networking helpers
# ---------------------------------------------------------------------------


def fetch(url):
    # Shell out to curl rather than urllib: macOS's python.org builds often
    # ship without a working default CA bundle, while curl uses the system
    # trust store and Just Works.
    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "--compressed",
                "-A", USER_AGENT,
                "-H", "Accept-Language: en-AU,en;q=0.9",
                "--max-time", "20",
                url,
            ],
            capture_output=True,
            timeout=25,
        )
    except subprocess.TimeoutExpired:
        print(f"  ! fetch timed out for {url}")
        return None
    if result.returncode != 0 or not result.stdout:
        print(f"  ! fetch failed for {url} (curl exit {result.returncode})")
        return None
    return result.stdout.decode("utf-8", errors="ignore")


def polite_sleep(lo=1.0, hi=2.2):
    time.sleep(random.uniform(lo, hi))


# ---------------------------------------------------------------------------
# Goodreads shelf scraping
# ---------------------------------------------------------------------------

SHELF_ENTRY_RE = re.compile(
    r'<a class="bookTitle" href="(?P<href>/book/show/[^"]+)">(?P<title>[^<]+)</a>.*?'
    r"itemprop=['\"]name['\"]>(?P<author>[^<]+)<.*?"
    r"avg rating (?P<rating>[\d.]+)\s*—\s*"
    r"[\d,]+\s*ratings\s*(?:—\s*published\s*(?P<year>\d{4}))?",
    re.S,
)

FORMAT_SUFFIX_RE = re.compile(
    r"\s*\((?:Paperback|Hardcover|Kindle Edition|ebook|E-?book|"
    r"Mass Market Paperback|Audiobook|Audio CD|Library Binding)\)\s*$",
    re.I,
)


def clean_title(raw_title):
    """Strip a trailing format tag like '(Paperback)', decode entities."""
    t = html.unescape(raw_title).strip()
    t = FORMAT_SUFFIX_RE.sub("", t)
    return t.strip()


def search_title(display_title):
    """Further strip any trailing series/parenthetical info for Amazon search."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", display_title).strip()


def scrape_shelf(tag):
    url = f"https://www.goodreads.com/shelf/show/{tag}"
    html_text = fetch(url)
    if not html_text:
        return []
    entries = []
    for m in SHELF_ENTRY_RE.finditer(html_text):
        if not m.group("year"):
            continue
        entries.append(
            {
                "book_id": m.group("href").split("/")[-1],
                "goodreads_url": "https://www.goodreads.com" + m.group("href"),
                "title": clean_title(m.group("title")),
                "author": html.unescape(m.group("author")).strip(),
                "rating": float(m.group("rating")),
                "pub_year": int(m.group("year")),
            }
        )
    return entries


def collect_candidates(current_year):
    """Returns dict keyed by book_id -> book dict (with 'genres' set)."""
    candidates = {}
    for genre, tags in GENRE_SHELF_TAGS.items():
        for tag in tags:
            print(f"Scraping Goodreads shelf '{tag}' ({genre})...")
            entries = scrape_shelf(tag)
            polite_sleep()
            for e in entries:
                if e["rating"] < MIN_RATING:
                    continue
                if e["pub_year"] < current_year - YEARS_BACK:
                    continue
                existing = candidates.get(e["book_id"])
                if existing:
                    existing["genres"].add(genre)
                else:
                    e["genres"] = {genre}
                    candidates[e["book_id"]] = e
    return candidates


# ---------------------------------------------------------------------------
# Amazon Kindle Unlimited lookup
# ---------------------------------------------------------------------------

RESULT_BLOCK_RE = re.compile(r'(?=data-component-type="s-search-result")')
ASIN_RE = re.compile(r'data-asin="([^"]*)"')
TITLE_RE = re.compile(r"<h2[^>]*>.*?<span[^>]*>([^<]+)</span>", re.S)


def normalize(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def check_kindle_unlimited(title, author):
    query = urllib.parse.quote(f"{title} {author}")
    url = f"https://www.{AMAZON_DOMAIN}/s?k={query}&i=digital-text"
    html_text = fetch(url)
    if not html_text:
        return None  # unknown — request failed

    if "bm-verify" in html_text or len(html_text) < 5000:
        # Amazon's bot-detection interstitial — not a real results page.
        # This happens if requests come in too fast; we don't try to solve
        # it, we just mark the book unknown and move on.
        print("    (Amazon bot-check triggered — marking unknown)")
        return None

    blocks = RESULT_BLOCK_RE.split(html_text)[1:]
    target = normalize(title)[:20]
    for block in blocks:
        asin_m = ASIN_RE.search(block)
        if not asin_m or not asin_m.group(1):
            continue
        title_m = TITLE_RE.search(block)
        block_title = normalize(title_m.group(1)) if title_m else ""
        if target and target not in block_title:
            continue
        return "apex-kindle-program-badge" in block

    # No confident title match — fall back to the first real result, best-effort.
    for block in blocks:
        asin_m = ASIN_RE.search(block)
        if asin_m and asin_m.group(1):
            return "apex-kindle-program-badge" in block
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    now = datetime.now(timezone.utc)
    current_year = now.year

    candidates = collect_candidates(current_year)
    print(f"\n{len(candidates)} unique candidates meet the rating/year bar. "
          f"Checking Kindle Unlimited status on {AMAZON_DOMAIN}...\n")

    books = []
    for i, c in enumerate(sorted(candidates.values(), key=lambda b: -b["rating"]), 1):
        print(f"[{i}/{len(candidates)}] {c['title']} — {c['author']}")
        ku = check_kindle_unlimited(search_title(c["title"]), c["author"])
        books.append(
            {
                "title": c["title"],
                "author": c["author"],
                "genres": sorted(c["genres"]),
                "rating": c["rating"],
                "pub_year": c["pub_year"],
                "goodreads_url": c["goodreads_url"],
                "ku_status": ku,  # True / False / None (unknown)
                "last_checked": now.strftime("%Y-%m-%d"),
            }
        )
        polite_sleep(3.0, 6.0)

    books.sort(key=lambda b: -b["rating"])

    output = {"generated_at": now.isoformat(), "books": books}
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    ku_yes = sum(1 for b in books if b["ku_status"] is True)
    ku_no = sum(1 for b in books if b["ku_status"] is False)
    ku_unknown = sum(1 for b in books if b["ku_status"] is None)
    print(f"\nWrote {len(books)} books to {OUTPUT_FILE}")
    print(f"  Kindle Unlimited: {ku_yes} yes / {ku_no} no / {ku_unknown} unknown")


if __name__ == "__main__":
    main()
