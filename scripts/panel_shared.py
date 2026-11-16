"""The few lines of page-building logic the admin panel and a church's site
build must agree on. This file is the one place they are written.

church-ops uses it directly (the preview). A site whose build wants the same
behaviour keeps a copy at ``scripts/panel_shared.py`` and imports it from
its build script; church-ops rewrites that copy whenever it differs
(`site_design.sync_site_helpers`), so the two can't drift apart. Plain
Python, standard library only, no imports from church-ops or the site
engine: it has to run inside either.

Edit it here, never in a site repo.
"""
import re

_HOOK_RE = re.compile(r"[a-z][a-z0-9-]{1,40}")
_FIRST_TAG_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>")
_LEADING_SEPARATORS = " |-–—·:"


def title_with_suffix(title, suffix):
    """`title` with the site's suffix, unless the title already says it."""
    title = str(title or "").strip()
    suffix = str(suffix or "")
    core = suffix.lstrip(_LEADING_SEPARATORS + "\t").strip()
    if not title or not core or core.lower() in title.lower():
        return title
    return title + (suffix if suffix[:1] in _LEADING_SEPARATORS else " " + suffix).rstrip()


def apply_head_defaults(data):
    """Site-wide title suffix and default description, from `head:` in
    _data/site.yml, applied to the loaded page data (nothing is written to
    disk). A page with no description gets the default."""
    site = data.get("site") if isinstance(data.get("site"), dict) else {}
    head = site.get("head") if isinstance(site.get("head"), dict) else {}
    suffix = str(head.get("title_suffix") or "")
    desc = str(head.get("description") or "").strip()
    if not suffix.strip() and not desc:
        return data
    for page in (data.get("pages") or {}).values():
        meta = page.get("meta") if isinstance(page, dict) else None
        if not isinstance(meta, dict):
            continue
        if suffix.strip() and meta.get("title"):
            meta["title"] = title_with_suffix(meta["title"], suffix)
        if desc and not str(meta.get("description") or "").strip():
            meta["description"] = desc
    return data


def add_hook(html, block):
    """A section with `hook: name` in its data is drawn with the class
    `sec-name`: a handle that stays put when sections are reordered, for the
    site's own CSS to hold on to."""
    hook = str(block.get("hook") or "") if isinstance(block, dict) else ""
    if not _HOOK_RE.fullmatch(hook):
        return html
    m = _FIRST_TAG_RE.search(html)
    if not m:
        return html
    attrs = m.group(2)
    if re.search(r'\bclass="', attrs):
        attrs = re.sub(r'\bclass="', 'class="sec-%s ' % hook, attrs, count=1)
    else:
        attrs = ' class="sec-%s"' % hook + attrs
    return html[:m.start()] + "<%s%s>" % (m.group(1), attrs) + html[m.end():]
