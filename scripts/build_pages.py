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
TARGETS = [
    ROOT / "index.html",
    ROOT / "about" / "index.html",
    ROOT / "podcasts" / "index.html",
    ROOT / "privacy" / "index.html",
    ROOT / "terms" / "index.html",
]

# Blog: the church-ops pipeline commits content/blog/<date>-<slug>.md files
# (YAML frontmatter + HTML body); we render those into /blog/<slug>/index.html
# pages plus a /blog/ index, wrapped in the site shell.
BLOG_SRC = ROOT / "content" / "blog"
BLOG_OUT = ROOT / "blog"


def load_data() -> dict:
    """Read every YAML file in _data/ into a single dict, keyed by filename.
    Files under _data/pages/ are nested under a 'pages' key so they resolve
    via paths like `pages.home.blocks.0.heading`."""
    data: dict = {}
    if not DATA_DIR.exists():
        return data
    for f in DATA_DIR.glob("*.yml"):
        with open(f, "r", encoding="utf-8") as fh:
            data[f.stem] = yaml.safe_load(fh) or {}
    pages_dir = DATA_DIR / "pages"
    if pages_dir.is_dir():
        pages: dict = {}
        for f in pages_dir.glob("*.yml"):
            with open(f, "r", encoding="utf-8") as fh:
                pages[f.stem] = yaml.safe_load(fh) or {}
        if pages:
            data["pages"] = pages
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

# SSI-style include directives, with idempotent marker comments wrapping the
# rendered output. On first build, an `<!--#include -->` directive gets a
# matching <!--inc:start … --> … <!--inc:end --> block appended; on later
# builds we find that block and replace it from the current partial, so the
# source file always carries both the directive (the source of truth) and a
# fresh inlined copy that GitHub Pages serves directly.
_INCLUDE_RE = re.compile(
    r'<!--\s*#include\s+file="(?P<path>[^"]+)"\s*-->'
    r'(?P<rendered>\s*<!--\s*inc:start[^>]*-->.*?<!--\s*inc:end[^>]*-->)?',
    re.DOTALL,
)


def _read_partial(rel: str, depth: int) -> str | None:
    target = (ROOT / rel.lstrip("/")).resolve()
    try:
        target.relative_to(ROOT)
    except ValueError:
        return None
    if not target.is_file():
        return None
    body = target.read_text(encoding="utf-8")
    expanded, _ = render_includes(body, depth + 1)
    return expanded


def render_includes(html: str, depth: int = 0) -> tuple[str, int]:
    """Inline <!--#include file="..." --> directives idempotently. Paths
    resolve from repo root. Recursive with a depth cap for accidental cycles."""
    if depth > 8:
        return html, 0
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        rel = m.group("path")
        body = _read_partial(rel, depth)
        if body is None:
            return m.group(0)
        count += 1
        marker_rel = rel.replace('"', "")
        return (
            f'<!--#include file="{rel}" -->\n'
            f'<!--inc:start "{marker_rel}"-->\n{body}\n<!--inc:end "{marker_rel}"-->'
        )

    return _INCLUDE_RE.sub(repl, html), count


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


# data-cms-html — for elements whose content includes inline HTML (e.g., a
# paragraph with <a> links inside). Same matching shape as data-cms, but
# content uses .*? DOTALL so nested tags are allowed. Pair with non-self-
# nesting tags only (p, li, h1–h4, span) — wrapping a <div data-cms-html>
# around other <div>s will eat the inner divs via greedy backtracking.
_DATA_CMS_HTML_RE = re.compile(
    r'(?P<open><(?P<tag>p|li|h1|h2|h3|h4|span)\b[^>]*?\bdata-cms-html="(?P<path>[^"]+)"[^>]*>)'
    r'(?P<content>.*?)'
    r'(?P<close></(?P=tag)\s*>)',
    re.DOTALL,
)


# cms:blocks page="X" — page-builder marker. The build pipeline finds
# this directive and inlines the rendered blocks from
# _data/pages/<X>.yml, wrapped in idempotent block-rendered marker
# comments so subsequent builds find + replace the previous render.
_BLOCKS_RE = re.compile(
    r'<!--\s*cms:blocks\s+page="(?P<page>[^"]+)"\s*-->'
    r'(?P<rendered>\s*<!--\s*cms:blocks-start[^>]*-->.*?<!--\s*cms:blocks-end[^>]*-->)?',
    re.DOTALL,
)


def render_blocks(html: str, data: dict) -> tuple[str, int]:
    """Find <!--cms:blocks page="X"--> markers and inline the rendered
    page tree underneath, idempotently."""
    # Local import so the build script still works if the module is missing
    # (e.g. on a branch that hasn't pulled the new file yet).
    try:
        from render_blocks import render_page  # type: ignore
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "render_blocks", ROOT / "scripts" / "render_blocks.py"
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(mod)  # type: ignore
        render_page = mod.render_page

    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        page = m.group("page")
        body = render_page(page, data)
        count += 1
        return (
            f'<!--cms:blocks page="{page}"-->\n'
            f'<!--cms:blocks-start "{page}"-->\n{body}\n<!--cms:blocks-end "{page}"-->'
        )

    return _BLOCKS_RE.sub(repl, html), count


def render_data_cms_html(html: str, data: dict) -> tuple[str, int]:
    """Replace inner HTML of elements carrying data-cms-html="path"."""
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

    return _DATA_CMS_HTML_RE.sub(repl, html), count


# List-template expansion. Source HTML has a <template> tag with
# data-cms-item-template="path" — browsers naturally ignore <template>
# contents, so the unrendered file is visually clean. Build time, we
# repeat the template contents once per YAML entry (with {{cms-index}}
# substituted) and wrap the result in cms:rendered marker comments so
# subsequent builds find and replace the previous render idempotently.

_TEMPLATE_WITH_RENDERED_RE = re.compile(
    r'(?P<template><template\b[^>]*\bdata-cms-item-template="(?P<path>[A-Za-z0-9_.]+)"[^>]*>'
    r'(?P<tmpl>.*?)</template>)'
    r'(?P<existing>\s*<!--\s*cms:rendered\s*-->.*?<!--\s*/cms:rendered\s*-->)?',
    re.DOTALL,
)

# <img data-cms-image="path"> binds the src attribute to a YAML value.
# data-cms (text content) doesn't work on void <img> elements.
_DATA_CMS_IMAGE_RE = re.compile(
    r'<img\b(?P<attrs>[^>]*?\bdata-cms-image="(?P<path>[^"]+)"[^>]*?)\s*/?>',
    re.IGNORECASE,
)
_SRC_ATTR_RE = re.compile(r'\bsrc="[^"]*"')


def render_data_cms_image(html: str, data: dict) -> tuple[str, int]:
    """Replace src attribute of <img data-cms-image="path"> with the
    resolved YAML value. Inserts src=… if the tag had none."""
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        val = resolve(m.group("path"), data)
        if val is None:
            return m.group(0)
        new_src = str(val)
        attrs = m.group("attrs")
        if _SRC_ATTR_RE.search(attrs):
            new_attrs = _SRC_ATTR_RE.sub(f'src="{new_src}"', attrs, count=1)
        else:
            new_attrs = f' src="{new_src}"' + attrs
        count += 1
        return "<img" + new_attrs + ">"

    return _DATA_CMS_IMAGE_RE.sub(repl, html), count


def render_lists(html: str, data: dict) -> tuple[str, int]:
    """Expand <template data-cms-item-template="path"> blocks: repeat the
    template content once per YAML entry, substituting {{cms-index}}, then
    wrap the rendered items in <!-- cms:rendered -->...<!-- /cms:rendered -->
    so the next build can find + replace the block idempotently."""
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        path = m.group("path")
        template_block = m.group("template")
        template_body = m.group("tmpl")
        the_list = resolve(path, data)
        if not isinstance(the_list, list):
            return m.group(0)
        rendered = "".join(
            template_body.replace("{{cms-index}}", str(i))
            for i in range(len(the_list))
        )
        count += 1
        return template_block + "<!-- cms:rendered -->" + rendered + "<!-- /cms:rendered -->"

    return _TEMPLATE_WITH_RENDERED_RE.sub(repl, html), count


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


def _page(prefix: str, *, title: str, desc: str, canonical: str, og_type: str,
          body_html: str) -> str:
    # Header / footer are emitted as include directives so they share a single
    # source of truth with every other page. render_includes() (called below)
    # inlines them before the file is written. The shared header detects the
    # active nav link at runtime from location.pathname.
    raw = f'''<!DOCTYPE html>
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

  <!--#include file="_includes/header.html" -->

{body_html}

  <!--#include file="_includes/footer.html" -->

  <script src="{prefix}js/main.js"></script>
  <script src="{prefix}js/dynamic.js"></script>
</body>
</html>
'''
    expanded, _ = render_includes(raw)
    return expanded


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
                 canonical=f'blog/{p["slug"]}/', og_type="article",
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
                 canonical="blog/", og_type="website", body_html=body)


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
        # Inline partials FIRST so the rest of the passes see the full HTML.
        rendered, n_inc = render_includes(original)
        # Expand <!--cms:blocks page="X"--> markers next — the rendered
        # block HTML carries data-cms attributes that subsequent passes fill in.
        rendered, n_blocks = render_blocks(rendered, data)
        # Then expand list templates — they create the per-item DOM that
        # data-cms substitution then fills in.
        rendered, n_list = render_lists(rendered, data)
        rendered, n_placeholder = render_placeholders(rendered, data)
        rendered, n_cms = render_data_cms(rendered, data)
        rendered, n_html = render_data_cms_html(rendered, data)
        rendered, n_img = render_data_cms_image(rendered, data)
        if rendered != original:
            target.write_text(rendered, encoding="utf-8")
            print(f"  {target.relative_to(ROOT)}: {n_cms} data-cms + {n_html} html + "
                  f"{n_img} img + {n_placeholder} placeholder + {n_list} list + "
                  f"{n_inc} include + {n_blocks} blocks")
            total += n_cms + n_html + n_placeholder + n_list + n_img + n_inc + n_blocks
        else:
            print(f"  {target.relative_to(ROOT)}: no changes")
    print(f"Total: {total} substitution(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
