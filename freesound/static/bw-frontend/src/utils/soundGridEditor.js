// Client-side sound grid for collection edit. Sort/search/paginate locally
// against pending state in the store; card HTML for the current page is
// fetched from ``render-cards`` and swapped in by htmx, with the paginator
// arriving as an OOB block in the same response. Per-card button state is
// restored from the store after each swap so the server stays unaware of
// pending flags.

import debounce from 'lodash.debounce';

import { initializeObjectSelectorActions } from '../components/objectSelector';

export class SoundGridEditor {
  // opts: { store, renderCardsUrl?, countEl?, searchInput? }. ``renderCardsUrl``
  // falls back to #sounds-section's data-render-cards-url when omitted.
  constructor(opts) {
    const configEl = document.getElementById('page-config');
    const config = configEl ? JSON.parse(configEl.textContent) : {};

    this.store = opts.store;
    this.renderCardsUrl =
      opts.renderCardsUrl ||
      (document.getElementById('sounds-section') || {}).dataset
        ?.renderCardsUrl ||
      '';
    this.sectionEl = document.getElementById('sounds-section');
    this.gridEl = document.getElementById('sounds-grid');
    this.paginationEl = document.getElementById('sounds-pagination');
    this.countEl = opts.countEl || null;
    this.searchInput = opts.searchInput || null;
    this.sortSelect = document.getElementById('sort-select');
    this.pageSize = config.sounds_per_page || 20;

    this.currentPage = 1;
    this.currentSort = this.sortSelect ? this.sortSelect.value : 'featured';
    this.currentSearch = this.searchInput ? this.searchInput.value.trim() : '';
    this._sortedCache = null;

    this._bindEvents();
    this._autoRender = debounce(() => this.renderPage(), 0);
    // Order is sticky: only the sort dropdown re-sorts. Toggling featured/remove
    // leaves the cached order alone; newly-added sounds get appended so they
    // show up without disturbing existing positions.
    this.store.onChange((id, name) => {
      if (name === 'added') {
        if (this._sortedCache) {
          const meta = this.store
            .allSoundsWithMeta()
            .find(s => s.id === id);
          if (meta) this._sortedCache.data.push(meta);
        }
        this._autoRender();
      } else if (this.countEl && name === 'remove') {
        this.countEl.textContent = this.store.presentCount();
      }
    });

    if (this.countEl) this.countEl.textContent = this.store.presentCount();
    this.renderPage();
  }

  getFilteredSorted() {
    if (!this._sortedCache || this._sortedCache.sort !== this.currentSort) {
      const sorted = this.store.allSoundsWithMeta().slice();
      const comparator = this._getComparator(this.currentSort);
      if (comparator) sorted.sort(comparator);
      this._sortedCache = { data: sorted, sort: this.currentSort };
    }

    if (this.currentSearch) {
      const q = this.currentSearch.toLowerCase();
      return this._sortedCache.data.filter(s => this._matchesSearch(s, q));
    }

    return this._sortedCache.data;
  }

  renderPage() {
    const filtered = this.getFilteredSorted();
    const totalPages = Math.max(1, Math.ceil(filtered.length / this.pageSize));

    if (this.currentPage > totalPages) this.currentPage = totalPages;
    if (this.currentPage < 1) this.currentPage = 1;

    const offset = (this.currentPage - 1) * this.pageSize;
    const pageIds = filtered
      .slice(offset, offset + this.pageSize)
      .map(s => s.id);

    const params = new URLSearchParams({
      ids: pageIds.join(','),
      page: String(this.currentPage),
      total: String(totalPages),
    });
    if (this.currentSearch) params.set('q', this.currentSearch);

    window.htmx.ajax('GET', `${this.renderCardsUrl}?${params}`, {
      target: this.gridEl,
      swap: 'innerHTML',
    });
  }

  featuredIdsForSubmit() {
    const comparator = this._getComparator('featured');
    return this.store
      .allSoundsWithMeta()
      .filter(
        sound =>
          this.store.has(sound.id, 'featured') &&
          !this.store.has(sound.id, 'remove')
      )
      .sort(comparator)
      .map(sound => sound.id);
  }

  _matchesSearch(sound, queryLower) {
    return (
      (sound.name || '').toLowerCase().includes(queryLower) ||
      (sound.username || '').toLowerCase().includes(queryLower)
    );
  }

  _getComparator(key) {
    const store = this.store;
    switch (key) {
      case 'featured':
        return (a, b) => {
          const af = store.has(a.id, 'featured');
          const bf = store.has(b.id, 'featured');
          if (af !== bf) return af ? -1 : 1;
          if (af && bf) {
            const aOrder = Number.isInteger(a.featured_order)
              ? a.featured_order
              : Number.MAX_SAFE_INTEGER;
            const bOrder = Number.isInteger(b.featured_order)
              ? b.featured_order
              : Number.MAX_SAFE_INTEGER;
            if (aOrder !== bOrder) return aOrder - bOrder;
          }
          return new Date(a.date_added || 0) - new Date(b.date_added || 0);
        };
      case 'created_desc':
        return (a, b) =>
          new Date(b.date_added || 0) - new Date(a.date_added || 0);
      case 'created_asc':
        return (a, b) =>
          new Date(a.date_added || 0) - new Date(b.date_added || 0);
      case 'name':
        // Match Python ``str.lower()`` codepoint ordering (see _sort_collection_sounds).
        return (a, b) => {
          const an = (a.name || '').toLowerCase();
          const bn = (b.name || '').toLowerCase();
          if (an < bn) return -1;
          if (an > bn) return 1;
          return 0;
        };
      default:
        return null;
    }
  }

  _getPaginationEl() {
    this.paginationEl = document.getElementById('sounds-pagination');
    return this.paginationEl;
  }

  onAfterSwap(fn) {
    this._afterSwapCallbacks = this._afterSwapCallbacks || [];
    this._afterSwapCallbacks.push(fn);
  }

  _hydrateSwappedGrid() {
    initializeObjectSelectorActions(this.gridEl, this.store);
    if (this.countEl) this.countEl.textContent = this.store.presentCount();
    if (this._afterSwapCallbacks) this._afterSwapCallbacks.forEach(fn => fn());
  }

  _bindEvents() {
    // Paginator clicks go through JS so the (URL-less) sort/search state
    // survives. Delegating on #sounds-section keeps the handler working
    // across OOB swaps that replace #sounds-pagination.
    if (this.sectionEl) {
      this.sectionEl.addEventListener('click', evt => {
        const link = evt.target.closest('#sounds-pagination a[data-page]');
        if (!link) return;
        const nextPage = parseInt(link.dataset.page, 10);
        if (!Number.isFinite(nextPage) || nextPage < 1) return;
        evt.preventDefault();
        this.currentPage = nextPage;
        this.renderPage();
      });
    }

    this.gridEl.addEventListener('htmx:afterSwap', () => {
      this._getPaginationEl();
      this._hydrateSwappedGrid();
    });

    this.gridEl.addEventListener('click', evt => {
      const clearLink = evt.target.closest('[data-clear-search]');
      if (!clearLink) return;
      evt.preventDefault();
      if (this.searchInput) this.searchInput.value = '';
      this.currentSearch = '';
      this.currentPage = 1;
      this.renderPage();
    });

    if (this.searchInput) {
      const handleSearch = () => {
        this.currentSearch = this.searchInput.value.trim();
        this.currentPage = 1;
        this.renderPage();
      };
      this.searchInput.addEventListener('keydown', evt => {
        if (evt.key === 'Enter') {
          evt.preventDefault();
          handleSearch();
        }
      });
      this.searchInput.addEventListener('search', handleSearch);
    }

    if (this.sortSelect) {
      const applySort = () => {
        this.currentSort = this.sortSelect.value;
        this._sortedCache = null;
        this.currentPage = 1;
        this.renderPage();
      };
      this.sortSelect.addEventListener('change', applySort);
      // `change` doesn't fire when re-selecting the current option.
      // Catch that case so the user can re-click "featured" to re-sort
      // after toggling featured flags.
      this.sortSelect.addEventListener('click', evt => {
        if (evt.target.tagName === 'OPTION' && evt.target.value === this.currentSort) {
          applySort();
        }
      });
    }
  }
}
