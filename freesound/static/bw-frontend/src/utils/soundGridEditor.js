// Sound grid for collection/pack edit pages. Client holds a pending delta (added/removed/featured);
// server owns search/sort/paginate and is re-fetched from render-cards on every change.

import { wireAddSoundsModal } from '../components/addSoundsModal';
import { initializeObjectSelectorActions } from '../components/objectSelector';

const idList = str => (str || '').split(',').filter(Boolean).map(Number);

// data-grid-value → the ids that field gets on submit
const VALUE_SOURCES = {
  added: e => [...e.added].filter(id => !e.removed.has(id)),
  removed: e => [...e.removed],
  featured: e => e.featured.filter(id => !e.removed.has(id)),
};

class SoundGridEditor {
  constructor(sectionEl) {
    this.sectionEl = sectionEl;
    this.gridEl = document.getElementById('sounds-grid');
    this.searchInput = document.getElementById('sounds-search');
    this.sortSelect = document.getElementById('sort-select');
    this.countEl = document.getElementById('element-count');
    this.featuredCountEl = document.getElementById('featured-count');

    this.url = sectionEl.dataset.renderCardsUrl;
    this.maxFeatured = parseInt(sectionEl.dataset.maxFeatured, 10) || 0;
    this.actionNames = this.maxFeatured ? ['remove', 'featured'] : ['remove'];

    this.added = new Set();
    this.removed = new Set();
    // Ordered (saved first, newly featured appended); also drives the "featured" sort
    this.featured = idList(sectionEl.dataset.featuredIds);
    this.total = 0; // saved + added, sent by the server on each render

    this.page = 1;
    this.sort = this.sortSelect ? this.sortSelect.value : '';
    this.search = this.searchInput ? this.searchInput.value.trim() : '';

    this.bindEvents();
    wireAddSoundsModal(
      document,
      () => [...this.added].join(','),
      ids => {
        ids.forEach(id => this.added.add(id));
        this.renderPage();
      }
    );
    this.renderPage();
  }

  renderPage() {
    const params = new URLSearchParams({ s: this.sort, page: this.page });
    if (this.added.size) params.set('added', [...this.added].join(','));
    if (this.search) params.set('q', this.search);
    if (this.maxFeatured) params.set('featured', this.featured.join(','));
    window.htmx.ajax('GET', `${this.url}?${params}`, {
      target: this.gridEl,
      swap: 'innerHTML',
    });
  }

  // has() and toggleAction() are called by the card buttons (see initializeObjectSelectorActions)
  has(id, name) {
    return name === 'remove'
      ? this.removed.has(id)
      : this.featured.includes(id);
  }

  // Returns the new state, or undefined when the click is a no-op
  toggleAction(id, name) {
    if (name === 'remove') {
      if (!this.removed.delete(id)) this.removed.add(id);
    } else if (name === 'featured') {
      const position = this.featured.indexOf(id);
      if (position !== -1) this.featured.splice(position, 1);
      else if (this.featuredCount() < this.maxFeatured) this.featured.push(id);
      else return undefined; // at the limit
    } else {
      return undefined;
    }
    this.syncCounts();
    return this.has(id, name);
  }

  featuredCount() {
    return this.featured.filter(id => !this.removed.has(id)).length;
  }

  // Counters, plus greying out the featured buttons that can't be clicked
  syncCounts() {
    if (this.countEl) this.countEl.textContent = this.total - this.removed.size;
    if (!this.maxFeatured) return;

    const count = this.featuredCount();
    if (this.featuredCountEl) this.featuredCountEl.textContent = count;

    const atLimit = count >= this.maxFeatured;
    this.gridEl.querySelectorAll('[data-action="featured"]').forEach(btn => {
      const id = Number(btn.closest('[data-object-id]').dataset.objectId);
      btn.disabled =
        this.removed.has(id) || (!this.featured.includes(id) && atLimit);
    });
  }

  bindEvents() {
    const reload = (page = 1) => {
      this.page = page;
      this.renderPage();
    };

    // Delegated: swaps replace #sounds-pagination, and this keeps sort/search state (no URL)
    this.sectionEl.addEventListener('click', evt => {
      const link = evt.target.closest('#sounds-pagination a[data-page]');
      if (!link) return;
      evt.preventDefault();
      const page = parseInt(link.dataset.page, 10);
      if (page >= 1) reload(page);
    });

    this.gridEl.addEventListener('htmx:afterSwap', () => {
      const meta = this.gridEl.querySelector('[data-grid-total]');
      this.total = meta ? Number(meta.dataset.gridTotal) : 0;
      initializeObjectSelectorActions(this.gridEl, this);
      this.syncCounts();
    });

    if (this.searchInput) {
      const applySearch = () => {
        this.search = this.searchInput.value.trim();
        reload();
      };
      this.searchInput.addEventListener('search', applySearch);
      this.searchInput.addEventListener('keydown', evt => {
        if (evt.key !== 'Enter') return;
        evt.preventDefault();
        applySearch();
      });
      this.gridEl.addEventListener('click', evt => {
        if (!evt.target.closest('[data-clear-search]')) return;
        evt.preventDefault();
        this.searchInput.value = '';
        applySearch();
      });
    }

    if (this.sortSelect) {
      // Deselect while the dropdown is open so re-picking the same option still fires `change`
      let lastValue = this.sortSelect.value;
      this.sortSelect.addEventListener('mousedown', () => {
        lastValue = this.sortSelect.value;
        this.sortSelect.selectedIndex = -1;
      });
      this.sortSelect.addEventListener('change', () => {
        this.sort = this.sortSelect.value;
        reload();
      });
      this.sortSelect.addEventListener('blur', () => {
        if (this.sortSelect.selectedIndex === -1)
          this.sortSelect.value = lastValue;
      });
    }
  }
}

const initSoundGridEditor = () => {
  const sectionEl = document.getElementById('sounds-section');
  if (!sectionEl) return;
  const editor = new SoundGridEditor(sectionEl);

  const form = sectionEl.closest('form');
  if (!form) return;
  form.addEventListener('submit', () => {
    form.querySelectorAll('[data-grid-value]').forEach(input => {
      const source = VALUE_SOURCES[input.dataset.gridValue];
      if (source) input.value = source(editor).join(',');
      else console.warn(`Unknown data-grid-value "${input.dataset.gridValue}"`);
    });
  });
};

export { initSoundGridEditor };
