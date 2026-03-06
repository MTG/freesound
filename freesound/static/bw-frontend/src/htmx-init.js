import htmx from 'htmx.org';

window.htmx = htmx;

/**
 * HTMX initialization: CSRF token and reinit of UI components after swaps.
 * Expects document.body to have data-csrf-token set by the page template.
 */
(function () {
    const csrfToken = document.body.getAttribute('data-csrf-token');
    if (csrfToken) {
        document.body.addEventListener('htmx:configRequest', (event) => {
            event.detail.headers['X-CSRFToken'] = csrfToken;
        });
    }

    // Reinitialize components (players, checkboxes, modals, etc.) when htmx adds new elements to the DOM.
    // The htmx:load event is triggered for every new element added to the DOM by HTMX.
    document.body.addEventListener('htmx:load', (event) => {
        if (window.initializeStuffInContainer) {
            const newElement = event.detail.elt;
            // Skip document.body since it's already initialized on page load by index.js
            if (newElement && newElement !== document.body) {
                window.initializeStuffInContainer(newElement, true, false);
            }
        }
    });
})();
