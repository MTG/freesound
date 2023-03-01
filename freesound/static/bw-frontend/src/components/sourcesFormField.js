import {handleDismissModal, handleGenericModal} from "../components/modal"
import {showToast} from "../components/toast"
import {stopAllPlayers} from '../components/player/utils'
import {createPlayer} from '../components/player/player-ui'
import {initializeSoundSelector, updateSoundsSelectorDataProperties} from '../components/soundsSelector'
import addCheckboxVisibleElements from "../components/checkbox"
import {serializedIdListToIntList, combineIdsLists} from "../utils/data"

const openAddSoundSourcesModal = (modalUrl, selectedSourcesDestinationElement, onSourcesSelectedCallback) => {
    handleGenericModal(modalUrl, () => {
        const modalWrapper = document.getElementById('genericModalWrapper');
        
        const players = [...modalWrapper.getElementsByClassName('bw-player')]
        players.forEach(createPlayer)
        
        addCheckboxVisibleElements()

        const inputElement = modalWrapper.getElementsByTagName('input')[0];
        inputElement.addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                openAddSoundSourcesModal(`${modalUrl}?q=${inputElement.value}`, selectedSourcesDestinationElement, onSourcesSelectedCallback);
            }
        });

        const soundSelectorElement = modalWrapper.getElementsByClassName('bw-sounds-selector-container')[0];
        initializeSoundSelector(soundSelectorElement, (element) => {
            addSelectedSourcesButton.disabled = element.dataset.selectedIds == ""
        });

        const addSelectedSourcesButton = modalWrapper.getElementsByTagName('button')[0];
        addSelectedSourcesButton.disabled = true;
        addSelectedSourcesButton.addEventListener('click', evt => {
            showToast("Adding selected sounds as sources!");
            const selectableSoundElements = [...modalWrapper.getElementsByClassName('bw-selectable-sound')];
            selectableSoundElements.forEach( element => {
                const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
                if (checkbox.checked) {
                    const clonedCheckbox = checkbox.cloneNode();  // Cloning the node will remove the event listeners which refer to the "old" sound selector
                    delete(clonedCheckbox.dataset.initialized); // This will force re-initialize the element when added to the new sounds selector
                    clonedCheckbox.checked = false;
                    checkbox.parentNode.replaceChild(clonedCheckbox, checkbox);
                    element.classList.remove('selected');
                    selectedSourcesDestinationElement.appendChild(element.parentNode);
                }
            });
            onSourcesSelectedCallback(soundSelectorElement.dataset.selectedIds);
            handleDismissModal('editSourcesModal');
        });

    }, () => {
        // Stop all players that could be being played inside the modal
        stopAllPlayers();
    }, true, true);
}

const prepareSourcesFormFields = () => {
    const soundAddSourcesButtons = [...document.querySelectorAll('[data-toggle^="add-sources-modal"]')];
    soundAddSourcesButtons.forEach(addSourcesButton => {
        const removeSourcesButton = addSourcesButton.nextElementSibling;
        removeSourcesButton.disabled = true;

        const selectedSourcesDestinationElement = addSourcesButton.parentNode.parentNode.getElementsByClassName('bw-sounds-selector-container')[0];
        initializeSoundSelector(selectedSourcesDestinationElement, (element) => {
            removeSourcesButton.disabled = element.dataset.selectedIds == ""
        });

        removeSourcesButton.addEventListener('click', (evt) => {
            evt.preventDefault();
            const soundCheckboxes = selectedSourcesDestinationElement.querySelectorAll('input.bw-checkbox');
            soundCheckboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    checkbox.closest('.bw-selectable-sound').parentNode.remove();
                }
            });
            updateSoundsSelectorDataProperties(selectedSourcesDestinationElement);
            const sourcesHiddenInput = document.getElementsByName(`${addSourcesButton.dataset.formIdx}-sources`)[0];
            sourcesHiddenInput.value = selectedSourcesDestinationElement.dataset.unselectedIds;
            removeSourcesButton.disabled = true;
        });

        addSourcesButton.addEventListener('click', (evt) => {
            evt.preventDefault();
            openAddSoundSourcesModal(addSourcesButton.dataset.modalUrl, selectedSourcesDestinationElement, (selectedSoundIds) => {
                const sourcesHiddenInput = document.getElementsByName(`${addSourcesButton.dataset.formIdx}-sources`)[0];
                const currentSourceIds = serializedIdListToIntList(sourcesHiddenInput.value);
                const newSourceIds = serializedIdListToIntList(selectedSoundIds);
                const combinedIds = combineIdsLists(currentSourceIds, newSourceIds);
                sourcesHiddenInput.value = combinedIds.join(',');
                initializeSoundSelector(selectedSourcesDestinationElement, (element) => {
                    removeSourcesButton.disabled = element.dataset.selectedIds == ""
                });
        
            });
        }); 
    });
}

export {prepareSourcesFormFields}
