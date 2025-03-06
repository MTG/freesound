import {dismissModal, handleGenericModal, handleGenericModalWithForm} from "./modal";
import {showToast} from "./toast";
import {makePostRequest} from "../utils/postRequest";
import {initializeObjectSelector, updateObjectSelectorDataProperties} from "./objectSelector";
import {combineIdsLists, serializedIdListToIntList} from "../utils/data";

const saveCollectionSound = (collectionSoundUrl, data) => {

    let formData = {};
    if (data === undefined){
        formData.name = "";
        formData.collection = "";
        formData.new_collection_name = "";
        formData.use_last_collection = true;
    } else {
        formData = data;
    }
    makePostRequest(collectionSoundUrl, formData, (responseText) => {
        // Collection attribute saved successfully. Close model and show feedback
        dismissModal('collectSoundModal'); // TBC
        try {
            showToast(JSON.parse(responseText).message);
        } catch (error) {
            // If not logged in, the url will respond with a redirect and JSON parsing will fail
            showToast("You need to be logged in before using collections.")
        }
    }, () => {
        // Unexpected errors happened while processing request: close modal and show error in toast
        dismissModal('collectSoundModal');
        showToast('Some errors occurred while adding the sound to the collection.');
    });
}


const toggleNewCollectionNameDiv = (select, newCollectionNameDiv) => {
    if (select.value == '0'){
        // No category is selected, show the new category name input
        newCollectionNameDiv.classList.remove('display-none');
    } else {
        newCollectionNameDiv.classList.add('display-none');
    }
}


const initCollectionFormModal = (soundId, collectionSoundUrl) => {
    
    // Modify the form structure to add a "Category" label inline with the select dropdown
    const modalContainer = document.getElementById('collectSoundModal');
    const selectElement = modalContainer.getElementsByTagName('select')[0];
    const wrapper = document.createElement('div');
    wrapper.style = 'display:inline-block;';
    if (selectElement === undefined){
        // If no select element, the modal has probably loaded for an unauthenticated user
        return;
    }
    selectElement.parentNode.insertBefore(wrapper, selectElement.parentNode.firstChild);
    const label = document.createElement('div');
    label.innerHTML = "Select a collection:"
    label.classList.add('text-grey');
    wrapper.appendChild(label)
    wrapper.appendChild(selectElement)

    const formElement = modalContainer.getElementsByTagName('form')[0];
    const buttonsInModalForm = formElement.getElementsByTagName('button');
    const saveButtonElement = buttonsInModalForm[buttonsInModalForm.length - 1];
    const categorySelectElement = document.getElementById(`id_${  soundId.toString()  }-collection`);

    const newCategoryNameElement = document.getElementById(`id_${  soundId.toString()  }-new_collection_name`);
    toggleNewCollectionNameDiv(categorySelectElement, newCategoryNameElement);
    categorySelectElement.addEventListener('change', (event) => {
    toggleNewCollectionNameDiv(categorySelectElement, newCategoryNameElement);
    });

    // Bind action to save collection attribute and prevent default submit
    saveButtonElement.addEventListener('click', (e) => {
        e.preventDefault();
        const data = {};
        data.collection = document.getElementById(`id_${  soundId.toString()  }-collection`).value;
        data.new_collection_name = document.getElementById(`id_${  soundId.toString()  }-new_collection_name`).value;
        saveCollectionSound(collectionSoundUrl, data);
    });
};

const bindCollectionModals = (container) => {
    const collectionButtons = [...container.querySelectorAll('[data-toggle="collection-modal"]')];
    collectionButtons.forEach(element => {
        if (element.dataset.alreadyBinded !== undefined){
            return;
        }
        element.dataset.alreadyBinded = true;
        element.addEventListener('click', (evt) => {
            evt.preventDefault();   
            const modalUrlSplitted = element.dataset.modalUrl.split('/');
            const soundId = parseInt(modalUrlSplitted[modalUrlSplitted.length - 2], 10);
            if (!evt.altKey) {
                handleGenericModal(element.dataset.modalUrl, () => {
                    initCollectionFormModal(soundId, element.dataset.collectionSoundUrl);
                }, undefined, true, true);
            } else {
                saveCollectionSound(element.dataset.collectionSoundUrl);
            }
        });
    });
}

// TODO: the AddMaintainerModal works really similarly to the AddSoundsModal, so maybe they could share behaviour
// However, it'd be interesting that checked users could be temporarly stored in the modal while other queries are performed
const handleAddMaintainersModal = (modalId, modalUrl, selectedMaintainersDestinationElement, onMaintainersSelectedCallback) => {
    handleGenericModalWithForm(modalUrl,(modalContainer) => {
        const inputElement = modalContainer.getElementsByTagName('input')[1];
        inputElement.addEventListener('keypress', (evt) => {
            if (evt.key === 'Enter'){
                evt.preventDefault();
                const baseUrl = modalUrl.split('?')[0];
                const maintainersIdsToExclude = combineIdsLists(serializedIdListToIntList(selectedMaintainersDestinationElement.dataset.selectedIds), serializedIdListToIntList(selectedMaintainersDestinationElement.dataset.unselectedIds)).join(',');
                console.log(maintainersIdsToExclude)
                handleAddMaintainersModal(modalId, `${baseUrl}?q=${inputElement.value}&exclude=${maintainersIdsToExclude}`, selectedMaintainersDestinationElement, onMaintainersSelectedCallback);
            }
        });

        const objectSelectorElement = modalContainer.getElementsByClassName('bw-object-selector-container')[0];
        initializeObjectSelector(objectSelectorElement, (element) => {
            addSelectedMaintainersButton.disabled = element.dataset.selectedIds == ""
        });

        const addSelectedMaintainersButton = modalContainer.getElementsByTagName('button')[0];
        addSelectedMaintainersButton.disabled = true;
        addSelectedMaintainersButton.addEventListener('click', evt => {
            evt.preventDefault();
            const selectableMaintainerElements = [...modalContainer.getElementsByClassName('bw-selectable-object')];
            selectableMaintainerElements.forEach(element => {
                const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
                if (checkbox.checked) {
                    const clonedCheckbox = checkbox.cloneNode();
                    delete(clonedCheckbox.dataset.initialized);
                    clonedCheckbox.checked = false;
                    checkbox.parentNode.replaceChild(clonedCheckbox, checkbox)
                    element.classList.remove('selected');
                    selectedMaintainersDestinationElement.appendChild(element.parentNode);
                }
            });
            onMaintainersSelectedCallback(objectSelectorElement.dataset.selectedIds)
            dismissModal(modalId)
        });
    }, undefined, showToast('Maintainers added successfully'), showToast('There were some errors handling the modal'), true, true, undefined, false);
};

const prepareAddMaintainersModalAndFields = (container) => {
    // select all buttons with a toggle that triggers the maintainers modal
    const addMaintainersButtons = [...container.querySelectorAll('[data-toggle="add-maintainers-modal"]')];
    // for each button, assign the next sibling to the remove maintainer button and disable it (since nothing will be selected by default)
    addMaintainersButtons.forEach(addMaintainersButton => {
        const removeMaintainersButton = addMaintainersButton.nextElementSibling;
        removeMaintainersButton.disabled = true;

        const selectedMaintainersDestinationElement = addMaintainersButton.parentNode.parentNode.getElementsByClassName('bw-object-selector-container')[0];
        initializeObjectSelector(selectedMaintainersDestinationElement, (element) => {
            removeMaintainersButton.disabled = element.dataset.selectedIds == "" 
        })

        const maintainersInput = selectedMaintainersDestinationElement.parentNode.parentNode.getElementsByTagName('input')[0];
        if(maintainersInput.getAttribute('readonly') !== null){
            addMaintainersButton.disabled = true
            const checkboxes = selectedMaintainersDestinationElement.querySelectorAll('span.bw-checkbox-container');
            checkboxes.forEach(checkbox => {
                console.log(checkbox)
                checkbox.remove()
            })
        }

        removeMaintainersButton.addEventListener('click', (evt) => {
            evt.preventDefault();
            const maintainerCheckboxes = selectedMaintainersDestinationElement.querySelectorAll('input.bw-checkbox');
            maintainerCheckboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    checkbox.closest('.bw-selectable-object').parentNode.remove();
                }
            });
            updateObjectSelectorDataProperties(selectedMaintainersDestinationElement);
            const selectedMaintainersHiddenInput = document.getElementById(addMaintainersButton.dataset.selectedMaintainersHiddenInputId);
            selectedMaintainersHiddenInput.value = selectedMaintainersDestinationElement.dataset.unselectedIds;
            removeMaintainersButton.disabled = true;
        });

        addMaintainersButton.addEventListener('click', (evt) => {
            evt.preventDefault();
            handleAddMaintainersModal('addMaintainersModal', addMaintainersButton.dataset.modalUrl, selectedMaintainersDestinationElement, (selectedMaintainersIds) => {
                const selectedMaintainersHiddenInput = document.getElementById(addMaintainersButton.dataset.selectedMaintainersHiddenInputId);
                const currentMaintainersIds = serializedIdListToIntList(selectedMaintainersHiddenInput.value);
                const newMaintainersIds = serializedIdListToIntList(selectedMaintainersIds);
                const combinedIds = combineIdsLists(currentMaintainersIds, newMaintainersIds)
                selectedMaintainersHiddenInput.value = combinedIds.join(',')
                initializeObjectSelector(selectedMaintainersDestinationElement, (element) => {
                    removeMaintainersButton.disabled = element.dataset.selectedIds == ""
                });
            });
        });
    })};

export { bindCollectionModals, prepareAddMaintainersModalAndFields };
