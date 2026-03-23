import { dismissModal, handleGenericModal } from '../components/modal';
import {
  initializeObjectSelector,
  updateObjectSelectorDataProperties,
} from '../components/objectSelector';
import { serializedIdListToIntList, combineIdsLists } from '../utils/data';

const prepareAddSoundsModalAndFields = container => {
  const addSoundsButtons = [
    ...container.querySelectorAll(`[data-toggle^="add-sounds-modal"]`),
  ];
  addSoundsButtons.forEach(addSoundsButton => {
    const removeSoundsButton = addSoundsButton.nextElementSibling;
    removeSoundsButton.disabled = true;

    const selectedSoundsDestinationElement =
      addSoundsButton.parentNode.parentNode.querySelector(
        '.bw-object-selector-container[data-type="sounds"]'
      );
    initializeObjectSelector(selectedSoundsDestinationElement, element => {
      removeSoundsButton.disabled = element.dataset.selectedIds == '';
    });

    const soundsInput =
      selectedSoundsDestinationElement.parentNode.parentNode.getElementsByTagName(
        'input'
      )[0];
    if (soundsInput.disabled) {
      addSoundsButton.disabled = true;
      const checkboxes = selectedSoundsDestinationElement.querySelectorAll(
        'span.bw-checkbox-container'
      );
      checkboxes.forEach(checkbox => {
        checkbox.remove();
      });
    }

    const soundsLabel =
      selectedSoundsDestinationElement.parentNode.parentNode.getElementsByTagName(
        'label'
      )[0];
    const itemCountElementInLabel =
      soundsLabel === (null || undefined)
        ? null
        : soundsLabel.querySelector('#element-count');

    const maxSounds = selectedSoundsDestinationElement.dataset.maxElements;
    const maxSoundsHelpText =
      selectedSoundsDestinationElement.parentNode.parentNode.getElementsByClassName(
        'helptext'
      )[0];
    if (maxSounds !== 'None') {
      if (soundsInput.value.split(',').length >= maxSounds) {
        addSoundsButton.disabled = true;
        maxSoundsHelpText.style.display = 'block';
      }
    }

    removeSoundsButton.addEventListener('click', evt => {
      evt.preventDefault();
      const soundCheckboxes =
        selectedSoundsDestinationElement.querySelectorAll('input.bw-checkbox');
      soundCheckboxes.forEach(checkbox => {
        if (checkbox.checked) {
          checkbox.closest('.bw-selectable-object').parentNode.remove();
        }
      });
      updateObjectSelectorDataProperties(selectedSoundsDestinationElement);
      const selectedSoundsHiddenInput = document.getElementById(
        addSoundsButton.dataset.selectedSoundsHiddenInputId
      );
      selectedSoundsHiddenInput.value =
        selectedSoundsDestinationElement.dataset.unselectedIds;
      if (
        maxSounds !== 'None' &&
        selectedSoundsHiddenInput.value.split(',').length < maxSounds
      ) {
        addSoundsButton.disabled = false;
        maxSoundsHelpText.style.display = 'none';
      }
      if (itemCountElementInLabel) {
        itemCountElementInLabel.innerHTML =
          selectedSoundsDestinationElement.children.length;
      }
      removeSoundsButton.disabled = true;
    });

    addSoundsButton.addEventListener('click', evt => {
      evt.preventDefault();
      const getExcludeIds = () => combineIdsLists(
        serializedIdListToIntList(selectedSoundsDestinationElement.dataset.selectedIds),
        serializedIdListToIntList(selectedSoundsDestinationElement.dataset.unselectedIds)
      ).join(',');
      openAddSoundsModal(
        'addSoundsModal',
        addSoundsButton.dataset.modalUrl,
        addSoundsButton.dataset.modalUrl,
        getExcludeIds,
        modalContainer => {
          const objectSelectorElement = modalContainer.getElementsByClassName(
            'bw-object-selector-container'
          )[0];
          const selectableSoundElements = [
            ...modalContainer.getElementsByClassName('bw-selectable-object'),
          ];
          selectableSoundElements.forEach(element => {
            const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
            if (checkbox.checked) {
              const clonedCheckbox = checkbox.cloneNode();
              delete clonedCheckbox.dataset.initialized;
              clonedCheckbox.checked = false;
              checkbox.parentNode.replaceChild(clonedCheckbox, checkbox);
              element.classList.remove('selected');
              selectedSoundsDestinationElement.appendChild(element.parentNode);
            }
          });
          const selectedSoundsHiddenInput = document.getElementById(
            addSoundsButton.dataset.selectedSoundsHiddenInputId
          );
          const currentSoundIds = serializedIdListToIntList(
            selectedSoundsHiddenInput.value
          );
          const newSoundIds = serializedIdListToIntList(
            objectSelectorElement.dataset.selectedIds
          );
          const combinedIds = combineIdsLists(currentSoundIds, newSoundIds);
          selectedSoundsHiddenInput.value = combinedIds.join(',');
          if (
            maxSounds !== 'None' &&
            selectedSoundsHiddenInput.value.split(',').length >= maxSounds
          ) {
            addSoundsButton.disabled = true;
            maxSoundsHelpText.style.display = 'block';
          }
          if (itemCountElementInLabel) {
            itemCountElementInLabel.innerHTML =
              selectedSoundsDestinationElement.children.length;
          }
          initializeObjectSelector(
            selectedSoundsDestinationElement,
            element => {
              removeSoundsButton.disabled = element.dataset.selectedIds == '';
            }
          );
        }
      );
    });
  });
};

const openAddSoundsModal = (modalId, modalUrl, url, getExcludeIds, onSoundsConfirmed) => {
    handleGenericModal(url, (modalContainer) => {
        const inputElement = modalContainer.getElementsByTagName('input')[0];
        inputElement.addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                const baseUrl = modalUrl.split('?')[0];
                const excludeIds = getExcludeIds();
                openAddSoundsModal(modalId, modalUrl, `${baseUrl}?q=${inputElement.value}&exclude=${excludeIds}`, getExcludeIds, onSoundsConfirmed);
            }
        });

        const objectSelectorElement = modalContainer.getElementsByClassName('bw-object-selector-container')[0];
        const addSelectedSoundsButton = modalContainer.getElementsByTagName('button')[0];
        addSelectedSoundsButton.disabled = true;
        initializeObjectSelector(objectSelectorElement, (element) => {
            addSelectedSoundsButton.disabled = element.dataset.selectedIds == ""
        });

        addSelectedSoundsButton.addEventListener('click', () => {
            onSoundsConfirmed(modalContainer);
            dismissModal(modalId);
        });
    }, undefined, true, true);
}

function extractSoundFromModal(card, soundId) {
    const fallback = {
        id: soundId, name: `Sound ${soundId}`, username: '', user_id: 0,
        duration: 0, samplerate: 44100, created: '', date_added: new Date().toISOString(), description: '',
    };
    const player = card.querySelector('.bw-player');
    if (!player) return fallback;

    const descEl = card.querySelector('.bw-player__description-height');
    return {
        id: soundId,
        name: player.dataset.title || fallback.name,
        username: player.dataset.username || '',
        user_id: parseInt(player.dataset.userId, 10) || 0,
        duration: parseFloat(player.dataset.duration) || 0,
        samplerate: parseFloat(player.dataset.samplerate) || 44100,
        created: '',
        date_added: new Date().toISOString(),
        description: descEl ? descEl.textContent.trim() : '',
    };
}

const prepareAddSoundsModalDynamic = (container, getExcludeIds, onSoundsConfirmed) => {
    const addSoundsButton = container.querySelector('[data-toggle="add-sounds-modal"]');
    if (!addSoundsButton) return;

    const onConfirmed = (modalContainer) => {
        const sounds = [...modalContainer.querySelectorAll('.bw-selectable-object')]
            .reduce((acc, element) => {
                const checkbox = element.querySelector('input.bw-checkbox');
                if (checkbox && checkbox.checked) {
                    acc.push(extractSoundFromModal(element, parseInt(checkbox.dataset.objectId, 10)));
                }
                return acc;
            }, []);
        onSoundsConfirmed(sounds);
    };

    addSoundsButton.addEventListener('click', (evt) => {
        evt.preventDefault();
        openAddSoundsModal('addSoundsModal', addSoundsButton.dataset.modalUrl, addSoundsButton.dataset.modalUrl, getExcludeIds, onConfirmed);
    });
};

export {prepareAddSoundsModalAndFields, prepareAddSoundsModalDynamic};
