/**
 * Ensure the given code gets executed only once since when a page is loaded.
 * This is needed given that some components are loaded by the common.js bundle
 * as well as from their own pageName.js bundle.
 *
 * You might need to call this function to:
 *   - avoid attaching multiple times the same listener to the same event, leading to
 *     inconsistent behavior
 *   - avoid calling the same function on specific DOM elements multiple times
 *     (for instance the function to automatically prepend the search icon to search inputs)
 *
 * @param {string} snippetName the UNIQUE name of the code snippet
 * @param {function} snippet the code to invoke only once
 */
export default function once(snippetName, snippet) {
  return function executeOnce() {
    if (!window.BWSE_ONCE_SNIPPETS) {
      window.BWSE_ONCE_SNIPPETS = {};
    }
    if (!window.BWSE_ONCE_SNIPPETS[snippetName]) {
      snippet();
      window.BWSE_ONCE_SNIPPETS[snippetName] = true;
    }
  };
}
