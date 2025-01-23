import {dismissModal, handleGenericModal} from "./modal";
import {showToast} from "./toast";
import {makePostRequest} from "../utils/postRequest";

const saveCollectionSound = (collectSoundUrl, data) => {

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
        dismissModal(`collectSoundModal`); // TBC
        try {
            showToast(JSON.parse(responseText).message);
        } catch (error) {
            // If not logged in, the url will respond with a redirect and JSON parsing will fail
            showToast("You need to be logged in before collecting sounds.")
        }
    }, () => {
        // Unexpected errors happened while processing request: close modal and show error in toast
        dismissModal(`collectSoundModal`);
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


const initCollectSoundFormModal = (soundId, collectSoundUrl) => {
    
    // Modify the form structure to add a "Category" label inline with the select dropdown
    const modalContainer = document.getElementById('collectSoundModal');
    const selectElement = modalContainer.getElementsByTagName('select')[0];
    const wrapper = document.createElement('div');
    wrapper.style = 'display:inline-block;';
    if (selectElement === undefined){
        // If no select element, the modal has probably loaded for an unauthenticated user
        console.log("select element is undefined")
        return;
    }
    console.log("SELECT ELEMENT", selectElement);
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
    console.log("CATEGORY SELECT ELEMENT: ", categorySelectElement);
    console.log("NEW CATEGORY NAME ELEMENT: ", newCategoryNameElement);
    toggleNewCollectionNameDiv(categorySelectElement, newCategoryNameElement);
    categorySelectElement.addEventListener('change', (event) => {
        toggleNewCollectionNameDiv(categorySelectElement, newCategoryNameElement);
    });

    // Bind action to save collectionSound in "add sound to collection button" (and prevent default form submit)
    saveButtonElement.addEventListener('click', (e) => {
        e.preventDefault();
        const data = {};
        data.collection = document.getElementById(`id_${  soundId.toString()  }-collection`).value;
        data.new_collection_name = document.getElementById(`id_${  soundId.toString()  }-new_collection_name`).value;
        saveCollectionSound(collectSoundUrl, data);
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
            if (!evt.altKey) {
                handleGenericModal(element.dataset.modalUrl, () => {
                    initCollectSoundFormModal(soundId, element.dataset.collectSoundUrl);
                }, undefined, true, true);
            } else {
                saveCollectionSound(element.dataset.collectSoundUrl);
            }
        });
    });
}

export { bindCollectSoundModals };
