"""
Substitute editable content from _data/*.yml into the static HTML pages.

The admin CMS edits the YAML files. A GitHub Action runs this script on
push to main, which writes the rendered HTML back to the repo so Pages
serves the latest values.

Two ways to mark content as CMS-editable in the HTML:

  1. data-cms attribute (preferred, durable across builds):

         <div class="announcement-bar" data-cms="site.announcement_text">
             current text content
         </div>

     The script replaces the inner text of any element carrying a
     data-cms attribute with the resolved value. Attribute stays in
     place so the next build can re-substitute. Only works for elements
     whose content is plain text (no nested tags).

  2. {{path}} placeholder (one-shot, useful for first-render only):

         <p>{{site.hero_tagline}}</p>

     The script substitutes once. Placeholder is consumed after build.
     Use only for fields you don't expect to change after first
     publication, OR add a data-cms wrapper so future builds work.

Run locally:
    pip install pyyaml
    python scripts/build_pages.py
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Install pyyaml: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "_data"
TARGETS = [ROOT / "index.html", ROOT / "about" / "index.html", ROOT / "podcasts" / "index.html"]


def load_data() -> dict:
    """Read every YAML file in _data/ into a single dict, keyed by filename."""
    data: dict = {}
    if not DATA_DIR.exists():
        return data
    for f in DATA_DIR.glob("*.yml"):
        with open(f, "r", encoding="utf-8") as fh:
            data[f.stem] = yaml.safe_load(fh) or {}
    return data


def resolve(path: str, data: dict):
    """Resolve a dotted path like 'site.phone' or 'services.cards.0.heading'."""
    parts = path.split(".")
    cur = data
    for p in parts:
        if isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
        if cur is None:
            return None
    return cur


# Matches an opening tag carrying data-cms="path", its text-only content, and
# the matching closing tag of the SAME tag name. Surgical — touches nothing
# outside the matched content region, preserves the file's formatting.
_DATA_CMS_RE = re.compile(
    r'(?P<open><(?P<tag>[a-zA-Z][a-zA-Z0-9]*)\b[^>]*?\bdata-cms="(?P<path>[^"]+)"[^>]*>)'
    r'(?P<content>[^<]*?)'
    r'(?P<close></(?P=tag)\s*>)',
    re.DOTALL,
)


def render_data_cms(html: str, data: dict) -> tuple[str, int]:
    """Replace text content of elements carrying data-cms="path"."""
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        val = resolve(m.group("path"), data)
        if val is None:
            return m.group(0)
        new = str(val)
        if new.strip() == m.group("content").strip():
            return m.group(0)
        count += 1
        return m.group("open") + new + m.group("close")

    return _DATA_CMS_RE.sub(repl, html), count


def render_placeholders(html: str, data: dict) -> tuple[str, int]:
    """Replace {{path}} placeholders with resolved values (one-shot)."""
    pattern = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        val = resolve(m.group(1), data)
        if val is None:
            return m.group(0)
        count += 1
        return str(val)

    return pattern.sub(repl, html), count


def main() -> int:
    data = load_data()
    if not data:
        print("No _data/*.yml files found; nothing to build.")
        return 0

    print(f"Loaded data from {len(data)} file(s): {sorted(data.keys())}")
    total = 0
    for target in TARGETS:
        if not target.exists():
            continue
        original = target.read_text(encoding="utf-8")
        rendered, n_placeholder = render_placeholders(original, data)
        rendered, n_cms = render_data_cms(rendered, data)
        if rendered != original:
            target.write_text(rendered, encoding="utf-8")
            print(f"  {target.relative_to(ROOT)}: {n_cms} data-cms + {n_placeholder} placeholder")
            total += n_cms + n_placeholder
        else:
            print(f"  {target.relative_to(ROOT)}: no changes")
    print(f"Total: {total} substitution(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
