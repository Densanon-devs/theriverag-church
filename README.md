# theriverag.church

Static replacement for The River Church's Squarespace site. Same structure, same pages, same external integrations — minus the $276/yr.

## Structure mirrors current Squarespace site

| Page | File | Notes |
|---|---|---|
| Home | `index.html` | Hero, service times, values, livestream CTA, gallery, 3-card section, calendar embed, Get Connected form |
| Sermons | `sermons.html` | Spotify / Apple / YouTube platform cards + sermon list (20 episodes) |
| About | `about.html` | Pastors bio, kids, youth, beliefs (15 cards), visit CTA |
| Give | external | Direct link to `theriverag.churchcenter.com/giving` (Planning Center) |
| Blog / Sermon Notes | `blog/index.html` + `blog/<slug>/index.html` | **Generated** — see below |

## Blog (Sermon Notes) — auto-generated

`/blog/` is built from `content/blog/*.md` files. Those `.md` files are written
and committed by the **church-ops** pipeline (`densanon-devs/church-ops`, runs on
Jordan's box) when a sermon is processed: YAML frontmatter (`title` / `date` /
`slug` / `summary` / `youtube_url` / `sermon_id`) + an HTML body (a responsive
YouTube embed + the post HTML). The body is reviewed in the church-ops admin
panel before it's published here.

`scripts/build_pages.py` (`build_blog()`) renders those into:
- `blog/<slug>/index.html` — one page per sermon recap (wrapped in the site shell, with the video embedded)
- `blog/index.html` — the index, newest first

The `.github/workflows/build-content.yml` GitHub Action runs `build_pages.py`
on any push that touches `content/blog/**`, `_data/**`, `css/blog.css`, or the
script itself, and commits the generated HTML back. So: church-ops pushes a
`.md` → the Action rebuilds → Pages serves it. Nothing to do by hand.

Styling for blog pages lives in `css/blog.css` (loaded on top of `styles.css`,
only on `/blog/` pages). The "Blog" nav link is in the header of `index.html`,
`about/index.html`, `podcasts/index.html`, and every generated blog page.

Run the build locally: `pip install pyyaml && python scripts/build_pages.py`

## What needs to be filled in before launch

### 1. Images — drop into `site/images/`
See `site/images/README.md` for the full list. Source from the Google Drive Riley left at:
https://drive.google.com/drive/folders/1N1MkmaoU5_sNYqC1onBU30d6Jm7qC3wo

### 2. Embed URLs — confirm or replace
- **Calendar** (`index.html`): currently `https://theriverag.churchcenter.com/calendar` — confirm this is the right Planning Center calendar URL.
- **Get Connected form** (`index.html`): currently `https://theriverag.churchcenter.com/people/forms/get-connected` — replace with the actual Planning Center form embed URL (Planning Center → Forms → Embed code).
- **Giving link** (every page nav): `https://theriverag.churchcenter.com/giving` — confirm this is the correct ChurchCenter giving subdomain.

### 3. Social links — confirm handles
- Facebook: `https://www.facebook.com/theriverag` — verify
- Instagram: `https://www.instagram.com/theriverag.church` — verify
- YouTube: `https://www.youtube.com/@theriverag.church` — confirmed working

### 4. Beliefs text
The 15 belief cards on `about.html` use standard Assemblies of God Statement of Fundamental Truths summaries. Replace with the church's exact wording if they have their own.

## Hosting

This is a static HTML site with zero build step. Drop it on:
- **GitHub Pages** (free) — `CNAME` file is already set to `theriverag.church`. Push to `densanon-devs/theriverag-church`, enable Pages, point the domain DNS at GitHub.
- Or any static host (Netlify, Cloudflare Pages, S3+CloudFront).

## DNS cutover

When ready to leave Squarespace:
1. Confirm new site works at a preview URL.
2. Point `theriverag.church` DNS at GitHub Pages (A records to GitHub IPs + CNAME for www).
3. Cancel Squarespace site renewal (Nov 16) but **keep the domain registered** wherever it currently lives ($50/yr Oct 31 — confirm registrar).
4. Squarespace plan can be downgraded/cancelled once DNS is propagated.

## Local preview

```sh
cd D:/LLCWork/theriverag-church
python -m http.server 8000
# open http://localhost:8000
```
