import {initializeSoundSelector} from '../components/soundsSelector'
import {handleModal} from "../components/modal";

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
            editSelectedSoundsButton.disabled = element.dataset.selectedIds === "";
            editSelectedSoundsButton.closest('form').querySelector('input[name="sound-ids"]').value = element.dataset.selectedIds;
        }
        if (removeSelectedSoundsButton !== null){
            removeSelectedSoundsButton.disabled = element.dataset.selectedIds === "";
        }
        if (reprocessSelectedSoundsButton !== null){
            reprocessSelectedSoundsButton.disabled = element.dataset.selectedIds === "";
            reprocessSelectedSoundsButton.closest('form').querySelector('input[name="sound-ids"]').value = element.dataset.selectedIds;
        }
        if (describeSelectedSoundsButton !== null){
            describeSelectedSoundsButton.disabled = element.dataset.selectedIds === "";
        }
    })
});

var sortByElement = document.getElementById('sort-by');
if (sortByElement !== null){
    sortByElement.addEventListener('change', function() {
        sortByElement.closest('form').submit();
    })
}

const describeFileCheckboxesWrapper = document.getElementById("describe-file-checkboxes");
const describeFilesForm = document.getElementById("fileform");

const noCheckboxSelected = describeFileCheckboxes => {
    let numChecked = 0;
    describeFileCheckboxes.forEach(checkboxElement => {
        if (checkboxElement.checked) {
            numChecked += 1;
        }
    })
    return numChecked === 0;
}


const onCheckboxChanged = (checkboxElement, describeFileCheckboxes) => {
var optionInFilesForm = describeFilesForm.querySelectorAll("option[value=" + checkboxElement.name + "]")[0];
        if (checkboxElement.checked) {
            optionInFilesForm.selected = true;
        } else {
            optionInFilesForm.selected = false;
        }
        const disabled = noCheckboxSelected(describeFileCheckboxes);
        describeSelectedSoundsButton.disabled = disabled;
            removeSelectedSoundsButton.disabled = disabled;
}


if (describeFileCheckboxesWrapper !== null){
    const describeFileCheckboxes = describeFileCheckboxesWrapper.querySelectorAll('input');
    describeFileCheckboxes.forEach(checkboxElement => {
        checkboxElement.addEventListener('change', evt => {
            onCheckboxChanged(checkboxElement, describeFileCheckboxes);
        });
    });
}

if (removeSelectedSoundsButton !== null){
    removeSelectedSoundsButton.addEventListener('click', evt =>{
        evt.preventDefault();
        const confirmationModalTitle = document.getElementById('confirmationModalTitle');
        confirmationModalTitle.innerText = "Are you sure you want to remove these sounds?";
        const confirmationModalHelpText = document.getElementById('confirmationModalHelpText');
        confirmationModalHelpText.innerText = "Be aware that this action is irreversible..."
        const confirmationModalAcceptForm = document.getElementById('confirmationModalAcceptSubmitForm');
        const confirmationModalAcceptButton = confirmationModalAcceptForm.querySelectorAll('button')[0];
        confirmationModalAcceptButton.addEventListener('click', evt => {
            evt.preventDefault();
            const removeSelectedSoundsButton = document.getElementById('remove-button-hidden');
            removeSelectedSoundsButton.click();  // This will trigger submitting the form with the name of the button in it and without submit being intercepted
        })
        handleModal('confirmationModal');
    })
}

const bulkDescribeButton = document.getElementById('bulk-describe-button');
if (bulkDescribeButton !== null) {
    bulkDescribeButton.addEventListener('click', evt => {
        evt.preventDefault();
        handleModal('bulkDescribeModal');
    })
    if (bulkDescribeButton.dataset.formHasErrors !== undefined) {
        handleModal('bulkDescribeModal');
    }
}

const selectAllButton = document.getElementById('select-all');
if (selectAllButton !== null) {
    selectAllButton.addEventListener('click', evt => {
        const describeFileCheckboxes = describeFileCheckboxesWrapper.querySelectorAll('input');
        describeFileCheckboxes.forEach(checkboxElement => {
            checkboxElement.checked = true;
            onCheckboxChanged(checkboxElement, describeFileCheckboxes);
        });
    })
}

const selectNoneButton = document.getElementById('select-none');
if (selectNoneButton !== null) {
    selectNoneButton.addEventListener('click', evt => {
        const describeFileCheckboxes = describeFileCheckboxesWrapper.querySelectorAll('input');
        describeFileCheckboxes.forEach(checkboxElement => {
            checkboxElement.checked = false;
            onCheckboxChanged(checkboxElement, describeFileCheckboxes);
        });
    })
}