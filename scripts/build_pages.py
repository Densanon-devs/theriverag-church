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
import html as _html
import re
import sys
from datetime import date as _date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Install pyyaml: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "_data"
TARGETS = [ROOT / "index.html", ROOT / "about" / "index.html", ROOT / "podcasts" / "index.html"]

# Blog: the church-ops pipeline commits content/blog/<date>-<slug>.md files
# (YAML frontmatter + HTML body); we render those into /blog/<slug>/index.html
# pages plus a /blog/ index, wrapped in the site shell.
BLOG_SRC = ROOT / "content" / "blog"
BLOG_OUT = ROOT / "blog"


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


# ─── Blog rendering ─────────────────────────────────────────────────────

_ESC = _html.escape
_MONTHS = ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]

# Social SVGs reused in the page header (same markup as the rest of the site).
_SVG_IG = ('<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2.2c3.2 0 3.6 0 4.8.1 1.2.1 1.8.2 2.2.4.6.2 1 .5 1.4.9.4.4.7.8.9 1.4.2.4.4 1 .4 2.2.1 1.2.1 1.6.1 4.8s0 3.6-.1 4.8c-.1 1.2-.2 1.8-.4 2.2-.2.6-.5 1-.9 1.4-.4.4-.8.7-1.4.9-.4.2-1 .4-2.2.4-1.2.1-1.6.1-4.8.1s-3.6 0-4.8-.1c-1.2-.1-1.8-.2-2.2-.4-.6-.2-1-.5-1.4-.9-.4-.4-.7-.8-.9-1.4-.2-.4-.4-1-.4-2.2-.1-1.2-.1-1.6-.1-4.8s0-3.6.1-4.8c.1-1.2.2-1.8.4-2.2.2-.6.5-1 .9-1.4.4-.4.8-.7 1.4-.9.4-.2 1-.4 2.2-.4 1.2-.1 1.6-.1 4.8-.1zm0-2.2c-3.3 0-3.7 0-5 .1-1.3.1-2.2.3-3 .6-.8.3-1.5.7-2.2 1.4-.7.7-1.1 1.4-1.4 2.2-.3.8-.5 1.7-.6 3-.1 1.3-.1 1.7-.1 5s0 3.7.1 5c.1 1.3.3 2.2.6 3 .3.8.7 1.5 1.4 2.2.7.7 1.4 1.1 2.2 1.4.8.3 1.7.5 3 .6 1.3.1 1.7.1 5 .1s3.7 0 5-.1c1.3-.1 2.2-.3 3-.6.8-.3 1.5-.7 2.2-1.4.7-.7 1.1-1.4 1.4-2.2.3-.8.5-1.7.6-3 .1-1.3.1-1.7.1-5s0-3.7-.1-5c-.1-1.3-.3-2.2-.6-3-.3-.8-.7-1.5-1.4-2.2-.7-.7-1.4-1.1-2.2-1.4-.8-.3-1.7-.5-3-.6-1.3-.1-1.7-.1-5-.1zm0 5.8a6.2 6.2 0 100 12.4 6.2 6.2 0 000-12.4zm0 10.2a4 4 0 110-8 4 4 0 010 8zm6.4-10.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"/></svg>')
_SVG_FB = ('<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M22 12a10 10 0 10-11.6 9.9v-7H7.9v-2.9h2.5V9.8c0-2.5 1.5-3.9 3.7-3.9 1.1 0 2.2.2 2.2.2v2.5h-1.3c-1.2 0-1.6.8-1.6 1.6v1.9h2.8l-.5 2.9h-2.4v7A10 10 0 0022 12z"/></svg>')
_SVG_YT = ('<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M23.5 6.2a3 3 0 00-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 00.5 6.2C0 8.1 0 12 0 12s0 3.9.5 5.8c.3 1 1.1 1.8 2.1 2.1 1.9.5 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 002.1-2.1c.5-1.9.5-5.8.5-5.8s0-3.9-.5-5.8zM9.6 15.6V8.4l6.2 3.6-6.2 3.6z"/></svg>')


def _human_date(iso: str) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-")[:3])
        return f"{_MONTHS[m]} {d}, {y}"
    except Exception:
        return iso or ""


def _parse_post(md_path: Path) -> dict | None:
    """Parse a content/blog/*.md file: '---' YAML frontmatter, then an HTML body."""
    raw = md_path.read_text(encoding="utf-8").lstrip()
    if not raw.startswith("---"):
        return None
    nl = raw.find("\n")
    if nl == -1:
        return None
    close = raw.find("\n---", nl)
    if close == -1:
        return None
    fm_block = raw[nl + 1:close]
    after = raw[close + 4:]
    body = after.split("\n", 1)[1] if "\n" in after else ""
    body = body.lstrip("\n")
    try:
        fm = yaml.safe_load(fm_block) or {}
    except Exception:
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    title = str(fm.get("title") or "").strip() or md_path.stem
    slug = str(fm.get("slug") or "").strip().lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-") or re.sub(r"[^a-z0-9-]+", "-", md_path.stem.lower()).strip("-") or "post"
    dv = fm.get("date")
    iso = dv.isoformat() if isinstance(dv, _date) else str(dv or "").strip()
    return {
        "title": title,
        "slug": slug,
        "date_iso": iso,
        "date_human": _human_date(iso),
        "summary": str(fm.get("summary") or "").strip(),
        "youtube_url": str(fm.get("youtube_url") or "").strip(),
        "sermon_id": str(fm.get("sermon_id") or "").strip(),
        "body": body,
        "src": md_path,
    }


def _nav(prefix: str, active: str) -> str:
    a = lambda name: ' class="active"' if name == active else ""
    return (
        '<nav class="main-nav"><ul>'
        f'<li><a href="{prefix}podcasts/"{a("sermons")}>Sermons</a></li>'
        f'<li><a href="{prefix}about/"{a("about")}>About</a></li>'
        f'<li><a href="{prefix}blog/"{a("blog")}>Blog</a></li>'
        '<li><a href="https://theriveragchurch.churchcenter.com/giving" target="_blank" rel="noopener">Give</a></li>'
        '</ul></nav>'
    )


def _page(prefix: str, *, title: str, desc: str, canonical: str, og_type: str,
          active: str, body_html: str) -> str:
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/x-icon" href="{prefix}site/images/favicon.ico">
  <link rel="apple-touch-icon" href="{prefix}site/images/logo.png">
  <meta name="description" content="{_ESC(desc)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://theriverag.church/{canonical}">
  <meta property="og:title" content="{_ESC(title)}">
  <meta property="og:description" content="{_ESC(desc)}">
  <meta property="og:url" content="https://theriverag.church/{canonical}">
  <meta property="og:type" content="{og_type}">
  <title>{_ESC(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Oswald:wght@400;600;700&family=Abel&display=swap">
  <link rel="stylesheet" href="{prefix}css/styles.css">
  <link rel="stylesheet" href="{prefix}css/blog.css">
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <button class="menu-toggle" aria-label="Toggle navigation menu"><span></span><span></span><span></span></button>
      {_nav(prefix, active)}
      <a href="{prefix}" class="logo"><img src="{prefix}site/images/logo.png" alt="The River Church"></a>
      <div class="header-right">
        <ul class="social-icons">
          <li><a href="https://www.instagram.com/theriverag.church" target="_blank" rel="noopener" aria-label="Instagram">{_SVG_IG}</a></li>
          <li><a href="https://www.facebook.com/profile.php?id=100090242570915" target="_blank" rel="noopener" aria-label="Facebook">{_SVG_FB}</a></li>
          <li><a href="https://www.youtube.com/@theriverag.church" target="_blank" rel="noopener" aria-label="YouTube">{_SVG_YT}</a></li>
        </ul>
        <a href="https://theriveragchurch.churchcenter.com/people/forms/559632" target="_blank" rel="noopener" class="header-cta header-cta-desktop">Get Connected</a>
      </div>
    </div>
  </header>
{body_html}
  <footer class="site-footer">
    <div class="container">
      <div class="footer-grid">
        <div class="footer-col"><img src="{prefix}site/images/logo.png" alt="The River Church" class="footer-logo"><p>A place where you feel at home. A place where you can feel like family.</p></div>
        <div class="footer-col"><h4>Visit Us</h4><p>Meeting in Northwest Family Church West<br>19587 W Riverview Dr<br>Post Falls, ID 83854</p></div>
        <div class="footer-col"><h4>Contact</h4><p><a href="tel:+12083048536">(208) 304-8536</a><br><a href="mailto:steven@theriverag.church">steven@theriverag.church</a><br><a href="{prefix}privacy/">Privacy Policy</a> &middot; <a href="{prefix}terms/">Terms</a></p></div>
        <div class="footer-col"><h4>Connect</h4><ul class="social-links"><li><a href="https://www.facebook.com/profile.php?id=100090242570915" target="_blank" rel="noopener">Facebook</a></li><li><a href="https://www.instagram.com/theriverag.church" target="_blank" rel="noopener">Instagram</a></li><li><a href="https://www.youtube.com/@theriverag.church" target="_blank" rel="noopener">YouTube</a></li></ul></div>
      </div>
      <div class="footer-bottom"><p>&copy; <span id="year">2026</span> The River Church. All rights reserved.</p></div>
    </div>
  </footer>
  <script src="{prefix}js/main.js"></script>
  <script src="{prefix}js/dynamic.js"></script>
</body>
</html>
'''


def _render_post_page(p: dict) -> str:
    prefix = "../../"
    cta = ""
    if p["youtube_url"]:
        cta = (f'<div class="blog-cta">'
               f'<a href="{_ESC(p["youtube_url"])}" target="_blank" rel="noopener" class="btn">Watch on YouTube</a>'
               f'<a href="{prefix}#visit" class="btn btn-outline">Plan a visit</a>'
               f'</div>')
    body = f'''  <main class="blog-page">
    <article class="blog-post container">
      <p class="blog-back"><a href="{prefix}blog/">&larr; All sermon notes</a></p>
      <h1>{_ESC(p["title"])}</h1>
      <p class="blog-date">{_ESC(p["date_human"])}</p>
{p["body"]}
      <hr class="blog-rule">
      {cta}
    </article>
  </main>'''
    desc = p["summary"] or f'{p["title"]} — sermon recap from The River Church, Post Falls, Idaho.'
    return _page(prefix, title=f'{p["title"]} — The River Church', desc=desc,
                 canonical=f'blog/{p["slug"]}/', og_type="article", active="blog",
                 body_html=body)


def _render_blog_index(posts: list[dict]) -> str:
    prefix = "../"
    if posts:
        cards = "\n".join(
            f'''      <article class="blog-card">
        <h2><a href="{prefix}blog/{p["slug"]}/">{_ESC(p["title"])}</a></h2>
        <p class="blog-date">{_ESC(p["date_human"])}</p>
        <p class="blog-summary">{_ESC(p["summary"])}</p>
        <p><a class="blog-readmore" href="{prefix}blog/{p["slug"]}/">Read the recap &rarr;</a></p>
      </article>''' for p in posts
        )
    else:
        cards = '      <p class="blog-empty">Sermon recaps will appear here soon — check back after this week\'s message.</p>'
    body = f'''  <main class="blog-page">
    <section class="blog-hero container">
      <h1>Sermon Notes</h1>
      <p class="blog-lead">Weekly recaps of what we're learning together at The River Church &mdash; each with the full message embedded so you can catch up anytime.</p>
    </section>
    <section class="blog-list container">
{cards}
    </section>
  </main>'''
    return _page(prefix, title="Sermon Notes — The River Church",
                 desc="Weekly sermon recaps from The River Church in Post Falls, Idaho — read the message and watch it here.",
                 canonical="blog/", og_type="website", active="blog", body_html=body)


def build_blog() -> int:
    """Render content/blog/*.md into /blog/<slug>/index.html + /blog/index.html.
    Returns the number of pages written."""
    posts: list[dict] = []
    if BLOG_SRC.exists():
        for md in sorted(BLOG_SRC.glob("*.md")):
            p = _parse_post(md)
            if p:
                posts.append(p)
            else:
                print(f"  blog: skipped {md.name} (no/invalid frontmatter)")
    posts.sort(key=lambda p: (p["date_iso"], p["slug"]), reverse=True)

    BLOG_OUT.mkdir(parents=True, exist_ok=True)
    written = 0
    for p in posts:
        out_dir = BLOG_OUT / p["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(_render_post_page(p), encoding="utf-8")
        written += 1
    (BLOG_OUT / "index.html").write_text(_render_blog_index(posts), encoding="utf-8")
    written += 1
    print(f"  blog: {len(posts)} post(s) → {written} page(s) under /blog/")
    return written


def main() -> int:
    build_blog()

    data = load_data()
    if not data:
        print("No _data/*.yml files found; skipped _data substitution.")
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
