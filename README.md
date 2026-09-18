# KU Book Finder

A personal tool to solve one problem: Goodreads doesn't let you filter by
Kindle Unlimited availability, so it's easy to shelve a book as "Want to
Read" and only discover later that reading it means paying.

This scrapes Goodreads for well-rated, recent Romance and Comedy books,
checks each one against Kindle Unlimited (Amazon Australia), and serves the
result as a simple filterable table. Find a book here → tap through to its
Goodreads page → hit "Want to Read" there as usual.

## How it works

- **`scraper.py`** — run locally. Pulls candidate books from several
  Goodreads genre "shelf" pages (romance/comedy and related tags), keeps
  ones rated **4.0+** and published in the **last 8 years**, then checks
  each surviving candidate against `amazon.com.au` for a Kindle Unlimited
  badge. Writes `data.json`.
- **`index.html` / `app.js` / `style.css`** — a static page that reads
  `data.json` and lets you filter by genre, minimum rating, publish-year
  range, and Kindle-Unlimited-only, sorted by rating or year.

No dependencies beyond Python 3 and `curl` (both come with macOS).

## Refreshing the data

```bash
cd ~/ku-book-finder
python3 scraper.py
```

This takes a few minutes (it deliberately paces requests to avoid hammering
Goodreads/Amazon). When it's done, `data.json` has the new results — reload
the page locally, or commit + push to update the hosted version:

```bash
git add -A && git commit -m "Refresh book data" && git push
```

Run it whenever you feel like browsing — there's no automatic schedule.
Weekly-ish is plenty; these lists don't change fast.

## Known limitations (read before assuming the data is gospel)

- **Amazon blocks scrapers.** During testing, ~30 lookups in a row was
  enough to trigger Amazon's bot-detection challenge, after which every
  further lookup that run came back "Unknown" instead of Yes/No. The
  script paces requests (3–6s apart) to reduce this, and always fails soft
  — a blocked/failed lookup shows as **Unknown**, never a wrong answer —
  but if you see a lot of Unknowns, wait a while (try again the next day)
  before re-running. This is a real, observed limitation, not a
  hypothetical one — don't be surprised by it.
- **Genre tagging is community-sourced.** Books are pulled from Goodreads
  shelf tags like "romance" and "humor" that users apply themselves, so
  the odd mis-tagged book (e.g. a witty literary novel showing up under
  Comedy) can slip through.
- **Only ~50 books per shelf tag.** Goodreads' shelf pages don't paginate,
  so each tag contributes its top 50 by popularity, filtered down by
  rating/year. Combined across several related tags per genre this gives
  a decent-sized pool, but it's not exhaustive — it's the well-known,
  well-rated end of each genre, not everything ever published.
- **KU marketplace is `amazon.com.au`.** If you ever subscribe from a
  different country's Amazon store, change `AMAZON_DOMAIN` at the top of
  `scraper.py`.

## Tuning

Everything adjustable lives at the top of `scraper.py`:
`MIN_RATING`, `YEARS_BACK`, `GENRE_SHELF_TAGS` (add/remove Goodreads shelf
tags or whole genres), `AMAZON_DOMAIN`.
