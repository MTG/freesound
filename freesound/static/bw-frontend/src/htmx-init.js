import htmx from 'htmx.org';

window.htmx = htmx;

(function () {
  document.body.addEventListener('htmx:configRequest', event => {
    event.detail.headers['X-CSRFToken'] =
      document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
  });

  // htmx:load fires for every new subtree added to the DOM by htmx (including after swap).
  // Rehydrate players, modals, rating widgets, etc. via the project's generic initializer.
  document.body.addEventListener('htmx:load', event => {
    if (window.initializeStuffInContainer) {
      const newElement = event.detail.elt;
      // Skip document.body since it's already initialized on page load by components/index.js
      if (newElement && newElement !== document.body) {
        window.initializeStuffInContainer(newElement, true, false);
      }
    }
  });
})();
