import debounce from 'lodash.debounce';

const updateSoundsSelectorDataProperties = (selectorElement, callback) => {
    const soundCheckboxes = selectorElement.querySelectorAll('input.bw-checkbox');
    const selectedIds = [];
    const unselectedIds = [];
    soundCheckboxes.forEach(checkbox => {
        if (checkbox.checked) {
            selectedIds.push(checkbox.dataset.soundId);    
        } else {
            unselectedIds.push(checkbox.dataset.soundId);    
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
    if (selectorElement.dataset.initialized != true){
        selectorElement.dataset.initialized = true;  // Avoid re-initializing multiple times the same object
        const debouncedOnChangeCallback = debounce(onChangeCallback);
        const selectableSoundElements = [...selectorElement.getElementsByClassName('bw-selectable-sound')];
        selectableSoundElements.forEach( element => {
            debouncedUpdateSoundsSelectorDataProperties(element.parentNode.parentNode);
            const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
            checkbox.addEventListener('change', evt => {
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
export {initializeSoundSelector};
