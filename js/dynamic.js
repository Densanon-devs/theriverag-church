// Fetches public feed data and renders it into page placeholders.

(function () {
  function $(sel) { return document.querySelector(sel); }
  function fmtDate(iso) {
    var d = new Date(iso);
    return (d.getMonth() + 1) + "/" + d.getDate() + "/" + String(d.getFullYear()).slice(-2);
  }
  function dataUrl(name) {
    // Resolve relative to the site root regardless of current page depth.
    var depth = (location.pathname.match(/\//g) || []).length - 1;
    return (depth > 0 ? "../".repeat(depth) : "") + "site/data/" + name;
  }

  function renderSermons() {
    var grid = $("#sermons-dynamic");
    if (!grid) return;
    fetch(dataUrl("sermons.json"), { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (items) {
        if (!items.length) return;
        grid.innerHTML = "";
        items.forEach(function (it) {
          var a = document.createElement("a");
          a.href = it.url;
          a.target = "_blank";
          a.rel = "noopener";
          a.className = "sermon-card";
          a.innerHTML =
            '<div class="sermon-thumb"><img loading="lazy" src="' + it.thumbnail + '" alt="' +
            it.title.replace(/"/g, "&quot;") + '"></div>' +
            '<div class="sermon-meta">' +
              '<span class="sermon-category">Sunday Service</span>' +
              '<h3 class="sermon-title">' + it.title + '</h3>' +
              '<span class="sermon-date">' + fmtDate(it.published) + '</span>' +
            '</div>';
          grid.appendChild(a);
        });
      })
      .catch(function () { /* leave static fallback in place */ });
  }

  function updateLivePlayer() {
    var iframe = document.getElementById("home-live-embed");
    if (!iframe) return;
    fetch(dataUrl("live.json"), { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (state) {
        if (!state || !state.videoId) return;
        var src = state.live
          ? "https://www.youtube.com/embed/" + state.videoId + "?autoplay=1&mute=1"
          : "https://www.youtube.com/embed/" + state.videoId;
        iframe.src = src;
        if (state.live) {
          var heading = document.querySelector(".live-card h3 a");
          if (heading) heading.textContent = "We're live on Youtube right now!";
        }
      })
      .catch(function () { /* keep server-rendered fallback */ });
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderSermons();
    updateLivePlayer();
  });
})();
