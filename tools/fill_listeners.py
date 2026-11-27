"""
Fill monthly listeners in data/master.csv from each artist's public Spotify page.

Step 3 of the track database. Runs in GitHub Actions ("Fill monthly listeners").
The Spotify API doesn't give monthly listeners, but every public artist page
carries a summary line like "Artist · 47.1M monthly listeners.", which this
reads. Big artists are rounded by Spotify (47.1M); small ones are exact.

Monthly listeners change all the time, so every run refreshes every artist.
One page per artist (not per song), about one per second.

Note: Spotify's terms don't allow automated collection from its website.
Dan accepted this for a low-volume pull (~70 pages, a few times a year).

Usage:
    python tools/fill_listeners.py
"""

import csv
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
MASTER_CSV = REPO / "data" / "master.csv"

COLUMNS = ["monthly_listeners", "monthly_listeners_text", "listeners_checked_at"]
PATTERN = re.compile(r"([\d.,]+)\s*([KMB])?\s+monthly listeners?", re.IGNORECASE)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; UnchartedTracks/1.0; +https://github.com/danielwipert/uncharted.tracks)",
    "Accept-Language": "en-US,en;q=0.9",
}


def to_number(amount, suffix):
    """'47.1', 'M' -> 47100000; '1,234', None -> 1234."""
    value = float(amount.replace(",", ""))
    value *= {"K": 1e3, "M": 1e6, "B": 1e9}.get((suffix or "").upper(), 1)
    return int(round(value))


def read_listeners(session, artist_id):
    """Return (number, text) or (None, reason)."""
    url = f"https://open.spotify.com/artist/{artist_id}"
    for attempt in range(4):
        try:
            response = session.get(url, timeout=30)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if response.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** (attempt + 1))
            continue
        if not response.ok:
            return None, f"page error {response.status_code}"
        match = PATTERN.search(response.text)
        if not match:
            return None, "no listener count on page"
        return to_number(*match.groups()), match.group(0)
    return None, "Spotify didn't answer"


def summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def main():
    if not MASTER_CSV.exists():
        sys.exit("::error::data/master.csv not found. Run 'Pull from Spotify' first.")
    with MASTER_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = list(reader.fieldnames or [])
    columns += [c for c in COLUMNS if c not in columns]

    artists = list(dict.fromkeys(r["spotify_artist_id"] for r in rows if r.get("spotify_artist_id")))
    names = {r["spotify_artist_id"]: r["artist"] for r in rows}
    print(f"Reading monthly listeners for {len(artists)} artists...\n")

    session = requests.Session()
    session.headers.update(HEADERS)
    results, missing = {}, []
    for i, artist_id in enumerate(artists, 1):
        number, text = read_listeners(session, artist_id)
        results[artist_id] = (number, text)
        if number is None:
            missing.append(f"{names[artist_id]} ({text})")
        print(f"  {i:>3}. {names[artist_id]}: {f'{number:,}' if number is not None else text}")
        time.sleep(1)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for r in rows:
        number, text = results.get(r.get("spotify_artist_id"), (None, ""))
        if number is not None:  # keep the last good number if this run missed it
            r["monthly_listeners"] = number
            r["monthly_listeners_text"] = text
            r["listeners_checked_at"] = today

    with MASTER_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    got = len(artists) - len(missing)
    ranked = sorted(((results[a][0], names[a]) for a in artists if results[a][0] is not None))
    lines = ["## Fill monthly listeners", "",
             f"Got monthly listeners for **{got} of {len(artists)}** artists.", ""]
    if ranked:
        lines += [f"Smallest: {ranked[0][1]} ({ranked[0][0]:,}) · Biggest: {ranked[-1][1]} ({ranked[-1][0]:,})", ""]
    if missing:
        lines += ["Missed (kept any earlier number):", ""] + [f"- {m}" for m in missing]
    print("\n" + lines[2])
    summary("\n".join(lines))
    if got == 0 and artists:
        sys.exit("::error::No listener counts found. Spotify may have changed its pages or blocked the run.")


if __name__ == "__main__":
    main()
