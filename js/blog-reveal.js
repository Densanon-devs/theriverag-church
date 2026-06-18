/* Scroll fade/slide-in reveals for blog & sermon-note pages.
   Progressive enhancement: the `.reveal` class (which hides the element until
   it scrolls in) is added BY this script, so visitors without JS — or with
   "reduce motion" set — always see the full content immediately. */
(function () {
  "use strict";

  var reduce = window.matchMedia
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Direct children of a sermon-note article + the index cards. (Using direct
  // children keeps the reveal at the section level — each heading, paragraph,
  // the video, the CTA — rather than animating nested spans.)
  var selector = [
    ".blog-post > h2",
    ".blog-post > h3",
    ".blog-post > p",
    ".blog-post > ul",
    ".blog-post > ol",
    ".blog-post > blockquote",
    ".blog-post > .sermon-video",
    ".blog-post > .blog-cta",
    ".blog-post > .blog-rule",
    ".blog-card"
  ].join(", ");

  var targets = Array.prototype.slice.call(document.querySelectorAll(selector));
  if (!targets.length) return;

  // No IntersectionObserver / reduced motion → leave everything visible.
  if (reduce || !("IntersectionObserver" in window)) return;

  targets.forEach(function (el) { el.classList.add("reveal"); });

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });

  targets.forEach(function (el) { io.observe(el); });

  // Safety net: if anything is still hidden a moment after load (e.g. an
  // observer edge case on very short pages), reveal it so content is never lost.
  window.addEventListener("load", function () {
    setTimeout(function () {
      targets.forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.top < window.innerHeight && !el.classList.contains("is-visible")) {
          el.classList.add("is-visible");
        }
      });
    }, 600);
  });
})();
