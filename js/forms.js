// Contact + prayer-request form submission.
//
// The generated markup posted to /api/site/forms/<kind>, a relative path that has
// never existed on this site — it deploys as static GitHub Pages, which answers a
// POST with 405 Method Not Allowed. Every submission since the page shipped
// (2026-05-16) dumped the visitor on an error page and was lost, prayer requests
// included. The forms now point at a hosted form endpoint; this file upgrades that
// to an inline submit so nobody leaves the page, and falls back to a plain mailto
// so a message is never silently dropped again.
//
// Progressive enhancement: with JS off, the form's own action still posts natively.

(function () {
  'use strict';

  var FALLBACK_EMAIL = 'steven@theriverag.church';

  function statusEl(form) {
    var el = form.querySelector('.cms-form-status');
    if (!el) {
      el = document.createElement('p');
      el.className = 'cms-form-status';
      el.setAttribute('role', 'status');
      el.setAttribute('aria-live', 'polite');
      form.appendChild(el);
    }
    return el;
  }

  function setStatus(form, message, kind) {
    var el = statusEl(form);
    el.textContent = message;
    el.className = 'cms-form-status is-' + kind;
  }

  // On failure, hand the visitor a prefilled mailto so their words survive the
  // round trip. Losing a prayer request to a network blip is the thing this page
  // has already done for months; it should not be possible again.
  function failWithFallback(form, data) {
    var subject = 'Website ' + (form.getAttribute('data-cms-form') || 'contact') + ' form';
    var lines = [];
    data.forEach(function (value, key) {
      if (key !== '_hp' && String(value).trim()) { lines.push(key + ': ' + value); }
    });
    var href = 'mailto:' + FALLBACK_EMAIL +
      '?subject=' + encodeURIComponent(subject) +
      '&body=' + encodeURIComponent(lines.join('\n'));

    var el = statusEl(form);
    el.className = 'cms-form-status is-error';
    el.textContent = 'Sorry — that did not go through. ';
    var a = document.createElement('a');
    a.href = href;
    a.textContent = 'Send it by email instead';
    el.appendChild(a);
    el.appendChild(document.createTextNode(' and nothing you typed is lost.'));
  }

  document.addEventListener('DOMContentLoaded', function () {
    var forms = document.querySelectorAll('form.cms-form');

    Array.prototype.forEach.call(forms, function (form) {
      form.addEventListener('submit', function (event) {
        var action = form.getAttribute('action') || '';
        // Nothing configured yet — let the browser do whatever it would have done
        // rather than swallow the submit and look broken in a new way.
        if (!action || action.indexOf('/api/site/forms/') === 0) { return; }

        event.preventDefault();

        var data = new FormData(form);
        var button = form.querySelector('button[type="submit"], button:not([type])');
        var original = button ? button.textContent : '';

        // Honeypot: a bot filled the hidden field. Show the normal success state
        // so it learns nothing, and send nothing.
        if (String(data.get('_hp') || '').trim()) {
          form.reset();
          setStatus(form, 'Thank you — we have received your message.', 'ok');
          return;
        }
        data.delete('_hp');

        if (button) { button.disabled = true; button.textContent = 'Sending…'; }
        setStatus(form, 'Sending…', 'pending');

        fetch(action, {
          method: 'POST',
          body: data,
          headers: { 'Accept': 'application/json' }
        }).then(function (response) {
          if (!response.ok) { throw new Error('HTTP ' + response.status); }
          form.reset();
          setStatus(form, 'Thank you — we have received your message.', 'ok');
        }).catch(function () {
          failWithFallback(form, data);
        }).then(function () {
          if (button) { button.disabled = false; button.textContent = original; }
        });
      });
    });
  });
})();
