# Blog templates

These four files are the **single source of truth** for how every sermon-note
(blog) page looks. Each blog post is just data — `content/blog/<slug>.md` holds
only the *specific* parts (title, date, YouTube URL, body). At build time
`scripts/build_pages.py` injects those parts into these shared templates, so the
chrome, hero, fonts, SEO scaffold, and scripts stay **unified** across all posts.

To restyle *every* blog at once, edit the template here and rebuild — you never
touch the individual posts.

| File | What it is |
|------|------------|
| `blog-shell.html` | The whole page wrapper: `<head>` + SEO scaffold, header/footer includes, the `<body>`, and the scripts. Shared by both post pages and the index. |
| `blog-post.html` | A single sermon post's content: the cinematic hero (title/date over the thumbnail) + the article body + CTA. |
| `blog-index.html` | The `/blog/` listing page (heading + the list of cards). |
| `blog-card.html` | One card in that list (repeated per post). |

## Placeholders

Values are injected with simple `{{name}}` substitution (no template engine):

- **shell** — `{{prefix}}`, `{{base_url}}`, `{{seo}}` (the assembled `<title>`/meta/JSON-LD block), `{{content}}`
- **post** — `{{prefix}}`, `{{hero_image}}`, `{{date}}`, `{{title}}`, `{{body}}`, `{{cta}}`
- **card** — `{{href}}`, `{{title}}`, `{{date}}`, `{{summary}}`

## Rebuild

```
python -X utf8 scripts/build_pages.py
```

(The admin panel's **Publish to site** already runs this on the box, so new
sermons from the church-ops pipeline pick up the current templates automatically
— no manual step.)
