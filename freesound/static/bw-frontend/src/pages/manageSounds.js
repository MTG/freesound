import {initializeSoundSelector, updateSoundsSelectorDataProperties} from '../components/soundsSelector'

const editSelectedSoundsButton = document.getElementById('edit-button');
if (editSelectedSoundsButton !== null){
    editSelectedSoundsButton.disabled = true;
}

const removeSelectedSoundsButton = document.getElementById('remove-button');
if (removeSelectedSoundsButton !== null){
    removeSelectedSoundsButton.disabled = true;
}

const reprocessSelectedSoundsButton = document.getElementById('reprocess-button');
if (reprocessSelectedSoundsButton !== null){
    reprocessSelectedSoundsButton.disabled = true;
}

const describeSelectedSoundsButton = document.getElementById('describe-button');
if (describeSelectedSoundsButton !== null){
    describeSelectedSoundsButton.disabled = true;
}

const soundSelector = [...document.getElementsByClassName('bw-sounds-selector-container')];
soundSelector.forEach(selectorElement => {
    initializeSoundSelector(selectorElement, (element) => {
        if (editSelectedSoundsButton !== null){
            editSelectedSoundsButton.disabled = element.dataset.selectedIds == "";
        }
        if (removeSelectedSoundsButton !== null){
            removeSelectedSoundsButton.disabled = element.dataset.selectedIds == "";
        }
        if (reprocessSelectedSoundsButton !== null){
            reprocessSelectedSoundsButton.disabled = element.dataset.selectedIds == "";
        }
        if (describeSelectedSoundsButton !== null){
            describeSelectedSoundsButton.disabled = element.dataset.selectedIds == "";
        }
    })
});

var sortByElement = document.getElementById('sort-by');
if (sortByElement !== null){
    sortByElement.addEventListener('change', function() {
        sortByElement.closest('form').submit();
    })
}
