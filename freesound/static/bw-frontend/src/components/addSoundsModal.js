import {dismissModal, handleGenericModal} from "../components/modal"
import {initializeObjectSelector, updateObjectSelectorDataProperties} from '../components/objectSelector'
import {serializedIdListToIntList, combineIdsLists} from "../utils/data"

const handleAddSoundsModal = (modalId, modalUrl, selectedSoundsDestinationElement, onSoundsSelectedCallback) => {
    handleGenericModal(modalUrl, (modalContainer) => {        
        const inputElement = modalContainer.getElementsByTagName('input')[0];
        inputElement.addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                const baseUrl = modalUrl.split('?')[0];
                const soundIdsToExclude = combineIdsLists(serializedIdListToIntList(selectedSoundsDestinationElement.dataset.selectedIds), serializedIdListToIntList(selectedSoundsDestinationElement.dataset.unselectedIds)).join(',');
                handleAddSoundsModal(modalId, `${baseUrl}?q=${inputElement.value}&exclude=${soundIdsToExclude}`, selectedSoundsDestinationElement, onSoundsSelectedCallback);
            }
        });

        const objectSelectorElement = modalContainer.getElementsByClassName('bw-object-selector-container')[0];
        initializeObjectSelector(objectSelectorElement, (element) => {
            addSelectedSoundsButton.disabled = element.dataset.selectedIds == ""
        });

        const addSelectedSoundsButton = modalContainer.getElementsByTagName('button')[0];
        addSelectedSoundsButton.disabled = true;
        addSelectedSoundsButton.addEventListener('click', evt => {
            const selectableSoundElements = [...modalContainer.getElementsByClassName('bw-selectable-object')];
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
            onSoundsSelectedCallback(objectSelectorElement.dataset.selectedIds);
            dismissModal(modalId);
        });
    }, undefined, true, true);
}

const prepareAddSoundsModalAndFields = (container) => {
    const addSoundsButtons = [...container.querySelectorAll(`[data-toggle^="add-sounds-modal"]`)];
    addSoundsButtons.forEach(addSoundsButton => {
        const removeSoundsButton = addSoundsButton.nextElementSibling;
        removeSoundsButton.disabled = true;

        const selectedSoundsDestinationElement = addSoundsButton.parentNode.parentNode.querySelector('.bw-object-selector-container[data-type="sounds"]');
        initializeObjectSelector(selectedSoundsDestinationElement, (element) => {
            removeSoundsButton.disabled = element.dataset.selectedIds == ""
        });

        const soundsInput = selectedSoundsDestinationElement.parentNode.parentNode.getElementsByTagName('input')[0];
        if(soundsInput.disabled){
            addSoundsButton.disabled = true
            const checkboxes = selectedSoundsDestinationElement.querySelectorAll('span.bw-checkbox-container');
            checkboxes.forEach(checkbox => {
                checkbox.remove()
            })
        }

        const soundsLabel = selectedSoundsDestinationElement.parentNode.parentNode.getElementsByTagName('label')[0];
        const itemCountElementInLabel = soundsLabel === (null || undefined) ? null : soundsLabel.querySelector('#element-count');
        
        const maxSounds = selectedSoundsDestinationElement.dataset.maxElements;
        const maxSoundsHelpText = selectedSoundsDestinationElement.parentNode.parentNode.getElementsByClassName('helptext')[0]
        if(maxSounds !== "None"){
            if (soundsInput.value.split(',').length >= maxSounds){
                addSoundsButton.disabled = true
                maxSoundsHelpText.style.display = 'block';
            }
        }

        removeSoundsButton.addEventListener('click', (evt) => {
            evt.preventDefault();
            const soundCheckboxes = selectedSoundsDestinationElement.querySelectorAll('input.bw-checkbox');
            soundCheckboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    checkbox.closest('.bw-selectable-object').parentNode.remove();
                }
            });
            updateObjectSelectorDataProperties(selectedSoundsDestinationElement);
            const selectedSoundsHiddenInput = document.getElementById(addSoundsButton.dataset.selectedSoundsHiddenInputId);
            selectedSoundsHiddenInput.value = selectedSoundsDestinationElement.dataset.unselectedIds;
            if(maxSounds !== "None" && selectedSoundsHiddenInput.value.split(',').length < maxSounds){
                addSoundsButton.disabled = false;
                maxSoundsHelpText.style.display = 'none';
            }
            if (itemCountElementInLabel){
                itemCountElementInLabel.innerHTML = selectedSoundsDestinationElement.children.length}
            removeSoundsButton.disabled = true;
        });

        addSoundsButton.addEventListener('click', (evt) => {
            evt.preventDefault();
            handleAddSoundsModal('addSoundsModal', addSoundsButton.dataset.modalUrl, selectedSoundsDestinationElement, (selectedSoundIds) => {
                const selectedSoundsHiddenInput = document.getElementById(addSoundsButton.dataset.selectedSoundsHiddenInputId);
                const currentSoundIds = serializedIdListToIntList(selectedSoundsHiddenInput.value);
                const newSoundIds = serializedIdListToIntList(selectedSoundIds);
                const combinedIds = combineIdsLists(currentSoundIds, newSoundIds);
                selectedSoundsHiddenInput.value = combinedIds.join(',');
                if(maxSounds !== "None" && selectedSoundsHiddenInput.value.split(',').length >= maxSounds){
                    addSoundsButton.disabled = true;
                    maxSoundsHelpText.style.display = 'block';
                }
                if (itemCountElementInLabel){
                    itemCountElementInLabel.innerHTML = selectedSoundsDestinationElement.children.length}
                initializeObjectSelector(selectedSoundsDestinationElement, (element) => {
                    removeSoundsButton.disabled = element.dataset.selectedIds == ""
                });
            });
            
        }); 
    });
}

export {prepareAddSoundsModalAndFields};
