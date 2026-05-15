# Decap OAuth Worker

A ~80-line Cloudflare Worker that bridges Decap CMS ↔ GitHub OAuth. See
`index.js` for the full code (well-commented).

**Why:** Decap runs in the browser at `theriverag.church/admin/` and needs a
GitHub access token to read/write the repo. The OAuth dance requires a
client secret that can't safely live in browser JS, so a tiny server-side
proxy handles the secret-bearing leg.

**What lives where:**
- Code: this directory (`oauth-worker/index.js`)
- Deployed at: `https://decap-oauth.<your-cloudflare-account>.workers.dev`
  (or a custom domain like `decap-oauth.theriverag.church`)
- Referenced from: `admin/config.yml`'s `backend.base_url`

**Deployment:** dashboard-only — no `wrangler` CLI needed. Step-by-step
instructions are in `docs/CMS_SETUP.md`.
