/**
 * Reusable client-side sound grid with pagination, search, and sort.
 *
 * Designed to work with SoundStateStore for state management and
 * initializeObjectSelectorActions for per-card action buttons.
 *
 * Usage:
 *   const editor = new SoundGridEditor({ store, gridEl, paginationEl, ... });
 *   editor.renderPage();
 */

import { escapeAttr, formatDate } from './formatters';
import { populateSoundCard } from './soundCard';
export { populateSoundCard, addEditActions } from './soundCard';
import { makeSoundPlayers } from '../components/player/utils';
import { initializeObjectSelectorActions } from '../components/objectSelector';
import { bindDefaultModals } from '../components/modal';
import { makeRatingWidgets } from '../components/rating';
import { bindCollectionModals } from '../components/collectionsModal';
import { bindSimilarSoundsModal } from '../components/similarSoundsModal';
import { bindRemixGroupModals } from '../components/remixGroupModal';

import debounce from 'lodash.debounce';

// ─── SoundGridEditor ────────────────────────────────────────

export class SoundGridEditor {
    /**
     * @param {Object}  opts
     * @param {SoundStateStore} opts.store           - state store for tracked sounds
     * @param {Element}        [opts.gridEl]         - container for rendered sound cards (default: #sounds-grid)
     * @param {Element}        [opts.paginationEl]   - container for pagination controls (default: #sounds-pagination)
     * @param {Element}        [opts.countEl]        - element whose textContent shows the sound count
     * @param {Element}        [opts.searchInput]    - search <input> element
     * @param {Element}        [opts.sortSelect]     - sort <select> element (default: #sort-select)
     * @param {Element}        [opts.cardTemplate]   - <template> element for a single card (default: #sound-card-template)
     * @param {Function}       [opts.renderCard]     - (sound, baseClone) => DocumentFragment post-process hook
     * @param {number}         [opts.pageSize]       - defaults from page-config or 12
     * @param {number}         [opts.maxSounds]      - defaults from page-config or 250
     * @param {Object}         [opts.sortComparators]- { key: (a, b) => number } sort functions
     * @param {string}         [opts.defaultSort]    - initial sort key (default: 'featured')
     * @param {Function}       [opts.searchFilter]   - (sound, query) => boolean
     * @param {Function}       [opts.onPostRender]   - (gridEl) => void, called after each render
     * @param {Element}        [opts.scrollTarget]   - element to scroll into view on page change (default: #sounds-section)
     * @param {boolean|Object} [opts.syncUrl]        - sync grid state with URL query params.
     *        Pass `true` for defaults ({ sort: 's', search: 'q', page: 'page' })
     *        or an object to override individual param names.
     */
    constructor(opts) {
        const configEl = document.getElementById('page-config');
        const config = configEl ? JSON.parse(configEl.textContent) : {};

        this.store = opts.store;
        this.gridEl = opts.gridEl || document.getElementById('sounds-grid');
        this.paginationEl = opts.paginationEl || document.getElementById('sounds-pagination');
        this.countEl = opts.countEl || null;
        this.searchInput = opts.searchInput || null;
        this.sortSelect = opts.sortSelect || document.getElementById('sort-select');
        this.cardTemplate = opts.cardTemplate || document.getElementById('sound-card-template');
        this.pageSize = opts.pageSize || config.sounds_per_page;
        this.maxSounds = opts.maxSounds || config.max_sounds;
        this.previewsUrl = opts.previewsUrl || config.previews_url || '';
        this.displaysUrl = opts.displaysUrl || config.displays_url || '';
        this.sortComparators = opts.sortComparators || this._defaultComparators();
        this.searchFilter = opts.searchFilter || SoundGridEditor.defaultSearchFilter;
        this.scrollTarget = opts.scrollTarget || document.getElementById('sounds-section');
        this.onPostRender = opts.onPostRender || SoundGridEditor.defaultPostRender;

        const postProcess = opts.renderCard || null;
        this.renderCard = (sound) => {
            const clone = populateSoundCard(this.cardTemplate, sound, {
                previewsUrl: this.previewsUrl,
                displaysUrl: this.displaysUrl,
            });
            return postProcess ? postProcess(sound, clone) : clone;
        };

        this._defaultSort = opts.defaultSort || Object.keys(this.sortComparators)[0];
        this.currentPage = 1;
        this.currentSort = this._defaultSort;
        this.currentSearch = '';
        this._sortedCache = null;

        this._urlParams = opts.syncUrl
            ? { sort: 's', search: 'q', page: 'page', ...(typeof opts.syncUrl === 'object' ? opts.syncUrl : {}) }
            : null;
        if (this._urlParams) this._readUrl();

        this._bindEvents();
        this._autoRender = debounce(() => this.renderPage(), 0);
        this._storeListener = (_id, flag) => {
            if (flag === this.store.FLAG.ADDED) {
                this._autoRender();
            } else if (this.countEl) {
                this.countEl.textContent = this.store.presentCount();
            }
        };
        this.store.onChange(this._storeListener);
    }

    static defaultSearchFilter(sound, query) {
        const q = query.toLowerCase();
        return (sound.name || '').toLowerCase().includes(q)
            || (sound.username || '').toLowerCase().includes(q)
            || (sound.description || '').toLowerCase().includes(q)
            || formatDate(sound.created).toLowerCase().includes(q);
    }

    static defaultPostRender(gridEl) {
        bindDefaultModals(gridEl);
        makeRatingWidgets(gridEl);
        bindCollectionModals(gridEl);
        bindSimilarSoundsModal(gridEl);
        bindRemixGroupModals(gridEl);
    }

    getFilteredSorted() {
        const sounds = this.store.allSoundsWithMeta();

        if (!this._sortedCache
            || this._sortedCache.data.length !== sounds.length
            || this._sortedCache.sort !== this.currentSort) {
            const sorted = sounds.slice();
            const comparator = this.sortComparators[this.currentSort];
            if (comparator) sorted.sort(comparator);
            this._sortedCache = { data: sorted, sort: this.currentSort };
        }

        if (this.currentSearch) {
            const q = this.currentSearch;
            return this._sortedCache.data.filter(s => this.searchFilter(s, q));
        }

        return this._sortedCache.data;
    }

    renderPage() {
        const filtered = this.getFilteredSorted();
        const totalItems = filtered.length;
        const totalPages = Math.max(1, Math.ceil(totalItems / this.pageSize));

        if (this.currentPage > totalPages) this.currentPage = totalPages;
        if (this.currentPage < 1) this.currentPage = 1;

        const offset = (this.currentPage - 1) * this.pageSize;
        const pageSounds = filtered.slice(offset, offset + this.pageSize);

        if (pageSounds.length > 0) {
            const wrapper = document.createElement('div');
            wrapper.className = 'bw-object-selector-container row no-gutters';
            wrapper.style.marginLeft = '-8px';
            wrapper.style.marginRight = '-8px';
            wrapper.dataset.type = 'sounds';
            wrapper.dataset.maxElements = this.maxSounds;
            pageSounds.forEach(sound => wrapper.appendChild(this.renderCard(sound)));
            this.gridEl.innerHTML = '';
            this.gridEl.appendChild(wrapper);
        } else if (this.currentSearch) {
            this.gridEl.innerHTML =
                `<div class="v-spacing-3 text-grey">No sounds found matching &ldquo;${escapeAttr(this.currentSearch)}&rdquo;. <a href="#" data-clear-search>Clear search</a></div>`;
        } else {
            this.gridEl.innerHTML = '';
        }

        this.paginationEl.innerHTML = this._renderPaginationHTML(totalPages, this.currentPage);

        makeSoundPlayers(this.gridEl);
        initializeObjectSelectorActions(this.gridEl, this.store);
        if (this.onPostRender) this.onPostRender(this.gridEl);

        if (this.countEl) this.countEl.textContent = this.store.presentCount();
        if (this._urlParams) this._pushUrl();
    }

    destroy() {
        this.store.removeListener(this._storeListener);
        this._autoRender.cancel();
    }

    // ─── Private ──────────────────────────────────────────────

    _defaultComparators() {
        const store = this.store;
        return {
            featured: (a, b) => {
                const aIsFeat = store.hasFlag(a.id, store.FLAG.FEATURED);
                const bIsFeat = store.hasFlag(b.id, store.FLAG.FEATURED);
                if (aIsFeat !== bIsFeat) return aIsFeat ? -1 : 1;
                return new Date(a.date_added || 0) - new Date(b.date_added || 0);
            },
            created_desc: (a, b) => new Date(b.date_added || 0) - new Date(a.date_added || 0),
            created_asc: (a, b) => new Date(a.date_added || 0) - new Date(b.date_added || 0),
            name: (a, b) => (a.name || '').localeCompare(b.name || ''),
        };
    }

    _renderPaginationHTML(totalPages, page) {
        if (totalPages <= 1) return '';

        const adjacent = 3;
        const wanted = adjacent * 2 + 1;
        let minPage = Math.max(page - adjacent, 1);
        let maxPage = Math.min(page + adjacent + 1, totalPages + 1);
        const numItems = maxPage - minPage;

        if (numItems < wanted && numItems < totalPages) {
            if (minPage === 1) {
                maxPage = Math.min(maxPage + (wanted - numItems), totalPages + 1);
            } else {
                minPage = Math.max(minPage - (wanted - numItems), 1);
            }
        }

        const pageNumbers = [];
        for (let n = minPage; n < maxPage; n++) {
            if (n > 0 && n <= totalPages) pageNumbers.push(n);
        }

        const showFirst = !pageNumbers.includes(1);
        const showLast = !pageNumbers.includes(totalPages);
        const lastIsNext = totalPages - 1 === pageNumbers[pageNumbers.length - 1];

        let html = '<ul class="bw-pagination_container">';

        if (page > 1) {
            html += `<li><a href="#" data-page="${page - 1}" class="bw-link--white bw-pagination_circle bw-pagination_direction no-hover" title="Previous Page" aria-label="Previous Page"><span class="bw-icon-arrow-left white"></span></a></li>`;
        }

        if (showFirst) {
            html += '<li class="first-page"><a href="#" data-page="1" title="First Page">1</a></li>';
            html += '<li class="text-grey no-paddings">...</li>';
        }

        pageNumbers.forEach(num => {
            if (num === page) {
                html += `<li class="bw-pagination_circle bw-pagination_selected">${num}</li>`;
            } else {
                html += `<li><a href="#" data-page="${num}" title="Page ${num}">${num}</a></li>`;
            }
        });

        if (showLast) {
            if (!lastIsNext) html += '<li class="text-grey no-paddings">...</li>';
            html += `<li><a href="#" data-page="${totalPages}" title="Last Page" aria-label="Last Page">${totalPages}</a></li>`;
        }

        if (page < totalPages) {
            html += `<li><a href="#" data-page="${page + 1}" class="bw-link--white bw-pagination_circle bw-pagination_direction no-hover" title="Next Page" aria-label="Next Page"><span class="bw-icon-arrow"></span></a></li>`;
        }

        html += '</ul>';
        return html;
    }

    _readUrl() {
        const params = new URLSearchParams(window.location.search);
        const sort = params.get(this._urlParams.sort);
        const search = params.get(this._urlParams.search) || '';
        const page = parseInt(params.get(this._urlParams.page), 10) || 1;

        if (sort) this.currentSort = sort;
        this.currentSearch = search;
        this.currentPage = page;

        if (search && this.searchInput) this.searchInput.value = search;
        if (sort && this.sortSelect) this.sortSelect.value = sort;
    }

    _pushUrl() {
        const url = new URL(window.location);
        const p = this._urlParams;
        const setOrDelete = (key, value, fallback) => {
            if (value && value !== fallback) url.searchParams.set(key, value);
            else url.searchParams.delete(key);
        };
        setOrDelete(p.search, this.currentSearch, '');
        setOrDelete(p.sort, this.currentSort, this._defaultSort);
        setOrDelete(p.page, this.currentPage > 1 ? String(this.currentPage) : '', '');
        history.replaceState(null, '', url);
    }

    _bindEvents() {
        this.paginationEl.addEventListener('click', evt => {
            const link = evt.target.closest('a[data-page]');
            if (!link) return;
            evt.preventDefault();
            this.currentPage = parseInt(link.dataset.page, 10);
            this.renderPage();
            const target = this.scrollTarget || this.gridEl.parentElement;
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
            const handleSearch = debounce(() => {
                this.currentSearch = this.searchInput.value.trim();
                this.currentPage = 1;
                this.renderPage();
            }, 150);
            this.searchInput.addEventListener('input', handleSearch);
            this.searchInput.addEventListener('search', handleSearch);
        }

        if (this.sortSelect) {
            this.sortSelect.addEventListener('change', () => {
                this.currentSort = this.sortSelect.value;
                this.currentPage = 1;
                this.renderPage();
            });
        }
    }
}
