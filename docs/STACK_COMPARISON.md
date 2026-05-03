# The River Church — Web & Media Stack Comparison

**Audience:** Steve, Tracey, Caitlyn, Ed, anyone making the cutover decision.
**Purpose:** Help the team choose between staying on Squarespace and moving to a self-owned static site + automation pipeline.
**Author:** Jordan / `media@theriverag.church` team
**Date:** May 2026

---

## Executive summary

The current Squarespace site costs **~$326/yr** ($276 site + $50 domain). It works, but every weekly task — posting a sermon, scheduling social posts, sending a recap email, generating clips — is manual, and Squarespace blocks any kind of automated publishing because it has no public API.

Replacing it with a self-owned static site on GitHub Pages plus a small automation pipeline cuts recurring cost to **~$32/yr** (just the domain on Cloudflare), gives the church real ownership of its content, and unlocks weekly automation that simply isn't possible on Squarespace.

The only real Squarespace strength for our context is the drag-and-drop editor for volunteers. We solve that with **Decap CMS**, a free open-source admin panel that gives volunteers a Squarespace-style editing UI on top of the same static site.

**Recommendation:** migrate. Net savings ~$1,200–3,000/yr depending on which Squarespace add-ons would otherwise be activated, with substantially better automation and zero loss of editing convenience for volunteers.

---

## Cost summary

| Path | Year-1 cost | Year-2 cost | Notes |
|---|---|---|---|
| Stay on Squarespace, do everything manually | $326/yr | $326/yr | Domain + site only. No add-ons. Manual social, manual sermon archive, no automation. |
| Squarespace + Pulpit AI for sermon repurposing | ~$1,030/yr | ~$1,030/yr | $326 Squarespace + ~$700 Pulpit Starter |
| Squarespace + full SaaS pipeline (Pulpit + Buffer + Brevo + Buzzsprout) | ~$1,800/yr | ~$1,800/yr | Each piece is a separate vendor relationship |
| **Self-owned static site + self-built automation** | **~$32/yr** | **~$32/yr** | Domain only. Hosting on GitHub Pages free. Automation runs on GitHub Actions (free) and existing infrastructure. |

A note on the Squarespace cancellation: the church already paid Squarespace through Nov 16, 2026, so cancelling the site portion early forfeits that money. Cancelling at renewal time is cleanest.

---

## Capability comparison

### Website / content publishing

| Capability | Squarespace | Self-built static site |
|---|---|---|
| Edit page content via web UI | ✅ Drag-and-drop editor | ✅ Decap CMS provides equivalent editing UI |
| Auto-publish a sermon archive page each week | ❌ Manual blog post per sermon | ✅ Pipeline writes the page automatically |
| Public API for programmatic publishing | ❌ None | ✅ `git push` is the API |
| Custom domain + free SSL | ✅ | ✅ (Cloudflare + Pages) |
| Mobile responsive | ✅ Auto | ✅ Hand-built CSS, already shipped |
| Versioned history of all changes | ⚠️ Limited | ✅ Full git history forever |
| Site is portable (move to another host later) | ❌ Locked into Squarespace | ✅ Plain files in a git repo |
| Speed | Average — Squarespace ships a lot of JS | Faster — static HTML on a CDN |

### Planning Center (Church Center)

Planning Center sits outside the website and exposes embeds + APIs. It plugs into either path identically.

| Capability | Squarespace | Self-built |
|---|---|---|
| Public calendar embed | ✅ | ✅ Already wired |
| Get Connected form | ✅ | ✅ Already wired |
| Ministry Communications form | ✅ | ✅ Already wired |
| Online giving | ✅ Link out | ✅ Link out |
| Group sign-ups | ✅ | ✅ |
| Programmatic data (e.g. live group counts) | ⚠️ Hack via code block | ✅ Clean — fetched at build time |

### Live streaming (OBS → YouTube → Facebook link post)

| Capability | Squarespace | Self-built |
|---|---|---|
| Embed YouTube live player | ✅ | ✅ |
| Show "We're live now" automatically | ❌ Manual or 3rd-party widget | ✅ Already built — daily check + JS swap |
| Embed VOD recordings | ✅ | ✅ |
| Custom player styling | ❌ Limited | ✅ Full control |

### Sermons & podcast

| Capability | Squarespace | Self-built |
|---|---|---|
| Sermon list page | ✅ Manual entries OR a Squarespace blog | ✅ Auto from YouTube RSS (already built) |
| Per-sermon pages | ✅ Manual blog posts | ✅ Auto-generated from the pipeline |
| Embed Spotify / Apple Podcasts | ✅ Code block | ✅ Already wired |
| Actually host the podcast (RSS feed + MP3 storage) | ❌ Squarespace is not a podcast host. Currently this is on Buzzsprout or similar (~$19/mo external). | ✅ Free — GitHub Releases for MP3, generated `feed.xml` in the repo |
| Auto-clip vertical Reels/Shorts | ❌ | ✅ ffmpeg pipeline (Phase 5) |
| Sermon transcripts on each page | ❌ | ✅ Whisper.cpp output |
| Search the sermon archive ("which sermon talked about Galatians?") | ❌ | ✅ Semantic search (Phase 5) |

### Email & SMS

| Capability | Squarespace | Self-built |
|---|---|---|
| Newsletter signup form | ✅ Built-in or any provider embed | ✅ Same |
| Send email blast to a list | ❌ Squarespace Email ($14/mo extra) | ✅ Google Workspace SMTP via `media@` (free up to 2,000 recipients/day) |
| Drip campaigns / 5-day devotional series | ❌ Add-on or external | ✅ Listmonk self-hosted, or simple Python sender |
| Auto-email when a new sermon drops | ❌ Not native | ✅ Pipeline triggers it |
| SMS blast | ❌ Twilio either way (~$16/mo) | ⚠️ Same — neither path has free SMS |

### Social media management

| Capability | Squarespace | Self-built |
|---|---|---|
| Post to FB / IG / X / LinkedIn / TikTok | ❌ Squarespace doesn't post for you. Manual or Buffer (~$18/mo). | ✅ Direct API calls — each platform's free tier is enough |
| Schedule posts in advance | ❌ Buffer / Hootsuite | ✅ GitHub Actions cron + queue |
| Auto-generate quote graphics from sermons | ❌ Need Canva + manual work | ✅ Playwright + brand-kit HTML template, free |
| Approval-before-post workflow | ❌ Buffer doesn't gate this well | ✅ admin panel does exactly this |

### Analytics

| Capability | Squarespace | Self-built |
|---|---|---|
| Page views, traffic sources | ✅ Built-in dashboard | ✅ Plausible self-hosted (free) or Google Analytics (free) |
| Email open rates | Squarespace Email or Brevo | Listmonk / Brevo |
| YouTube views | ❌ Go to YouTube Studio | ✅ Pull via YouTube Analytics API into a unified Metabase dashboard |
| Sermon-specific engagement (views + listens + blog visits) | ❌ Not unified | ✅ Custom dashboard per sermon |

### Store / e-commerce

| Capability | Squarespace | Self-built |
|---|---|---|
| Sell merch (T-shirts, books) | ✅ Built-in store + checkout | ❌ Would need Stripe Checkout (~$0.30 + 2.9% per order) |
| Recurring giving | ✅ Via ChurchCenter | ✅ Same — both link to ChurchCenter |
| One-time donations | ✅ Via ChurchCenter | ✅ Same |

The merch store is the only real Squarespace advantage here, and only if the church actually wants one. Currently there's no store on the live site.

### Member-only content

| Capability | Squarespace | Self-built |
|---|---|---|
| Gated content with login | ✅ Member Areas ($9–$35/mo extra) | ⚠️ Possible via Cloudflare Access or JWT layer (~1–2 days work). Currently nothing gated. |

### Volunteer-friendly editing

| Capability | Squarespace | Self-built |
|---|---|---|
| Volunteer fixes a typo on the home page | ✅ 30 seconds in the editor | ✅ Decap CMS gives Squarespace-style UI; same 30 seconds |
| Volunteer adds a new sermon | ✅ Manual blog post | ✅ Pipeline auto-publishes — they don't touch anything |
| Volunteer adds an event | ✅ Squarespace events | ✅ Lives in Planning Center — both paths use the same calendar |
| Volunteer swaps the hero photo | ✅ Click and replace | ✅ Decap CMS — click and replace |
| Volunteer schedules a social post | ❌ Not native; Buffer | ✅ Decap CMS UI shows a queue they can edit |

### Backups & portability

| Capability | Squarespace | Self-built |
|---|---|---|
| Site is portable | ❌ Locked into Squarespace | ✅ Just files in a git repo |
| Versioned history | ⚠️ Limited revision history | ✅ Full git history forever |
| Export everything | ❌ XML export limited | ✅ `git clone` |

---

## What we lose by leaving Squarespace

Honest list:

1. **Drag-drop visual editor** — replaced 1:1 by Decap CMS, which gives volunteers the same editing experience.
2. **Built-in store** — only matters if we ever sell merch. Replaceable with Stripe Checkout in a day.
3. **Email Campaigns add-on** — replaceable.
4. **Member Areas** — currently unused.

---

## What we gain

1. **~$1,200–$3,000/yr** in savings depending on which Squarespace add-ons would otherwise be activated.
2. **Real automation** — sermon → 20 content pieces → published across all channels with no human keystrokes. Squarespace cannot do this at all.
3. **Full data ownership** — sermons, transcripts, and a searchable archive are owned by the church forever, not in Squarespace's database.
4. **Custom features that aren't possible on Squarespace:**
   - Sermon search ("Ask the archive a question")
   - Spanish translation
   - Devotional audio podcast (with a custom voice)
   - Auto-generated vertical clips for Reels/Shorts/TikTok
5. **Same domain, same staff workflow** — the cutover is invisible to anyone outside the team.

---

## Decision matrix

| Scenario | Recommended path |
|---|---|
| Church wants to ship today, never touch tech, accepts paying $1,200+/yr in tooling | Squarespace + Pulpit AI |
| Church has engineering capacity (Jordan's team), wants automation, wants ownership | **Self-built** |
| Church wants merch store + member areas + drag-drop editor for many volunteers | Squarespace |
| Church wants the sermon → blog → social → podcast → email pipeline running automatically | **Self-built** (Squarespace literally cannot do this) |

The deciding factor is **who edits the website day-to-day**. Whether that's a tech-savvy admin or a rotating bench of volunteers, the self-built path covers it once Decap CMS is in place.

---

## What "the day after migration" looks like

Sunday service ends. The pipeline runs automatically:

1. YouTube auto-uploads the recording.
2. Our daily refresh detects it.
3. The video downloads to Drive (5 TB Workspace).
4. Whisper.cpp on the local GPU produces a transcript.
5. Sermon audio is trimmed and uploaded as a podcast MP3.
6. Local Qwen 2.5 14B drafts 20 pieces of content (titles, blog post, social posts, devotional, etc.).
7. Scripture references are verified against the transcript so we never publish a hallucinated verse.
8. An email goes to admins with a link: "Approve at admin.theriverag.church".
9. Steve or Caitlyn opens the link, reviews the drafts, edits if needed, clicks Approve.
10. Distribution fans out: YouTube metadata updates, FB native video upload, IG post, LinkedIn post, recap email, sermon page committed to the static site, calendar event created for next Sunday.

Squarespace cannot do step 1 through step 10 even with every add-on. The self-built path does all of it for ~$32/yr.

---

## Migration plan (high level)

| Week | Milestone |
|---|---|
| Week 1 (now) | Domain transfer Squarespace → Cloudflare started. Static site mirroring complete (already done). Decap CMS scaffolded for volunteer editing. |
| Week 2 | DNS cutover after transfer completes. Squarespace site cancelled at next renewal. |
| Week 3–4 | `church-ops` Phase 0–1 built: ingestion + transcription on a real test sermon. |
| Week 5–6 | `church-ops` Phase 2–3: AI repurposing + distribution wired. |
| Week 7 | `church-ops` Phase 4: approval UI + halt switch + non-technical handoff. |
| Months 2–3 | Phase 5 polish: vertical clips, sermon search, devotional audio. |

---

## Appendix: who plugs into what

| Service | Squarespace path | Self-built path |
|---|---|---|
| Planning Center | Embed scripts | Embed scripts (already wired) |
| Google Workspace | Email forwarding only | Email forwarding **plus** SMTP send + Drive archive + service-account automation |
| YouTube | Embed videos | Embed + automated metadata update + RSS-driven auto-publish + live detection |
| Spotify / Apple Podcasts | Link out to Buzzsprout-hosted feed | Self-hosted feed in repo + GitHub Releases for MP3 |
| Facebook / Instagram | Link out, manual posts | Direct Graph API for posts + native video uploads |
| Mailchimp / Brevo | Embed signup form, paid plan for blasts | Workspace SMTP for blasts; embed any provider for signups |
| Stripe / Square | Squarespace handles checkout | Direct Stripe Checkout if/when needed |
| Cloudflare | Optional in front of Squarespace | Domain registrar + DNS + Workers for the admin gateway |
