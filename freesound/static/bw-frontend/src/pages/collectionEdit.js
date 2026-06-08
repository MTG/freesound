import { prepareAddMaintainersModalAndFields } from '../components/collectionsModal';
import { prepareAddSoundsModalDynamic } from '../components/addSoundsModal';
import { SoundStateStore } from '../utils/soundStateStore';
import { SoundGridEditor } from '../utils/soundGridEditor';

const soundsData = JSON.parse(
  document.getElementById('sounds-data').textContent
);
const pageConfig = JSON.parse(
  document.getElementById('page-config').textContent
);
const initialFeaturedIds = soundsData
  .filter(s => Number.isInteger(s.featured_order))
  .sort((a, b) => a.featured_order - b.featured_order)
  .map(s => s.id);

const store = new SoundStateStore(['added', 'remove', 'featured'], {
  maxFeatured: pageConfig.max_featured || Infinity,
}).load(soundsData, { featured: initialFeaturedIds });

const featuredCountEl = document.getElementById('featured-count');

const editor = new SoundGridEditor({
  store,
  countEl: document.getElementById('element-count'),
  searchInput: document.getElementById('edit-collection-search'),
});

const updateFeaturedUI = () => {
  const count = store.featuredCount();
  const atLimit = count >= (pageConfig.max_featured || Infinity);

  if (featuredCountEl) featuredCountEl.textContent = count;

  // Disable/enable non-featured buttons across the grid
  const grid = document.getElementById('sounds-grid');
  if (grid) {
    grid.querySelectorAll('[data-action="featured"]').forEach(btn => {
      const container = btn.closest('[data-object-id]');
      const id = container ? parseInt(container.dataset.objectId, 10) : NaN;
      const isFeatured = store.has(id, 'featured');
      const isRemoved = store.has(id, 'remove');
      btn.disabled = isRemoved || (!isFeatured && atLimit);
    });
  }
};
updateFeaturedUI();
store.onChange((_id, name) => {
  if (name === 'featured' || name === 'remove') updateFeaturedUI();
});
editor.onAfterSwap(updateFeaturedUI);

prepareAddMaintainersModalAndFields(document);

prepareAddSoundsModalDynamic(
  document,
  () => store.ids().join(','),
  sounds => sounds.forEach(s => store.add(s.id, s))
);

const collectionForm = document.getElementById('collection-form');
if (collectionForm) {
  collectionForm.addEventListener('submit', () => {
    const addedInput = document.getElementById('added_sound_ids');
    const removedInput = document.getElementById('removed_sound_ids');
    const featuredInput = document.getElementById('featured_sounds');

    if (addedInput)
      addedInput.value = store.idsWithAction('added', true).join(',');
    if (removedInput)
      removedInput.value = store.idsWithAction('remove').join(',');
    if (featuredInput)
      featuredInput.value = editor.featuredIdsForSubmit().join(',');
  });
}
