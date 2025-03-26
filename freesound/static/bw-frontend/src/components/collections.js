import {dismissModal, handleGenericModal, handleGenericModalWithForm} from "./modal";
import {showToast} from "./toast";
import { initializeStuffInContainer } from "../utils/initHelper";
import {initializeObjectSelector, updateObjectSelectorDataProperties} from "./objectSelector";
import {combineIdsLists, serializedIdListToIntList} from "../utils/data";

const toggleNewCollectionNameDiv = (select, newCollectionNameDiv) => {
    if (select.value == '0'){
        // No category is selected, show the new category name input
        newCollectionNameDiv.classList.remove('display-none');
    } else {
        newCollectionNameDiv.classList.add('display-none');
    }
}


const initCollectionFormModal = () => {
    
    // Modify the form structure to add a "Category" label inline with the select dropdown
    const modalContainer = document.getElementById('collectSoundModal');
    // To display the selector in case of an error in form, the following function is needed, despite it being called in
    // handleGenericModal. TODO: this needs an improvement so it's only called when necessary
    initializeStuffInContainer(modalContainer, false, false);
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

    const categorySelectElement = document.getElementById('id_collection');
    const newCategoryNameElement = document.getElementById('id_new_collection_name');
    toggleNewCollectionNameDiv(categorySelectElement, newCategoryNameElement);
    categorySelectElement.addEventListener('change', (event) => {
    toggleNewCollectionNameDiv(categorySelectElement, newCategoryNameElement);
});}

const bindCollectionModals = (container) => {
    const collectionButtons = [...container.querySelectorAll('[data-toggle="collection-modal"]')];
    collectionButtons.forEach(element => {
        if (element.dataset.alreadyBinded !== undefined){
            return;
        }
        element.dataset.alreadyBinded = true;
        element.addEventListener('click', (evt) => {
            evt.preventDefault();   
            const modalUrlSplitted = element.dataset.modalContentUrl.split('/')
            const soundId = parseInt(modalUrlSplitted[modalUrlSplitted.length - 3], 10)
            if (!evt.altKey) {
                handleGenericModalWithForm(element.dataset.modalContentUrl, () => {
                    initCollectionFormModal(soundId, element.dataset.modalContentUrl);
                }, undefined, (req) => {showToast(JSON.parse(req.responseText).message);}, () => {showToast('There were errors processing the form...');}, true, true, undefined, false);
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
                handleAddMaintainersModal(modalId, `${baseUrl}?q=${inputElement.value}`, selectedMaintainersDestinationElement, onMaintainersSelectedCallback);
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
        
        const selectedMaintainersDestinationElement = addMaintainersButton.parentNode.parentNode.querySelector('.bw-object-selector-container[data-type="users"]');
        /*
        USEFUL NOTES AFTER DEBUGGING:
        
        The function updateObjectSelectorDataProperties in charge of defining the selectedIds and unselectedIds for each
        selector does not work for maintainers. Instead it is only triggered once the user interacts with a maintainer checkbox.
        Data might get overwritten as this works simultaneously with addSoundsModal.js file. The thing is that in
        updateObjectSelectorDataProperties, the "call stack" states that originally, the function is called from here (line 175).
        Therefore, the definition of selectedMaintainersDestinationElement somehow is wrong or confused with the selectedSoundsDestinationElement.
        I tried to filter this using the above queryselector but it does not work. I guess this might have something to do with the file
        collectionEdit.js.
        */
        initializeObjectSelector(selectedMaintainersDestinationElement, (element) => {
            removeMaintainersButton.disabled = element.dataset.selectedIds == "" 
        })


        const maintainersInput = selectedMaintainersDestinationElement.parentNode.parentNode.getElementsByTagName('input')[0];
        if(maintainersInput.disabled !== false){
            addMaintainersButton.disabled = true;
            addMaintainersButton.nextElementSibling.remove();
            addMaintainersButton.remove();
            const checkboxes = selectedMaintainersDestinationElement.querySelectorAll('span.bw-checkbox-container');
            checkboxes.forEach(checkbox => {
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
