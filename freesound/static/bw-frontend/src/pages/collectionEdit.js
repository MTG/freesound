import {prepareAddMaintainersModalAndFields} from "../components/collectionsModal"
import { prepareAddSoundsModalAndFields } from "../components/addSoundsModal";
import {updateObjectSelectorDataProperties} from '../components/objectSelector'


const updateFeaturedHighlights = (soundSelectorContainer, featuredIds) => {
    const allSelectableObjects = soundSelectorContainer.querySelectorAll('.bw-selectable-object');
    allSelectableObjects.forEach(element => {
        const checkbox = element.querySelector('input.bw-checkbox');
        const existingLabel = element.querySelector('.featured-label');
        
        if (checkbox && featuredIds.includes(checkbox.dataset.objectId)) {
            element.classList.add('featured');
            // Add "Featured" label if not already present
            if (!existingLabel) {
                const label = document.createElement('span');
                label.className = 'featured-label';
                label.textContent = 'Featured';
                element.appendChild(label);
            }
        } else {
            element.classList.remove('featured');
            // Remove "Featured" label if present
            if (existingLabel) {
                existingLabel.remove();
            }
        }
    });
};

const prepareFeaturedSoundsButtons = (container) => {
    const setButton = container.querySelector('[data-toggle="set-featured-sounds"]');
    const removeButton = container.querySelector('[data-toggle="remove-featured-sounds"]');
    const clearAllButton = container.querySelector('[data-toggle="clear-all-featured-sounds"]');
    if (!setButton || !removeButton) return;

    const referenceButton = setButton || removeButton;
    const soundSelectorContainer = referenceButton.closest('.v-spacing-5').querySelector('.bw-object-selector-container[data-type="sounds"]');
    if (!soundSelectorContainer) return;

    // Disable selection-based buttons initially
    setButton.disabled = true;
    removeButton.disabled = true;

    const featuredSoundsInput = document.getElementById(referenceButton.dataset.featuredSoundsHiddenInputId);

    const getSelectedIds = () => (soundSelectorContainer.dataset.selectedIds || "").split(',').filter(Boolean);
    const getFeaturedIds = () => ((featuredSoundsInput && featuredSoundsInput.value) || "").split(',').filter(Boolean);

    // Update clear all button based on whether there are any featured sounds
    const updateClearAllButtonState = () => {
        if (clearAllButton) {
            clearAllButton.disabled = getFeaturedIds().length === 0;
        }
    };

    // Add change listeners directly to checkboxes (works alongside existing listeners from addSoundsModal)
    const updateButtonStates = () => {
        // Check directly from checkboxes since dataset.selectedIds may not be updated yet (debounced)
        const hasSelection = soundSelectorContainer.querySelector('input.bw-checkbox:checked') !== null;
        setButton.disabled = !hasSelection;
        removeButton.disabled = !hasSelection;
    };

    soundSelectorContainer.querySelectorAll('input.bw-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateButtonStates);
    });

    updateFeaturedHighlights(soundSelectorContainer, getFeaturedIds());
    updateClearAllButtonState();

    const updateFeatured = (ids) => {
        if (featuredSoundsInput) featuredSoundsInput.value = ids.join(',');
        updateFeaturedHighlights(soundSelectorContainer, ids);
        updateClearAllButtonState();
    };

    const clearSelection = () => {
        soundSelectorContainer.querySelectorAll('input.bw-checkbox:checked').forEach(cb => {
            cb.checked = false;
            var parent = cb.closest('.bw-selectable-object');
            if (parent) parent.classList.remove('selected');
        });
        updateObjectSelectorDataProperties(soundSelectorContainer);
        setButton.disabled = true;
        removeButton.disabled = true;
        // Dispatch change event so other listeners (e.g. from addSoundsModal) get notified
        const firstCheckbox = soundSelectorContainer.querySelector('input.bw-checkbox');
        if (firstCheckbox) {
            firstCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
        }
    };

    setButton.addEventListener('click', (e) => {
        e.preventDefault();
        const merged = [...new Set([...getFeaturedIds(), ...getSelectedIds()])];
        updateFeatured(merged);
        clearSelection();
    });

    removeButton.addEventListener('click', (e) => {
        e.preventDefault();
        const selectedIds = new Set(getSelectedIds());
        const newFeatured = selectedIds.size > 0
            ? getFeaturedIds().filter(id => !selectedIds.has(id))
            : [];
        updateFeatured(newFeatured);
        clearSelection();
    });

    if (clearAllButton) {
        clearAllButton.addEventListener('click', (e) => {
            e.preventDefault();
            updateFeatured([]);
        });
    }
};

prepareAddMaintainersModalAndFields(document);
prepareAddSoundsModalAndFields(document);
prepareFeaturedSoundsButtons(document);