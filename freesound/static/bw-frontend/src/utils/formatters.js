/**
 * Shared formatting and URL helpers for sound-related pages.
 */

export function escapeAttr(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

export function truncate(str, len) {
    if (!str || str.length <= len) return str || '';
    return str.substring(0, len) + '\u2026';
}

export function formatDate(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return String(isoString);
    const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December',
    ];
    const day = d.getDate();
    const suffix = [1, 21, 31].includes(day) ? 'st'
        : [2, 22].includes(day) ? 'nd'
        : [3, 23].includes(day) ? 'rd' : 'th';
    return `${months[d.getMonth()]} ${day}${suffix}, ${d.getFullYear()}`;
}

export function formatNumber(n) {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return String(n);
}

export function soundPlayerUrls(sound, previewsUrl, displaysUrl) {
    if (!sound.user_id) {
        return {
            mp3: sound.mp3 || '',
            ogg: sound.ogg || '',
            waveform: sound.waveform || '',
            spectral: sound.spectral || '',
        };
    }
    const folder = Math.floor(sound.id / 1000);
    return {
        mp3: `${previewsUrl}${folder}/${sound.id}_${sound.user_id}-lq.mp3`,
        ogg: `${previewsUrl}${folder}/${sound.id}_${sound.user_id}-lq.ogg`,
        waveform: `${displaysUrl}${folder}/${sound.id}_${sound.user_id}_wave_bw_M.png`,
        spectral: `${displaysUrl}${folder}/${sound.id}_${sound.user_id}_spec_bw_M.jpg`,
    };
}
