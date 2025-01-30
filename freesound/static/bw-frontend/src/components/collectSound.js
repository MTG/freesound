import {dismissModal, handleGenericModal} from "./modal";
import {showToast} from "./toast";
import {makePostRequest} from "../utils/postRequest";

const saveCollectionSound = (collectSoundUrl, data, modalType) => {

    let formData = {};
    if (data === undefined){
        formData.name = "";
        formData.collection = "";
        formData.new_collection_name = "";
        formData.use_last_collection = true;
    } else {
        formData = data;
    }
    makePostRequest(collectSoundUrl, formData, (responseText) => {
        // CollectionSound saved successfully. Close model and show feedback
        dismissModal(modalType); // TBC
        try {
            showToast(JSON.parse(responseText).message);
        } catch (error) {
            // If not logged in, the url will respond with a redirect and JSON parsing will fail
            showToast("You need to be logged in before collecting sounds.")
        }
    }, () => {
        // Unexpected errors happened while processing request: close modal and show error in toast
        dismissModal(modalType);
        showToast('Some errors occurred while collecting the sound.');
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


const initCollectSoundFormModal = (soundId, collectSoundUrl, modalType) => {
    
    // Modify the form structure to add a "Category" label inline with the select dropdown
    const modalContainer = document.getElementById(modalType);
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
    // New collection is not allowed for addMaintainerModal
    if (modalType=='collectSoundModal'){
        const newCategoryNameElement = document.getElementById(`id_${  soundId.toString()  }-new_collection_name`);
        toggleNewCollectionNameDiv(categorySelectElement, newCategoryNameElement);
        categorySelectElement.addEventListener('change', (event) => {
            toggleNewCollectionNameDiv(categorySelectElement, newCategoryNameElement);
        });
    }
    

    // Bind action to save collectionSound in "add sound to collection button" (and prevent default form submit)
    saveButtonElement.addEventListener('click', (e) => {
        e.preventDefault();
        const data = {};
        data.collection = document.getElementById(`id_${  soundId.toString()  }-collection`).value;
        if(modalType=='collectSoundModal'){
            data.new_collection_name = document.getElementById(`id_${  soundId.toString()  }-new_collection_name`).value;
        }
        saveCollectionSound(collectSoundUrl, data, modalType);
    });
};

const bindCollectSoundModals = (container) => {
    const collectSoundButtons = [...container.querySelectorAll('[data-toggle="collect-modal"]')];
    collectSoundButtons.forEach(element => {
        if (element.dataset.alreadyBinded !== undefined){
            return;
        }
        element.dataset.alreadyBinded = true;
        element.addEventListener('click', (evt) => {
            evt.preventDefault();   
            const modalUrlSplitted = element.dataset.modalUrl.split('/');
            const soundId = parseInt(modalUrlSplitted[modalUrlSplitted.length - 2], 10);
            const modalType = element.dataset.modalType;
            if (!evt.altKey) {
                handleGenericModal(element.dataset.modalUrl, () => {
                    initCollectSoundFormModal(soundId, element.dataset.collectSoundUrl, modalType);
                }, undefined, true, true);
            } else {
                saveCollectionSound(element.dataset.collectSoundUrl);
            }
        });
    });
}

export { bindCollectSoundModals };
