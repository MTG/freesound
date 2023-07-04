import {dismissModal, handleGenericModal} from "./modal";
import {createSelect} from "./select";
import {showToast} from "./toast";
import {makePostRequest} from "../utils/postRequest";

const saveBookmark = (addBookmarkUrl, data) => {

    let formData = {};
    if (data === undefined){
        formData.name = "";
        formData.category = "";
        formData.new_category_name = "";
        formData.use_last_category = true;
    } else {
        formData = data;
    }
    makePostRequest(addBookmarkUrl, formData, (responseText) => {
        // Bookmark saved successfully. Close model and show feedback
        dismissModal(`bookmarkSoundModal`);
        try {
            showToast(JSON.parse(responseText).message);
        } catch (error) {
            // If not logged in, the url will respond with a redirect and JSON parsing will fail
            showToast("You need to be logged in before bookmarking sounds.")
        }
    }, () => {
        // Unexpected errors happened while processing request: close modal and show error in toast
        dismissModal(`bookmarkSoundModal`);
        showToast('Some errors occurred while bookmarking the sound.');
    });
}


const toggleNewCategoryNameDiv = (select, newCategoryNameDiv) => {
    if (select.value == '0'){
        // No category is selected, show the new category name input
        newCategoryNameDiv.classList.remove('display-none');
    } else {
        newCategoryNameDiv.classList.add('display-none');
    }
}


const initBookmarkFormModal = (soundId, addBookmarkUrl) => {
    
    // Modify the form structure to add a "Category" label inline with the select dropdown
    const modalContainer = document.getElementById(`bookmarkSoundModal`);
    const selectElement = modalContainer.getElementsByTagName('select')[0];
    const wrapper = document.createElement('div');
    if (selectElement === undefined){
        // If no select element, the modal has probably loaded for an unauthenticated user
        return;
    }
    selectElement.parentNode.insertBefore(wrapper, selectElement.parentNode.firstChild);
    const label = document.createElement('div');
    label.innerHTML = "Select a bookmark category:"
    label.style = 'display:inline-block;';
    label.classList.add('text-grey');
    wrapper.appendChild(label)
    wrapper.appendChild(selectElement)
    createSelect();  // We need to trigger create select elements because bookmark form has one

    const formElement = modalContainer.getElementsByTagName('form')[0];
    const buttonsInModalForm = formElement.getElementsByTagName('button');
    const saveButtonElement = buttonsInModalForm[buttonsInModalForm.length - 1];
    const categorySelectElement = document.getElementById(`id_${  soundId.toString()  }-category`);
    const newCategoryNameElement = document.getElementById(`id_${  soundId.toString()  }-new_category_name`);
    toggleNewCategoryNameDiv(categorySelectElement, newCategoryNameElement);
    categorySelectElement.addEventListener('change', (event) => {
        toggleNewCategoryNameDiv(categorySelectElement, newCategoryNameElement);
    });

    // Bind action to save bookmark in "add bookmark button" (and prevent default form submit)
    saveButtonElement.addEventListener('click', (e) => {
        e.preventDefault();
        const data = {};
        data.category = document.getElementById(`id_${  soundId.toString()  }-category`).value;
        data.new_category_name = document.getElementById(`id_${  soundId.toString()  }-new_category_name`).value;
        saveBookmark(addBookmarkUrl, data);
    });
};

const bindBookmarkSoundButtons = () => {
    const bookmarkSoundButtons = [...document.querySelectorAll('[data-toggle="bookmark-modal"]')];
    bookmarkSoundButtons.forEach(element => {
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
                    initBookmarkFormModal(soundId, element.dataset.addBookmarkUrl);
                }, () => {}, true, true);
            } else {
                saveBookmark(element.dataset.addBookmarkUrl);
            }
        });
    });
}

bindBookmarkSoundButtons();

export {bindBookmarkSoundButtons};
