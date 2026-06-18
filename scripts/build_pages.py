"""Build the static HTML pages.

Thin wrapper over `densanon.core.site_builder` — the generic
visual-page-builder engine that powers the admin. This script:

  1. Wires up the church-specific block types via `church_blocks`
     (which registers onto densanon's shared block registry on import).
  2. Renders content/blog/*.md → /blog/<slug>/index.html via the
     church-only `_render_blog` helper (sermon-notes pages aren't
     block-tree-driven yet — they're plain article pages).
  3. Calls `build_site()` to run the full pipeline (includes →
     blocks render → list templates → placeholders → data-cms text →
     data-cms-html → data-cms-image → lightbox inject → code
     injection → SEO meta + sitemap).

Run locally:

    pip install pyyaml
    PYTHONIOENCODING=utf-8 python scripts/build_pages.py
"""
from __future__ import annotations

import html as _html
import re
import sys
from datetime import date as _date
from pathlib import Path

# Make sibling densanon-core importable without an explicit pip install.
# In CI / production the package is installed normally.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DENSANON_CORE = _REPO_ROOT.parent / "densanon-core"
if _DENSANON_CORE.is_dir() and str(_DENSANON_CORE) not in sys.path:
    sys.path.insert(0, str(_DENSANON_CORE))

try:
    import yaml
except ImportError:
    print("Install pyyaml: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# The rendering engine lives in the sibling densanon-core repo, which is
# present on the publish box (the admin "Publish to site" runs this script
# there) but NOT on the GitHub Actions runner. Pages are rendered + committed
# from the box, so on the runner this build has nothing to do — skip cleanly
# instead of crashing. (Before this guard, every push failed the "Build
# content from _data" workflow with `No module named 'densanon'`, which is
# what made site edits appear to "never publish": the push landed but the
# render that turns _data edits into HTML never ran.)
try:
    from densanon.core.site_builder import default_blocks  # noqa: F401 — registers core block library
    from densanon.core.site_builder.data_loader import load_site_data
    from densanon.core.site_builder.pipeline import BuildContext, build_page, build_site

    # Side-effect import: registers church-specific block types onto
    # densanon's default_registry. MUST come after default_blocks so any
    # overrides we apply land on top.
    import church_blocks  # noqa: F401
except ModuleNotFoundError as exc:
    print(f"[build_pages] rendering engine unavailable ({exc}); "
          f"pages are built + committed on the publish box, nothing to do here. "
          f"Skipping.", file=sys.stderr)
    sys.exit(0)


ROOT = _REPO_ROOT
BLOG_SRC = ROOT / "content" / "blog"
BLOG_OUT = ROOT / "blog"
BASE_URL = "https://theriverag.church"


_ESC = _html.escape
_MONTHS = ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]


# ─── Blog rendering (church-specific, not block-tree-driven) ───────────


def _human_date(iso: str) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-")[:3])
        return f"{_MONTHS[m]} {d}, {y}"
    except Exception:
        return iso or ""


def _parse_post(md_path: Path) -> dict | None:
    """Parse a content/blog/*.md file: YAML frontmatter, then HTML body."""
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
    slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-") or \
           re.sub(r"[^a-z0-9-]+", "-", md_path.stem.lower()).strip("-") or "post"
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


_YT_ID_RE = re.compile(r"(?:v=|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})")


def _youtube_thumb(video_id: str) -> str:
    """maxresdefault is 1280x720 (matches FB / Twitter's 1.91:1 preferred
    ratio) and exists for any video uploaded after ~2012. If it's
    missing, YouTube serves the fallback hqdefault transparently."""
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"


def _post_og_image(p: dict) -> str:
    """Pick the best social-share image for a sermon-recap post:
    sermon_id → YouTube thumb (already at video resolution),
    else parse youtube_url for the id, else site default."""
    vid = (p.get("sermon_id") or "").strip()
    if not vid:
        m = _YT_ID_RE.search(p.get("youtube_url") or "")
        if m:
            vid = m.group(1)
    if vid:
        return _youtube_thumb(vid)
    return f"{BASE_URL}/site/images/og-cover.png"


def _blog_page_shell(prefix: str, *, title: str, desc: str,
                     canonical: str, og_type: str, body_html: str,
                     article_schema: dict | None = None,
                     og_image: str | None = None) -> str:
    """Standard blog-page wrapper. Uses the shared header/footer partials
    so blog pages auto-pick up nav + footer changes from the site_builder
    pipeline. The SEO meta tags (title/description/og:*/twitter:*/
    canonical) plus the BlogPosting JSON-LD schema all live inside the
    cms:seo marker block — same convention as the rest of the site, so
    apply_seo() doesn't see two copies."""
    import json as _json
    if og_image is None:
        og_image = f"{BASE_URL}/site/images/og-cover.png"
    schema_json = (
        f'\n  <script type="application/ld+json">{_json.dumps(article_schema, indent=2, ensure_ascii=False)}</script>'
        if article_schema else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/x-icon" href="{prefix}site/images/favicon.ico">
  <link rel="apple-touch-icon" href="{prefix}site/images/logo.png">
  <meta name="robots" content="index, follow">
  <meta name="theme-color" content="#cfa861">
  <link rel="alternate" type="application/rss+xml" title="The River Church — Sermons Podcast" href="{BASE_URL}/feed.xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Oswald:wght@400;600;700&family=Abel&display=swap">
  <link rel="stylesheet" href="{prefix}css/styles.css">
  <link rel="stylesheet" href="{prefix}css/blog.css">
  <!--cms:head-code--><!--/cms:head-code-->
  <!--cms:seo-->
  <title>{_ESC(title)}</title>
  <meta name="description" content="{_ESC(desc)}">
  <meta property="og:title" content="{_ESC(title)}">
  <meta property="og:description" content="{_ESC(desc)}">
  <meta property="og:url" content="{BASE_URL}/{canonical}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:image" content="{og_image}">
  <meta property="og:site_name" content="The River Church">
  <meta property="og:locale" content="en_US">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{_ESC(title)}">
  <meta name="twitter:description" content="{_ESC(desc)}">
  <meta name="twitter:image" content="{og_image}">
  <link rel="canonical" href="{BASE_URL}/{canonical}">{schema_json}
  <!--/cms:seo-->
</head>
<body>

  <!--#include file="_includes/header.html" -->

{body_html}

  <!--#include file="_includes/footer.html" -->

  <script src="{prefix}js/main.js"></script>
  <script src="{prefix}js/dynamic.js"></script>
  <script src="{prefix}js/blog-reveal.js" defer></script>
  <!--cms:body-code--><!--/cms:body-code-->
</body>
</html>
"""


def _render_post_page(p: dict) -> str:
    prefix = "../../"
    cta = ""
    if p["youtube_url"]:
        cta = (f'<div class="blog-cta">'
               f'<a href="{_ESC(p["youtube_url"])}" target="_blank" rel="noopener" class="btn">Watch on YouTube</a>'
               f'<a href="{prefix}#visit" class="btn btn-outline">Plan a visit</a>'
               f'</div>')
    desc = p["summary"] or f'{p["title"]} — sermon recap from The River Church, Post Falls, Idaho.'
    og_img = _post_og_image(p)
    # Cinematic hero: the sermon's title + date over the message thumbnail, with
    # a dark legibility veil and a bottom gradient that fades into the white page
    # (mirrors the reference Squarespace sermon page). The thumbnail is passed as
    # a CSS custom property so the styling lives entirely in blog.css.
    hero = f'''  <header class="sermon-hero" style="--hero-img:url('{_ESC(og_img)}')">
    <div class="sermon-hero__inner container">
      <p class="blog-back"><a href="{prefix}blog/">&larr; All sermon notes</a></p>
      <p class="blog-date">{_ESC(p["date_human"])}</p>
      <h1>{_ESC(p["title"])}</h1>
    </div>
  </header>'''
    body = f'''{hero}
  <main class="blog-page">
    <article class="blog-post container">
{p["body"]}
      <hr class="blog-rule">
      {cta}
    </article>
  </main>'''
    return _blog_page_shell(
        prefix,
        title=f'{p["title"]} — The River Church',
        desc=desc,
        canonical=f'blog/{p["slug"]}/',
        og_type="article",
        body_html=body,
        og_image=og_img,
        article_schema={
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": p["title"],
            "datePublished": p["date_iso"],
            "dateModified": p["date_iso"],
            "description": desc,
            "url": f"{BASE_URL}/blog/{p['slug']}/",
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": f"{BASE_URL}/blog/{p['slug']}/",
            },
            "image": og_img,
            "author": {
                "@type": "Organization",
                "name": "The River Church",
                "url": BASE_URL,
            },
            "publisher": {
                "@type": "Organization",
                "name": "The River Church",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{BASE_URL}/site/images/logo.png",
                },
            },
        },
    )


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
    return _blog_page_shell(
        prefix,
        title="Sermon Notes — The River Church",
        desc="Weekly sermon recaps from The River Church in Post Falls, Idaho — read the message and watch it here.",
        canonical="blog/",
        og_type="website",
        body_html=body,
    )


def build_blog(ctx: "BuildContext | None" = None) -> int:
    """Render content/blog/*.md into /blog/<slug>/index.html + /blog/index.html.

    Only writes a file when its rendered contents would differ from what's
    on disk — keeps the build idempotent so repeated runs don't churn git.
    When `ctx` is supplied, runs the full pipeline on each rendered page
    before writing so the disk version matches what build_site() would
    produce later (idempotent across the build_blog → build_site flow).
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

    def _bake(raw: str) -> str:
        """Run the full pipeline on the rendered HTML if a context is
        available, so the on-disk version matches what build_site() would
        produce — keeps build_blog → build_site idempotent."""
        return build_page(raw, ctx) if ctx is not None else raw

    written = 0
    for p in posts:
        out_dir = BLOG_OUT / p["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "index.html"
        new_html = _bake(_render_post_page(p))
        if not target.is_file() or target.read_text(encoding="utf-8") != new_html:
            target.write_text(new_html, encoding="utf-8")
            written += 1
    blog_index = BLOG_OUT / "index.html"
    new_index = _bake(_render_blog_index(posts))
    if not blog_index.is_file() or blog_index.read_text(encoding="utf-8") != new_index:
        blog_index.write_text(new_index, encoding="utf-8")
        written += 1
    print(f"  blog: {len(posts)} post(s) -> {written} page(s) updated")
    return written


# ─── main ──────────────────────────────────────────────────────────────


def _append_blog_to_sitemap() -> int:
    """Add `/blog/` index + every `/blog/<slug>/` post to sitemap.xml.

    The densanon-core write_sitemap_xml only sees `data['pages']`, which
    has `blog.yml > meta.no_html: true` (so /blog/ stays OUT) and no
    entry per post. This pass reopens the sitemap, drops any entries
    we'd duplicate, and adds one URL per .md file under content/blog/
    plus the index. Idempotent — collapses on repeated builds."""
    import xml.etree.ElementTree as ET
    from datetime import date as _d
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.is_file():
        return 0

    posts: list[dict] = []
    if BLOG_SRC.exists():
        for md in sorted(BLOG_SRC.glob("*.md")):
            p = _parse_post(md)
            if p:
                posts.append(p)

    today = _d.today().isoformat()
    blog_urls = [{"loc": f"{BASE_URL}/blog/", "lastmod": today}]
    for p in posts:
        blog_urls.append({
            "loc": f"{BASE_URL}/blog/{p['slug']}/",
            "lastmod": p["date_iso"] or today,
        })

    # Parse, deduplicate, append.
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    ET.register_namespace("", ns["sm"])
    tree = ET.parse(sitemap)
    root = tree.getroot()
    existing = {url.find("sm:loc", ns).text for url in root.findall("sm:url", ns)
                if url.find("sm:loc", ns) is not None}
    added = 0
    for entry in blog_urls:
        if entry["loc"] in existing:
            continue
        u = ET.SubElement(root, f'{{{ns["sm"]}}}url')
        ET.SubElement(u, f'{{{ns["sm"]}}}loc').text = entry["loc"]
        ET.SubElement(u, f'{{{ns["sm"]}}}lastmod').text = entry["lastmod"]
        added += 1
    if added:
        # Pretty-print to match the rest of the file's style.
        ET.indent(tree, space="  ")
        with sitemap.open("wb") as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
    return added


def main() -> int:
    data = load_site_data(ROOT)
    if not data:
        print("No _data/*.yml files found; skipped substitution.")
        build_blog()
        return 0

    print(f"Loaded data from {len(data)} file(s): {sorted(data.keys())}")
    ctx = BuildContext(repo=ROOT, data=data, base_url=BASE_URL)
    # build_blog FIRST with the build context so it bakes the full pipeline
    # into each blog page, keeping the subsequent build_site() a no-op on
    # repeat runs.
    build_blog(ctx)
    result = build_site(ctx)
    if result.nav_refreshed:
        print("  _includes/header.html: nav refreshed from pages/")
    for path, changed in result.page_diffs:
        flag = "changed" if changed else "no changes"
        print(f"  {path}: {flag}")
    print(f"Total: {result.pages_changed}/{result.pages_built} page(s) updated")
    n = _append_blog_to_sitemap()
    if n:
        print(f"  sitemap.xml: +{n} blog URL(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
