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

import { escapeAttr, truncate, formatDate, formatNumber, soundPlayerUrls } from './formatters';
import { makeSoundPlayers } from '../components/player/utils';
import { initializeObjectSelectorActions } from '../components/objectSelector';
import { bindDefaultModals } from '../components/modal';
import { makeRatingWidgets } from '../components/rating';
import { bindCollectionModals } from '../components/collectionsModal';
import { bindSimilarSoundsModal } from '../components/similarSoundsModal';
import { bindRemixGroupModals } from '../components/remixGroupModal';

import debounce from 'lodash.debounce';

// ─── Card renderer ──────────────────────────────────────────

/**
 * Clone a <template> and populate all sound card fields: player with
 * overlay buttons, links, date, description, rating widget, and small
 * stat icons. Features degrade gracefully — overlay buttons are only
 * added when the sound has the relevant data, icons slots are only
 * filled when present in the template, etc.
 *
 * Action button state (featured/remove) is handled separately by
 * initializeObjectSelectorActions.
 */
export function populateSoundCard(templateEl, sound, { previewsUrl, displaysUrl }) {
    const clone = templateEl.content.cloneNode(true);
    const urls = soundPlayerUrls(sound, previewsUrl, displaysUrl);
    const username = encodeURIComponent(sound.username);

    const container = clone.querySelector('.bw-selectable-object');
    if (container) container.dataset.objectId = sound.id;

    const overflow = clone.querySelector('.overflow-hidden');
    if (overflow) overflow.setAttribute('aria-label', `Sound ${sound.name} by ${sound.username}`);

    // Player: audio data + overlay button attributes
    const player = clone.querySelector('.bw-player');
    if (player) {
        Object.assign(player.dataset, {
            soundId: sound.id,
            mp3: urls.mp3,
            ogg: urls.ogg,
            waveform: urls.waveform,
            spectrum: urls.spectral,
            title: sound.name,
            duration: sound.duration,
            samplerate: sound.samplerate || 44100,
            showMilliseconds: sound.duration < 10 ? 'true' : 'false',
            collection: 'true',
            collectionModalContentUrl: `/collections/${sound.id}/add/`,
        });
        if (sound.ready_for_similarity) {
            player.dataset.similarSounds = 'true';
            player.dataset.similarSoundsModalUrl = `/people/${username}/sounds/${sound.id}/similar/?ajax=1`;
        }
        if (sound.remix_group) {
            player.dataset.remixGroup = 'true';
            player.dataset.remixGroupModalUrl = `/people/${username}/sounds/${sound.id}/remixes/?ajax=1`;
        }

        const rateWidget = document.createElement('div');
        rateWidget.className = 'display-none bw-player__rate__widget';
        rateWidget.innerHTML = buildRatingWidgetHtml(sound);
        player.insertAdjacentElement('afterend', rateWidget);
    }

    // Links
    const soundLink = clone.querySelector('.js-sound-link');
    if (soundLink) {
        soundLink.href = `/people/${username}/sounds/${sound.id}/`;
        soundLink.title = sound.name;
        soundLink.textContent = sound.name;
    }

    const userLink = clone.querySelector('.js-user-link');
    if (userLink) {
        userLink.href = `/people/${username}/`;
        userLink.title = `Username: ${sound.username}`;
        userLink.textContent = sound.username;
    }

    // Date & description
    const dateEl = clone.querySelector('.js-date');
    if (dateEl) dateEl.textContent = formatDate(sound.created);

    const descEl = clone.querySelector('.js-description');
    if (descEl) {
        const fullDesc = sound.description || '';
        descEl.textContent = truncate(fullDesc, 55);
        if (fullDesc.length >= 55) descEl.title = fullDesc;
    }

    // Small stat icons (only rendered if template has the target slots)
    const iconsTarget = clone.querySelector(`.js-small-icons-line${smallIconsLine(sound)}`);
    if (iconsTarget) iconsTarget.innerHTML = buildSmallIconsHtml(sound);

    return clone;
}

// ─── Card helpers ───────────────────────────────────────────

function smallIconsLine(sound) {
    let count = 1; // license always present
    if (sound.pack_id) count += 1;
    if (sound.has_geotag) count += 1;
    if (sound.num_downloads) count += 2;
    if (sound.num_comments) count += 2;
    if (sound.avg_rating !== null) count += 2;
    const len = (sound.name || '').length;
    if (count >= 6) return len >= 15 ? '2' : '1';
    if (count >= 3) return len >= 23 ? '2' : '1';
    return len >= 30 ? '2' : '1';
}

function buildSmallIconsHtml(sound) {
    let html = '';
    const username = encodeURIComponent(sound.username);
    if (sound.num_downloads)
        html += `<div class="h-spacing-left-1" title="${sound.num_downloads} downloads">`
            + `<a href="javascript:void(0)" data-toggle="modal-default" data-modal-content-url="/people/${username}/sounds/${sound.id}/downloaders/?ajax=1" class="bw-link--grey-light">`
            + `<span class="bw-icon-download" style="font-size:90%"></span> ${formatNumber(sound.num_downloads)}</a></div>`;
    if (sound.num_comments)
        html += `<div class="h-spacing-left-1" title="${sound.num_comments} comments">`
            + `<a href="javascript:void(0)" data-toggle="modal-default" data-modal-content-url="/people/${username}/sounds/${sound.id}/comments/?ajax=1" class="bw-link--grey-light">`
            + `<span class="bw-icon-comments" style="font-size:90%"></span> ${formatNumber(sound.num_comments)}</a></div>`;
    if (sound.pack_id)
        html += `<div class="h-spacing-left-1" title="Pack: ${sound.pack_name || ''}"><a href="/people/${username}/packs/${sound.pack_id}/" class="bw-link--grey-light"><span class="bw-icon-stack"></span></a></div>`;
    if (sound.has_geotag)
        html += `<div class="h-spacing-left-1">`
            + `<a href="javascript:void(0)" data-toggle="modal-default" data-modal-content-url="/people/${username}/sounds/${sound.id}/geotag/?ajax=1" class="bw-link--grey-light">`
            + `<span class="bw-icon-pin"></span></a></div>`;
    html += `<div class="h-spacing-left-1" title="License: ${sound.license_name || ''}"><span class="bw-icon-${sound.license_icon || 'cc'}"></span></div>`;
    if (sound.avg_rating !== null)
        html += `<div class="h-spacing-left-1" title="${sound.num_ratings} rating${sound.num_ratings !== 1 ? 's' : ''}">`
            + `<span class="bw-icon-star"></span><span class="bw-rating__avg"> ${Number(sound.avg_rating).toFixed(1)}</span></div>`;
    return html;
}

function buildStarIcon(type, fillClass) {
    if (type === 'half')
        return `<span class="bw-icon-half-star ${fillClass}"><span class="path1"></span><span class="path2"></span></span>`;
    return `<span class="bw-icon-star ${fillClass}"></span>`;
}

function buildRatingWidgetHtml(sound) {
    const rating = sound.avg_rating !== null ? sound.avg_rating : 0;
    const username = encodeURIComponent(sound.username);
    let html = '<div class="bw-rating__container" data-show-added-rating-on-save="false"'
        + ` aria-label="Average rating of ${rating.toFixed(1)}">`;
    // Stars rendered in reverse order (5 to 1) to match CSS sibling selectors
    for (let i = 5; i >= 1; i--) {
        const low = i - 1;
        const half = (low + i) / 2;
        let type, fill;
        if (i <= rating) { type = 'full'; fill = 'text-red'; }
        else if (half <= rating && rating < i) { type = 'half'; fill = 'text-red'; }
        else { type = 'full'; fill = 'text-light-grey'; }

        html += `<input class="bw-rating__input" type="radio" name="rate-${sound.id}"`
            + ` data-rate-url="/people/${username}/sounds/${sound.id}/rate/${i}/"`
            + ` id="rate-${sound.id}-${i}" value="${i}">`;
        html += `<label for="rate-${sound.id}-${i}" data-value="${i}" aria-label="Rate sound ${i} star${i !== 1 ? 's' : ''}">`;
        html += buildStarIcon(type, fill);
        html += '</label>';
    }
    html += '</div>';
    return html;
}

/**
 * Wrap a card's .bw-selectable-object with edit-mode action buttons
 * (featured toggle + remove toggle). Works with any card produced by
 * populateSoundCard.
 */
export function addEditActions(clone) {
    const container = clone.querySelector('.bw-selectable-object');
    if (!container) return clone;

    container.classList.add('with-actions');

    const actions = document.createElement('div');
    actions.className = 'bw-object-actions';
    actions.innerHTML =
        '<button type="button" class="btn-inverse featured-toggle" data-action="featured">'
        + '<span class="label-default">Make Featured</span>'
        + '<span class="label-hover">Make Featured</span>'
        + '<span class="label-active-default">Featured</span>'
        + '<span class="label-active-hover">Unfeature</span>'
        + '</button>'
        + '<button type="button" class="btn-inverse remove-toggle" data-action="remove"'
        + ' title="Remove from collection" data-container-active-class="marked-for-removal"'
        + ' data-active-title="Undo removal" data-disables="featured">'
        + '<span class="label-default"><span class="bw-icon-trash"></span></span>'
        + '<span class="label-hover">Undo</span>'
        + '</button>';
    container.appendChild(actions);

    return clone;
}

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

        this._defaultSort = opts.defaultSort || Object.keys(this.sortComparators)[0] || 'featured';
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
