/**
 * Sound card rendering: clone a <template> and populate all fields
 * (player, links, date, description, rating widget, stat icons).
 *
 * Also provides addEditActions() to wrap a card with featured/remove
 * action buttons for edit mode.
 */

import { escapeAttr, truncate, formatDate, formatNumber, soundPlayerUrls } from './formatters';

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
    if (iconsTarget) iconsTarget.innerHTML = buildSmallIconsHtml(sound, username);

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

function buildSmallIconsHtml(sound, username) {
    let html = '';
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

function buildRatingWidgetHtml(sound) {
    const rating = sound.avg_rating !== null ? sound.avg_rating : 0;
    const username = encodeURIComponent(sound.username);
    let html = '<div class="bw-rating__container" data-show-added-rating-on-save="false"'
        + ` aria-label="Average rating of ${rating.toFixed(1)}">`;
    // Stars rendered in reverse order (5 to 1) to match CSS sibling selectors
    for (let i = 5; i >= 1; i--) {
        const low = i - 1;
        const half = (low + i) / 2;
        let isHalf, fill;
        if (i <= rating) { isHalf = false; fill = 'text-red'; }
        else if (half <= rating && rating < i) { isHalf = true; fill = 'text-red'; }
        else { isHalf = false; fill = 'text-light-grey'; }

        html += `<input class="bw-rating__input" type="radio" name="rate-${sound.id}"`
            + ` data-rate-url="/people/${username}/sounds/${sound.id}/rate/${i}/"`
            + ` id="rate-${sound.id}-${i}" value="${i}">`;
        html += `<label for="rate-${sound.id}-${i}" data-value="${i}" aria-label="Rate sound ${i} star${i !== 1 ? 's' : ''}">`;
        html += isHalf
            ? `<span class="bw-icon-half-star ${fill}"><span class="path1"></span><span class="path2"></span></span>`
            : `<span class="bw-icon-star ${fill}"></span>`;
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
