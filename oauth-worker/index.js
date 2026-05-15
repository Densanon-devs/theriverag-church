// Decap CMS GitHub OAuth proxy — Cloudflare Worker.
//
// Decap runs in the browser at /admin/ and can't hold a GitHub OAuth client
// secret. This worker handles the secret-bearing legs of the dance:
//
//   1. Decap opens a popup at:  <worker>/auth?provider=github
//   2. We redirect to:          github.com/login/oauth/authorize
//   3. GitHub redirects back to: <worker>/callback?code=...
//   4. We exchange code+secret for an access_token
//   5. We return an HTML page that postMessages the token back to Decap
//
// Env vars (Cloudflare dashboard → Worker → Settings → Variables):
//   OAUTH_CLIENT_ID       plain
//   OAUTH_CLIENT_SECRET   encrypted
//
// To deploy via the Cloudflare dashboard:
//   1. Workers & Pages → Create → Worker → name it "decap-oauth"
//   2. Quick edit → paste THIS FILE's contents → Save and Deploy
//   3. Settings → Variables → add OAUTH_CLIENT_ID + OAUTH_CLIENT_SECRET (encrypt the secret)
//   4. Your worker URL is e.g. https://decap-oauth.<account>.workers.dev
//   5. Update the GitHub OAuth App's callback URL to:
//        https://decap-oauth.<account>.workers.dev/callback
//   6. (Optional) Add a custom domain like decap-oauth.theriverag.church
//      and update admin/config.yml's base_url to match.

const SCOPE = "repo,user:email";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // ── /auth → redirect to GitHub for user consent ──────────────────
    if (url.pathname === "/auth") {
      if (!env.OAUTH_CLIENT_ID) {
        return text("OAUTH_CLIENT_ID not configured on this Worker.", 500);
      }
      const state = crypto.randomUUID();
      const gh = new URL("https://github.com/login/oauth/authorize");
      gh.searchParams.set("client_id", env.OAUTH_CLIENT_ID);
      gh.searchParams.set("redirect_uri", `${url.origin}/callback`);
      gh.searchParams.set("scope", SCOPE);
      gh.searchParams.set("state", state);
      return new Response(null, {
        status: 302,
        headers: {
          Location: gh.toString(),
          // Cookie binds /callback to this /auth so a stray callback URL
          // with someone else's code can't be replayed.
          "Set-Cookie": `oauth_state=${state}; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=600`,
        },
      });
    }

    // ── /callback → exchange code, postMessage token to Decap ────────
    if (url.pathname === "/callback") {
      const code = url.searchParams.get("code");
      const stateParam = url.searchParams.get("state");
      const cookies = request.headers.get("Cookie") || "";
      const stateCookie = (cookies.match(/oauth_state=([^;]+)/) || [])[1];

      if (!code || !stateParam || stateParam !== stateCookie) {
        return html(
          `<h1>OAuth error</h1>
           <p>State mismatch or missing code. Start over from
           <a href="https://theriverag.church/admin/">/admin/</a>.</p>`,
          400
        );
      }

      const tokenRes = await fetch("https://github.com/login/oauth/access_token", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify({
          client_id: env.OAUTH_CLIENT_ID,
          client_secret: env.OAUTH_CLIENT_SECRET,
          code,
        }),
      });
      const data = await tokenRes.json();
      const token = data.access_token;
      if (!token) {
        return html(
          `<h1>GitHub rejected the code exchange</h1>
           <pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`,
          500
        );
      }

      // The exact message format Decap CMS expects. Sent both reactively
      // (in response to "authorizing:github" from the opener) and
      // proactively (on load) so Decap always picks it up.
      const payload = JSON.stringify({ token, provider: "github" });
      const messageJs = JSON.stringify(`authorization:github:success:${payload}`);

      return html(
        `<p>Signed in! This window should close automatically.</p>
<script>
(function () {
  var msg = ${messageJs};
  function send() { if (window.opener) window.opener.postMessage(msg, "*"); }
  window.addEventListener("message", function (e) {
    if (typeof e.data === "string" && e.data.indexOf("authorizing:github") === 0) send();
  });
  send();
  setTimeout(function () { window.close(); }, 2500);
})();
</script>`,
        200,
        { "Set-Cookie": "oauth_state=; Path=/; Max-Age=0" }
      );
    }

    return text(
      "Decap OAuth proxy. Endpoints: /auth, /callback.\n" +
      "Visit https://theriverag.church/admin/ to sign in.",
      200
    );
  },
};

function html(body, status = 200, extraHeaders = {}) {
  return new Response(
    `<!doctype html><html><body style="font-family:sans-serif;padding:1.5rem;">${body}</body></html>`,
    { status, headers: { "Content-Type": "text/html; charset=utf-8", ...extraHeaders } }
  );
}

function text(body, status = 200) {
  return new Response(body, { status, headers: { "Content-Type": "text/plain; charset=utf-8" } });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
