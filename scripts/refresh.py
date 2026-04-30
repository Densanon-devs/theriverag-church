"""
Refresh dynamic feeds for theriverag.church.

Pulls public sources (no credentials) and writes JSON files into site/data/
that the frontend JS reads on page load.

Sources:
  - YouTube channel RSS  -> latest 15 videos (sermons.json)

Usage:
  python scripts/refresh.py

Run via GitHub Actions on a daily cron, or locally before pushing.
"""
import json
import re
import sys
from pathlib import Path
from urllib import request

CHANNEL_ID = "UC9waM1-e8dY3yNQH5-6pAvw"
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "site" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch(url: str) -> str:
    req = request.Request(url, headers={"User-Agent": "Mozilla/5.0 (theriverag-church refresh)"})
    with request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def refresh_sermons() -> int:
    feed = fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}")
    entries = re.findall(r"<entry>(.*?)</entry>", feed, re.DOTALL)
    items = []
    for e in entries:
        vid = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", e)
        title = re.search(r"<title>([^<]+)</title>", e)
        published = re.search(r"<published>([^<]+)</published>", e)
        if not (vid and title and published):
            continue
        items.append({
            "videoId":   vid.group(1),
            "title":     title.group(1).strip(),
            "published": published.group(1),
            "url":       f"https://www.youtube.com/watch?v={vid.group(1)}",
            "thumbnail": f"https://i.ytimg.com/vi/{vid.group(1)}/hqdefault.jpg",
        })
    out = OUT_DIR / "sermons.json"
    out.write_text(json.dumps(items, indent=2), encoding="utf-8")
    return len(items)


def main() -> int:
    n = refresh_sermons()
    print(f"sermons.json: {n} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
