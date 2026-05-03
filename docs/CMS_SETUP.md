# CMS setup — technical handoff

This documents how the volunteer admin panel at `theriverag.church/admin/` is wired up. Read this if you need to add a new editable field, deploy the OAuth proxy, or troubleshoot.

## Architecture

```
Volunteer browser
       │
       ▼
theriverag.church/admin/  ── loads Decap CMS (UI is just static JS)
       │
       │  click "Login with GitHub"
       ▼
decap-oauth.theriverag.workers.dev  ── tiny OAuth proxy on Cloudflare Workers
       │                                (because GitHub OAuth requires a server-side
       │                                 step that static Pages cannot do)
       ▼
github.com/login/oauth/authorize
       │
       │  user grants access
       ▼
Cloudflare Worker exchanges code for token, hands it back to Decap
       │
       ▼
Decap CMS calls GitHub API directly  ── reads/writes _data/*.yml files,
                                         creates Pull Requests for the
                                         editorial workflow
       │
       ▼
GitHub Action `build-content.yml` runs on push to main:
  - reads _data/*.yml
  - substitutes {{site.foo}} placeholders in HTML pages
  - commits the rendered HTML back to main with [skip ci]
       │
       ▼
GitHub Pages serves the updated HTML
```

## Files in this repo

| Path | Purpose |
|---|---|
| `admin/index.html` | Loads Decap CMS bundle |
| `admin/config.yml` | Tells Decap where to read/write content, what the form fields are |
| `_data/*.yml` | The actual editable content (site-wide settings, services, leadership, etc.) |
| `content/blog/` | Volunteer-authored blog posts (Markdown files Decap creates) |
| `scripts/build_pages.py` | Substitutes `{{path.to.field}}` placeholders in HTML from `_data` files |
| `.github/workflows/build-content.yml` | Runs `build_pages.py` on every push to `_data/` |
| `docs/VOLUNTEER_GUIDE.md` | What volunteers see / can do |

## Step 1 — Deploy the OAuth proxy (one-time setup)

Decap needs an OAuth gateway because static sites can't safely hold GitHub client secrets.

### Create a GitHub OAuth app

1. Go to **https://github.com/settings/developers** → OAuth Apps → New OAuth App.
2. Fill in:
   - **Application name:** The River Church CMS
   - **Homepage URL:** `https://theriverag.church`
   - **Authorization callback URL:** `https://decap-oauth.theriverag.workers.dev/callback`
3. After creating, note the **Client ID** and generate a **Client Secret**.

### Deploy the Cloudflare Worker

1. Sign in to **Cloudflare** with the account that holds `theriverag.church`.
2. Workers & Pages → Create → Worker.
3. Name it `decap-oauth`.
4. Replace the default code with the script from
   **https://github.com/sterlingwes/decap-proxy** (small, audited, ~150 lines).
5. Add environment variables in the Worker's Settings → Variables:
   - `OAUTH_CLIENT_ID` = the GitHub Client ID
   - `OAUTH_CLIENT_SECRET` = the GitHub Client Secret (encrypted)
6. Add a Custom Domain → `decap-oauth.theriverag.church` (or use the default `*.workers.dev` URL).
7. Test by visiting `https://decap-oauth.theriverag.church/auth` — should redirect to GitHub.

### Update `admin/config.yml`

Edit the `base_url` line to point at your Worker:

```yaml
backend:
  name: github
  repo: densanon-devs/theriverag-church
  branch: main
  base_url: https://decap-oauth.theriverag.church  # or the workers.dev URL
  auth_endpoint: auth
```

Commit and push. Volunteers can now log in.

## Step 2 — Add a volunteer to the admin panel

1. They create a free GitHub account at **github.com/signup**.
2. Send Jordan their username.
3. Repo → Settings → Collaborators → Add people → paste username → role: **Write** (sufficient for editorial workflow; **Admin** if they should also approve drafts).
4. They accept the invitation email.
5. Done — they can log in at theriverag.church/admin/.

## Step 3 — Add a new editable field

Say someone wants to add a new field, e.g. a "Quote of the Week" on the home page.

1. **Add the field to `_data/site.yml`:**

   ```yaml
   quote_of_the_week: "Be still and know that I am God."
   ```

2. **Add the form field in `admin/config.yml`** under the appropriate collection:

   ```yaml
   - { label: "Quote of the Week", name: quote_of_the_week, widget: string }
   ```

3. **Add a placeholder in the HTML** where the value should render:

   ```html
   <p class="quote">{{site.quote_of_the_week}}</p>
   ```

4. **Push.** The build action runs, substitutes the placeholder, and the page updates.

## Step 4 — Connect a custom domain (optional)

If you want `cms.theriverag.church` instead of `theriverag.church/admin/`:

1. Cloudflare DNS → add a CNAME `cms` → `densanon-devs.github.io`.
2. GitHub repo → Settings → Pages → no custom domain change needed; it serves the `/admin/` directory at the same domain.
3. Or deploy `admin/` as a separate Pages site under `cms.theriverag.church` (more isolation).

## Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| "Failed to load config.yml" | Spelling or YAML syntax error in `admin/config.yml` | Lint with `yamllint admin/config.yml` |
| Login button does nothing | OAuth proxy not deployed or `base_url` wrong | Check Worker logs in Cloudflare dashboard |
| Saving doesn't update the live site | Build Action failed | Check the Actions tab on GitHub for error |
| Volunteer can't log in despite invite | They haven't accepted the email invitation yet | Resend invitation from repo settings |
| Image uploads fail | Repo is over 1 GB | Move large media to Drive; only thumbnails in repo |

## Cost

| Service | Cost |
|---|---|
| Decap CMS | $0 (open source, self-hosted in our repo) |
| GitHub Pages hosting | $0 |
| Cloudflare Worker for OAuth | $0 (free tier — 100k requests/day) |
| GitHub Actions (build runs) | $0 (free for public repos; free 2000 min/mo for private) |
| **Total** | **$0/mo** |

## Migration path forward

The current implementation is the minimum viable version. Future improvements (in order of value):

1. **Wire more editable fields** — currently only Site Settings, Services, Leadership, and Galleries are pulled into the data layer. The About page beliefs, Sermons page intro text, etc. could move to `_data/` too.
2. **Convert HTML pages to fuller templates** (Eleventy / Astro) so volunteers can add entire new pages, not just edit existing ones.
3. **Custom roles** — restrict certain volunteers to only specific collections (e.g. youth ministry leader can edit only youth-related content).
4. **Image optimization on upload** — Decap can call a Cloudflare Image Resizing endpoint on save to auto-compress photos.
