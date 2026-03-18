import { SoundStateStore } from "../utils/soundStateStore"
import { SoundGridEditor } from "../utils/soundGridEditor"

// ─── Data ────────────────────────────────────────────────────

const soundsData = JSON.parse(document.getElementById('sounds-data').textContent);
const initialFeaturedIds = JSON.parse(document.getElementById('featured-data').textContent);

// ─── State & grid ────────────────────────────────────────────

const store = new SoundStateStore(['featured'])
    .load(soundsData, { featured: initialFeaturedIds });

const editor = new SoundGridEditor({
    store,
    searchInput: document.getElementById('collection-search'),
    syncUrl: true,
    renderCard(sound, clone) {
        if (store.hasFlag(sound.id, store.FLAG.FEATURED)) {
            const col = clone.querySelector('.col-md-4');
            if (col) col.style.backgroundColor = '#fff8e1';
        }
        return clone;
    },
});

editor.renderPage();
