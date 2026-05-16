"""Block renderer for the visual page builder.

Each top-level section on a page is a "block" with a `type` and
type-specific fields, stored as an entry in `_data/pages/<name>.yml`
under the `blocks:` key. This module:

  - Defines one render_<type> function per supported block type.
  - Each renderer takes (block_dict, block_index) and returns HTML.
  - render_page(page_name, data) reads the page's blocks list and
    returns the assembled HTML body.

Every rendered element is annotated with:
  - data-cms="pages.<page>.blocks.<i>.<field>"  on editable text
  - data-cms-image="pages.<page>.blocks.<i>.<field>"  on images
  - data-cms-html="pages.<page>.blocks.<i>.<field>"  on inline-HTML text
  - data-cms-block="<i>"  on the block wrapper itself (drag handle target)
  - data-cms-blocks-page="<page>"  on the page-level container

The build pipeline (build_pages.py) substitutes per-element values via
the standard data-cms passes, so YAML edits land in the HTML on every
build without re-running the block renderer.
"""
from __future__ import annotations

import html as _html
from typing import Any


_ESC = _html.escape


def _path(page: str, idx: int, *parts: str) -> str:
    """Build a YAML resolver path: pages.<page>.blocks.<i>[.field...]"""
    base = f"pages.{page}.blocks.{idx}"
    if parts:
        return base + "." + ".".join(parts)
    return base


# ─── Block renderers ────────────────────────────────────────────────────

def render_hero(block: dict, idx: int, page: str) -> str:
    heading = _ESC(str(block.get("heading", "YOU BELONG HERE!")))
    tagline = _ESC(str(block.get("tagline", "")))
    p = _path(page, idx, "heading")
    pt = _path(page, idx, "tagline")
    return (
        f'<section class="hero hero-home wave-bottom" data-cms-block="{idx}" data-cms-block-type="hero">\n'
        f'  <div class="container">\n'
        f'    <div class="hero-frame">\n'
        f'      <div class="hero-content">\n'
        f'        <h1 data-cms="{p}">{heading}</h1>\n'
        f'        <p data-cms="{pt}">{tagline}</p>\n'
        f'      </div>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'</section>'
    )


def render_wave_divider(block: dict, idx: int, page: str) -> str:
    return (
        f'<div class="wave-divider" aria-hidden="true" data-cms-block="{idx}" data-cms-block-type="wave_divider">\n'
        f'  <svg viewBox="0 0 1440 48" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">\n'
        f'    <path d="M0,24 C240,48 480,0 720,24 C960,48 1200,0 1440,24" fill="none" stroke="#cfa861" stroke-width="2"/>\n'
        f'  </svg>\n'
        f'</div>'
    )


def render_service_times(block: dict, idx: int, page: str) -> str:
    live_heading = _ESC(str(block.get("live_heading", "Join us live on YouTube!")))
    embed_url = _ESC(str(block.get("live_embed_url", "")))
    cards = block.get("cards", []) or []
    inline_photo = str(block.get("inline_photo", ""))
    values_lines = block.get("values_lines", []) or []

    cards_html_parts = []
    for ci, card in enumerate(cards):
        heading = _ESC(str(card.get("heading", "")))
        description = _ESC(str(card.get("description", "")))
        when = _ESC(str(card.get("when", "")))
        ph = _path(page, idx, "cards", str(ci), "heading")
        pd = _path(page, idx, "cards", str(ci), "description")
        pw = _path(page, idx, "cards", str(ci), "when")
        pi = _path(page, idx, "cards", str(ci))
        cards_html_parts.append(
            f'<details class="accordion-card" data-cms-item="{pi}">\n'
            f'  <summary>\n'
            f'    <h3 data-cms="{ph}">{heading}</h3>\n'
            f'    <span class="accordion-chev" aria-hidden="true"></span>\n'
            f'  </summary>\n'
            f'  <div class="accordion-body">\n'
            f'    <p data-cms="{pd}">{description}</p>\n'
            f'    <span class="when" data-cms="{pw}">{when}</span>\n'
            f'  </div>\n'
            f'</details>'
        )
    cards_html = "\n".join(cards_html_parts)

    values_html = "\n".join(
        f'    <p data-cms="{_path(page, idx, "values_lines", str(li))}">{_ESC(str(line))}</p>'
        for li, line in enumerate(values_lines)
    )

    p_live = _path(page, idx, "live_heading")
    p_photo = _path(page, idx, "inline_photo")
    p_cards = _path(page, idx, "cards")

    return (
        f'<section class="service-block wave-top" aria-label="Service times" data-cms-block="{idx}" data-cms-block-type="service_times">\n'
        f'  <div class="container">\n'
        f'    <div class="service-row">\n'
        f'      <div class="live-card">\n'
        f'        <h2><a href="https://www.youtube.com/@theriverag.church/streams" target="_blank" rel="noopener" data-cms="{p_live}">{live_heading}</a></h2>\n'
        f'        <div class="live-thumb live-thumb-embed">\n'
        f'          <iframe id="home-live-embed" src="{embed_url}" title="Latest sermon — The River Church" frameborder="0" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen loading="lazy"></iframe>\n'
        f'        </div>\n'
        f'      </div>\n'
        f'      <div class="accordion-list" data-cms-list="{p_cards}">\n'
        f'{cards_html}\n'
        f'      </div>\n'
        f'    </div>\n'
        f'    <div class="service-row">\n'
        f'      <div class="service-row__media">\n'
        f'        <div class="rounded-photo">\n'
        f'          <img data-cms-image="{p_photo}" src="{_ESC(inline_photo)}" alt="Photo" loading="lazy" decoding="async" width="800" height="600">\n'
        f'        </div>\n'
        f'      </div>\n'
        f'      <div class="inline-values">\n'
        f'{values_html}\n'
        f'      </div>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'</section>'
    )


def render_gallery_strip(block: dict, idx: int, page: str) -> str:
    photos = block.get("photos", []) or []
    extra_class = " wave-bottom" if block.get("wave_bottom") else ""
    p_photos = _path(page, idx, "photos")
    items = []
    for pi, photo in enumerate(photos):
        src = _ESC(str(photo.get("src", "")))
        img_path = _path(page, idx, "photos", str(pi), "src")
        item_path = _path(page, idx, "photos", str(pi))
        items.append(
            f'  <div class="gallery-item" data-cms-item="{item_path}"><img data-cms-image="{img_path}" src="{src}" alt="Photo" loading="lazy" decoding="async" width="800" height="600"></div>'
        )
    items_html = "\n".join(items)
    return (
        f'<div class="gallery-strip{extra_class}" aria-label="Photo gallery" data-cms-block="{idx}" data-cms-block-type="gallery_strip" data-cms-list="{p_photos}">\n'
        f'{items_html}\n'
        f'</div>'
    )


def render_invitation(block: dict, idx: int, page: str) -> str:
    heading = _ESC(str(block.get("heading", "")))
    paragraphs = block.get("paragraphs", []) or []
    p_h = _path(page, idx, "heading")
    p_list = _path(page, idx, "paragraphs")
    paras = []
    for pi, para in enumerate(paragraphs):
        item_path = _path(page, idx, "paragraphs", str(pi))
        paras.append(
            f'    <p data-cms="{item_path}" data-cms-item="{item_path}">{_ESC(str(para))}</p>'
        )
    paras_html = "\n".join(paras)
    return (
        f'<section class="section-river wave-top" data-cms-block="{idx}" data-cms-block-type="invitation">\n'
        f'  <div class="container">\n'
        f'    <div class="invitation" data-cms-list="{p_list}">\n'
        f'      <h2 data-cms="{p_h}">{heading}</h2>\n'
        f'{paras_html}\n'
        f'    </div>\n'
        f'  </div>\n'
        f'</section>'
    )


def render_three_cards(block: dict, idx: int, page: str) -> str:
    cards = block.get("cards", []) or []
    p_list = _path(page, idx, "cards")
    cards_html_parts = []
    icon_class_map = {
        "default": "three-card-icon",
        "blue": "three-card-icon three-card-icon-blue",
        "gold": "three-card-icon three-card-icon-gold",
    }
    for ci, card in enumerate(cards):
        heading = _ESC(str(card.get("heading", "")))
        image = _ESC(str(card.get("image", "")))
        button_label = _ESC(str(card.get("button_label", "")))
        button_url = _ESC(str(card.get("button_url", "#")))
        icon_style = str(card.get("icon_style", "default"))
        icon_class = icon_class_map.get(icon_style, "three-card-icon")
        button_target = card.get("button_target", "")
        target_attr = ' target="_blank" rel="noopener"' if button_target == "_blank" else ""
        p_h = _path(page, idx, "cards", str(ci), "heading")
        p_img = _path(page, idx, "cards", str(ci), "image")
        p_btn = _path(page, idx, "cards", str(ci), "button_label")
        p_item = _path(page, idx, "cards", str(ci))
        # If the card has a "use_heart_icon" flag, render the heart instead of an image.
        if card.get("use_heart_icon"):
            icon_html = f'<div class="{icon_class}"><span class="give-heart" aria-hidden="true">&hearts;</span></div>'
        else:
            img_contain = ' class="contain"' if icon_style == "blue" else ""
            icon_html = (
                f'<div class="{icon_class}"><img{img_contain} data-cms-image="{p_img}" '
                f'src="{image}" alt="Photo" loading="lazy" decoding="async" width="320" height="320"></div>'
            )
        cards_html_parts.append(
            f'  <div class="three-card" data-cms-item="{p_item}">\n'
            f'    {icon_html}\n'
            f'    <h3 data-cms="{p_h}">{heading}</h3>\n'
            f'    <a href="{button_url}"{target_attr} class="btn btn-primary" data-cms="{p_btn}">{button_label}</a>\n'
            f'  </div>'
        )
    cards_html = "\n".join(cards_html_parts)
    return (
        f'<section class="section section-dark wave-bottom" data-cms-block="{idx}" data-cms-block-type="three_cards">\n'
        f'  <div class="container">\n'
        f'    <div class="three-card-grid" data-cms-list="{p_list}">\n'
        f'{cards_html}\n'
        f'    </div>\n'
        f'  </div>\n'
        f'</section>'
    )


def render_calendar(block: dict, idx: int, page: str) -> str:
    heading = _ESC(str(block.get("heading", "View Our Full Calendar!")))
    embed_src = _ESC(str(block.get("embed_src", "https://theriveragchurch.churchcenter.com/assets/calendar_embed.js")))
    calendar_url = _ESC(str(block.get("calendar_url", "https://theriveragchurch.churchcenter.com/calendar")))
    p_h = _path(page, idx, "heading")
    return (
        f'<section class="section-river wave-top" data-cms-block="{idx}" data-cms-block-type="calendar">\n'
        f'  <div class="container">\n'
        f'    <div class="calendar-callout">\n'
        f'      <a href="{calendar_url}" target="_blank" rel="noopener" style="text-decoration:none;">\n'
        f'        <h2 data-cms="{p_h}">{heading}</h2>\n'
        f'      </a>\n'
        f'    </div>\n'
        f'    <div class="calendar-embed">\n'
        f'      <script src="{embed_src}" data-view="list" data-show-filter="true" data-height="560px"></script>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'</section>'
    )


def render_tagline(block: dict, idx: int, page: str) -> str:
    heading = _ESC(str(block.get("heading", "")))
    theme = str(block.get("theme", "light"))
    cls = "section section-dark" if theme == "dark" else "section section-light"
    p_h = _path(page, idx, "heading")
    return (
        f'<section class="{cls}" data-cms-block="{idx}" data-cms-block-type="tagline">\n'
        f'  <div class="container">\n'
        f'    <div class="tagline">\n'
        f'      <h2 data-cms="{p_h}">{heading}</h2>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'</section>'
    )


def render_rich_text(block: dict, idx: int, page: str) -> str:
    # Free-form HTML block. The whole body is editable as inline HTML.
    body_html = str(block.get("html", ""))
    p_h = _path(page, idx, "html")
    return (
        f'<section class="section section-light" data-cms-block="{idx}" data-cms-block-type="rich_text">\n'
        f'  <div class="container">\n'
        f'    <div data-cms-html="{p_h}">{body_html}</div>\n'
        f'  </div>\n'
        f'</section>'
    )


# Public registry — name → (renderer, label, default block for +Add)
BLOCK_TYPES: dict[str, dict[str, Any]] = {
    "hero": {
        "renderer": render_hero,
        "label": "Hero (big heading + tagline)",
        "default": {"heading": "Welcome!", "tagline": "A short tagline goes here."},
    },
    "wave_divider": {
        "renderer": render_wave_divider,
        "label": "Wave divider (decoration)",
        "default": {},
    },
    "service_times": {
        "renderer": render_service_times,
        "label": "Service times (live video + accordion)",
        "default": {
            "live_heading": "Join us live on YouTube!",
            "live_embed_url": "https://www.youtube.com/embed/gHczC5kLM0A",
            "cards": [
                {"heading": "Sunday Services", "description": "Description goes here.", "when": "Sundays @ 10 AM"},
            ],
            "inline_photo": "/site/images/gallery-01.jpg",
            "values_lines": ["Value line one", "Value line two"],
        },
    },
    "gallery_strip": {
        "renderer": render_gallery_strip,
        "label": "Gallery strip (row of photos)",
        "default": {
            "photos": [{"src": "/site/images/gallery-01.jpg"}],
            "wave_bottom": False,
        },
    },
    "invitation": {
        "renderer": render_invitation,
        "label": "Invitation (heading + paragraph list)",
        "default": {
            "heading": "Are You Curious About Jesus?",
            "paragraphs": ["First paragraph.", "Second paragraph."],
        },
    },
    "three_cards": {
        "renderer": render_three_cards,
        "label": "Three-card section",
        "default": {
            "cards": [
                {"heading": "Card 1", "image": "/site/images/gallery-01.jpg", "button_label": "Learn more", "button_url": "#", "icon_style": "default"},
                {"heading": "Card 2", "image": "/site/images/gallery-02.jpg", "button_label": "Learn more", "button_url": "#", "icon_style": "default"},
                {"heading": "Card 3", "image": "/site/images/gallery-03.jpg", "button_label": "Learn more", "button_url": "#", "icon_style": "default"},
            ],
        },
    },
    "calendar": {
        "renderer": render_calendar,
        "label": "Calendar embed",
        "default": {
            "heading": "View Our Full Calendar!",
            "calendar_url": "https://theriveragchurch.churchcenter.com/calendar",
            "embed_src": "https://theriveragchurch.churchcenter.com/assets/calendar_embed.js",
        },
    },
    "tagline": {
        "renderer": render_tagline,
        "label": "Tagline (single heading)",
        "default": {"heading": "Tagline goes here", "theme": "light"},
    },
    "rich_text": {
        "renderer": render_rich_text,
        "label": "Rich text (free-form HTML)",
        "default": {"html": "<p>Your content here.</p>"},
    },
}


def render_block(block: dict, idx: int, page: str) -> str:
    """Render a single block; unknown types render an inline warning so the
    page still builds (instead of swallowing the error silently)."""
    btype = str(block.get("type", "")).strip()
    spec = BLOCK_TYPES.get(btype)
    if spec is None:
        return (
            f'<section class="section section-light" data-cms-block="{idx}" data-cms-block-type="unknown">'
            f'<div class="container"><p style="color:#a33;">'
            f'Unknown block type: <code>{_ESC(btype)}</code> at index {idx}'
            f'</p></div></section>'
        )
    return spec["renderer"](block, idx, page)


def render_page(page_name: str, data: dict) -> str:
    """Render the full blocks list for a page. Wraps the whole thing in a
    container marked data-cms-blocks-page so the editor can find it for
    drag-reorder + +Add Section."""
    page_data = (data.get("pages") or {}).get(page_name) or {}
    blocks = page_data.get("blocks") or []
    parts = [render_block(b, i, page_name) for i, b in enumerate(blocks)]
    body = "\n\n".join(parts)
    return (
        f'<div class="cms-blocks-page" data-cms-blocks-page="{_ESC(page_name)}">\n'
        f'{body}\n'
        f'</div>'
    )
