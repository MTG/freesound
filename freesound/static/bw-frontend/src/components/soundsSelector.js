import debounce from 'lodash.debounce';

const updateSoundsSelectorDataProperties = (selectorElement, callback) => {
    const soundCheckboxes = selectorElement.querySelectorAll('input.bw-checkbox');
    const selectedIds = [];
    const unselectedIds = [];
    soundCheckboxes.forEach(checkbox => {
        if (checkbox.checked) {
            selectedIds.push(checkbox.dataset.objectId);    
        } else {
            unselectedIds.push(checkbox.dataset.objectId);    
        } 
    });
    selectorElement.dataset.selectedIds = selectedIds.join(',');
    selectorElement.dataset.unselectedIds = unselectedIds.join(',');
    if (callback !== undefined){
        callback(selectorElement);
    }
}

const debouncedUpdateSoundsSelectorDataProperties = debounce(updateSoundsSelectorDataProperties, 100, {'trailing': true})


const initializeSoundSelector = (selectorElement, onChangeCallback) => {
    // Note this can be safely called multiple times on the same selectorElement as event listeners will only be added if not already added
    // Also note that if called multiple times, only the first passed onChangeCallback will remain active 
    const debouncedOnChangeCallback = debounce(onChangeCallback);
    const selectableSoundElements = [...selectorElement.getElementsByClassName('bw-selectable-sound')];
    selectableSoundElements.forEach( element => {
        const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
        if (checkbox.dataset.initialized === undefined){
            debouncedUpdateSoundsSelectorDataProperties(element.parentNode.parentNode);
            checkbox.dataset.initialized = true;  // Avoid re-initializing multiple times the same object
            checkbox.addEventListener('change', evt => {
                if (checkbox.checked) {
                    element.classList.add('selected');    
                } else {
                    element.classList.remove('selected');
                }
                debouncedUpdateSoundsSelectorDataProperties(element.parentNode.parentNode, debouncedOnChangeCallback);
            });
        }
    });

    // Configure select all/none buttons
    const selectAllSelectNoneButtons = selectorElement.parentNode.getElementsByClassName('select-button');
    if (selectAllSelectNoneButtons.length == 2){
        const selectAllButton = selectAllSelectNoneButtons[0];
        const selectNoneButton = selectAllSelectNoneButtons[1];
        selectAllButton.addEventListener('click', evt => {
            selectableSoundElements.forEach(element => {
                const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
                checkbox.checked = true;
                if (checkbox.checked) {
                    element.classList.add('selected');    
                } else {
                    element.classList.remove('selected');
                }
                debouncedUpdateSoundsSelectorDataProperties(element.parentNode.parentNode, debouncedOnChangeCallback);
            });
        });
        selectNoneButton.addEventListener('click', evt => {
            selectableSoundElements.forEach(element => {
                const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
                checkbox.checked = false;
                if (checkbox.checked) {
                    element.classList.add('selected');    
                } else {
                    element.classList.remove('selected');
                }
                debouncedUpdateSoundsSelectorDataProperties(element.parentNode.parentNode, debouncedOnChangeCallback);
            });
        });
    }
    
}
export {initializeSoundSelector, updateSoundsSelectorDataProperties};
