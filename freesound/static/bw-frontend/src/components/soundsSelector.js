import debounce from 'lodash.debounce';

const updateSoundsSelectorDataProperties = element => {
    const soundCheckboxes = element.querySelectorAll('input.bw-checkbox');
    const selectedIds = [];
    const unselectedIds = [];
    soundCheckboxes.forEach(checkbox => {
        if (checkbox.checked) {
            selectedIds.push(checkbox.dataset.soundId);    
        } else {
            unselectedIds.push(checkbox.dataset.soundId);    
        } 
    });
    element.dataset.selectedIds = selectedIds.join(',');
    element.dataset.unselectedIds = unselectedIds.join(',');
}

const debouncedUpdateSoundsSelectorDataProperties = debounce(updateSoundsSelectorDataProperties, 100, {'trailing': true})

const selectableSoundElements = [...document.getElementsByClassName('bw-selectable-sound')];
selectableSoundElements.forEach( element => {
    debouncedUpdateSoundsSelectorDataProperties(element.parentNode.parentNode);
    const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
    checkbox.addEventListener('change', evt => {
        if (checkbox.checked) {
            element.classList.add('selected');    
        } else {
            element.classList.remove('selected');
        }
        debouncedUpdateSoundsSelectorDataProperties(element.parentNode.parentNode);
    });
});
