import {handleDismissModal, handleGenericModal} from "../components/modal"
import {stopAllPlayers} from '../components/player/utils'
import {createPlayer} from '../components/player/player-ui'
import {initializeSoundSelector, updateSoundsSelectorDataProperties} from '../components/soundsSelector'
import addCheckboxVisibleElements from "../components/checkbox"
import {serializedIdListToIntList, combineIdsLists} from "../utils/data"

const openAddSoundsModal = (modalId, modalUrl, selectedSoundsDestinationElement, onSoundsSelectedCallback) => {
    handleGenericModal(modalUrl, () => {
        const modalWrapper = document.getElementById('genericModalWrapper');
        
        const players = [...modalWrapper.getElementsByClassName('bw-player')]
        players.forEach(createPlayer)
        
        addCheckboxVisibleElements()

        const inputElement = modalWrapper.getElementsByTagName('input')[0];
        inputElement.addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                const baseUrl = modalUrl.split('?')[0]
                openAddSoundsModal(modalId, `${baseUrl}?q=${inputElement.value}`, selectedSoundsDestinationElement, onSoundsSelectedCallback);
            }
        });

        const soundSelectorElement = modalWrapper.getElementsByClassName('bw-sounds-selector-container')[0];
        initializeSoundSelector(soundSelectorElement, (element) => {
            addSelectedSoundsButton.disabled = element.dataset.selectedIds == ""
        });

        const addSelectedSoundsButton = modalWrapper.getElementsByTagName('button')[0];
        addSelectedSoundsButton.disabled = true;
        addSelectedSoundsButton.addEventListener('click', evt => {
            const selectableSoundElements = [...modalWrapper.getElementsByClassName('bw-selectable-sound')];
            selectableSoundElements.forEach( element => {
                const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
                if (checkbox.checked) {
                    const clonedCheckbox = checkbox.cloneNode();  // Cloning the node will remove the event listeners which refer to the "old" sound selector
                    delete(clonedCheckbox.dataset.initialized); // This will force re-initialize the element when added to the new sounds selector
                    clonedCheckbox.checked = false;
                    checkbox.parentNode.replaceChild(clonedCheckbox, checkbox);
                    element.classList.remove('selected');
                    selectedSoundsDestinationElement.appendChild(element.parentNode);
                }
            });
            onSoundsSelectedCallback(soundSelectorElement.dataset.selectedIds);
            handleDismissModal(modalId);
        });
    }, () => {
        // Stop all players that could be being played inside the modal
        stopAllPlayers();
    }, true, true);
}

const prepareAddSoundsModalAndFields = () => {
    const addSoundsButtons = [...document.querySelectorAll(`[data-toggle^="add-sounds-modal"]`)];
    addSoundsButtons.forEach(addSoundsButton => {
        const removeSoundsButton = addSoundsButton.nextElementSibling;
        removeSoundsButton.disabled = true;

        const selectedSoundsDestinationElement = addSoundsButton.parentNode.parentNode.getElementsByClassName('bw-sounds-selector-container')[0];
        initializeSoundSelector(selectedSoundsDestinationElement, (element) => {
            removeSoundsButton.disabled = element.dataset.selectedIds == ""
        });

        removeSoundsButton.addEventListener('click', (evt) => {
            evt.preventDefault();
            const soundCheckboxes = selectedSoundsDestinationElement.querySelectorAll('input.bw-checkbox');
            soundCheckboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    checkbox.closest('.bw-selectable-sound').parentNode.remove();
                }
            });
            updateSoundsSelectorDataProperties(selectedSoundsDestinationElement);
            const selectedSoundsHiddenInput = document.getElementById(addSoundsButton.dataset.selectedSoundsHiddenInputId);
            selectedSoundsHiddenInput.value = selectedSoundsDestinationElement.dataset.unselectedIds;
            removeSoundsButton.disabled = true;
        });

        addSoundsButton.addEventListener('click', (evt) => {
            evt.preventDefault();
            openAddSoundsModal('addSoundsModal', addSoundsButton.dataset.modalUrl, selectedSoundsDestinationElement, (selectedSoundIds) => {
                const selectedSoundsHiddenInput = document.getElementById(addSoundsButton.dataset.selectedSoundsHiddenInputId);
                const currentSoundIds = serializedIdListToIntList(selectedSoundsHiddenInput.value);
                const newSoundIds = serializedIdListToIntList(selectedSoundIds);
                const combinedIds = combineIdsLists(currentSoundIds, newSoundIds);
                selectedSoundsHiddenInput.value = combinedIds.join(',');
                initializeSoundSelector(selectedSoundsDestinationElement, (element) => {
                    removeSoundsButton.disabled = element.dataset.selectedIds == ""
                });
        
            });
        }); 
    });
}

export {prepareAddSoundsModalAndFields};
