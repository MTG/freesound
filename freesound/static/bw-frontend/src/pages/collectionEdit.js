import { prepareAddMaintainersModalAndFields } from "../components/collectionsModal"
import { prepareAddSoundsModalDynamic } from "../components/addSoundsModal"
import { initializeObjectSelectorActions } from "../components/objectSelector"
import { SoundStateStore, STATE } from "../utils/soundStateStore"

const store = new SoundStateStore({
    // collection_sounds is a read-only init element (no name attr, not submitted with the form)
    input: document.getElementById('collection_sounds'),
    actions: [
        { actionName: 'featured', flag: STATE.FEATURED, input: document.getElementById('featured_sounds') },
        { actionName: 'remove', flag: STATE.REMOVED, input: document.getElementById('removed_sound_ids') },
        { actionName: 'added', flag: STATE.ADDED, input: document.getElementById('added_sound_ids') },
    ],
});

// React to state changes: update element count and sync hidden inputs
const countEl = document.getElementById('element-count');
store.onChange(function (_objectId, flag, _isActive) {
    if (countEl && flag & (STATE.REMOVED | STATE.ADDED)) {
        countEl.textContent = store.presentCount();
    }
    store.syncInputs();
});

const refreshSoundsSection = () => {
    const soundsSection = document.getElementById('sounds-section');
    if (!soundsSection) return;

    const searchInput = document.getElementById('edit-collection-search');
    const sortSelect = document.getElementById('sort-select');
    const params = [];

    if (searchInput && searchInput.value) params.push(`q=${encodeURIComponent(searchInput.value)}`);
    if (sortSelect && sortSelect.value) params.push(`s=${encodeURIComponent(sortSelect.value)}`);
    params.push(`added_sounds=${store.idsWithFlag(STATE.ADDED).join(',')}`);
    params.push(`featured_sounds=${store.idsWithFlag(STATE.FEATURED, true).join(',')}`);

    const activePage = soundsSection.querySelector('.bw-pagination_selected');
    if (activePage) params.push(`page=${activePage.textContent.trim()}`);

    const baseUrl = sortSelect.getAttribute('hx-get');
    htmx.ajax('GET', `${baseUrl}?${params.join('&')}`, {
        target: '#sounds-section',
        select: '#sounds-section',
        swap: 'outerHTML',
    });
};

prepareAddMaintainersModalAndFields(document);
prepareAddSoundsModalDynamic(
    document,
    () => store.ids().join(','),
    (selectedIds) => { selectedIds.forEach(id => store.add(id)); refreshSoundsSection(); }
);
initializeObjectSelectorActions(document, store);

// Serialize hidden inputs just before the form is submitted
const collectionForm = document.getElementById('collection-form');
if (collectionForm) {
    collectionForm.addEventListener('submit', function () {
        store.syncInputs();
    });
}

// Re-initialise sound actions after any htmx swap into #sounds-section
document.body.addEventListener('htmx:afterSettle', function (event) {
    if (event.detail.target && event.detail.target.id === 'sounds-section') {
        initializeObjectSelectorActions(document, store);
    }
});
