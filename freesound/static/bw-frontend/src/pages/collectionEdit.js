import { prepareAddMaintainersModalAndFields } from "../components/collectionsModal"
import { prepareAddSoundsModalDynamic } from "../components/addSoundsModal"
import { SoundStateStore } from "../utils/soundStateStore"
import { SoundGridEditor } from "../utils/soundGridEditor"
import { addEditActions } from "../utils/soundCard"

// ─── Data ────────────────────────────────────────────────────

const soundsData = JSON.parse(document.getElementById('sounds-data').textContent);
const initialFeaturedIds = JSON.parse(document.getElementById('featured-data').textContent);

// ─── State & grid ────────────────────────────────────────────

const store = new SoundStateStore(['added', 'remove', 'featured'])
    .load(soundsData, { featured: initialFeaturedIds });

const editor = new SoundGridEditor({
    store,
    countEl: document.getElementById('element-count'),
    searchInput: document.getElementById('edit-collection-search'),
    renderCard(_sound, clone) {
        return addEditActions(clone);
    },
});

editor.renderPage();

// ─── Maintainers ─────────────────────────────────────────────

prepareAddMaintainersModalAndFields(document);

// ─── Add sounds modal ────────────────────────────────────────

prepareAddSoundsModalDynamic(
    document,
    () => store.ids().join(','),
    (sounds) => sounds.forEach(s => store.add(s.id, s))
);

// ─── Form submission ─────────────────────────────────────────

const collectionForm = document.getElementById('collection-form');
if (collectionForm) {
    collectionForm.addEventListener('submit', () => {
        const addedInput = document.getElementById('added_sound_ids');
        const removedInput = document.getElementById('removed_sound_ids');
        const featuredInput = document.getElementById('featured_sounds');

        if (addedInput) addedInput.value = store.idsWithFlag(store.FLAG.ADDED, true).join(',');
        if (removedInput) removedInput.value = store.idsWithFlag(store.FLAG.REMOVE).join(',');
        if (featuredInput) featuredInput.value = store.idsWithFlag(store.FLAG.FEATURED, true).join(',');
    });
}
