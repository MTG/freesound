import {handleDismissModal, handleGenericModal} from "./modal";
import {createSelect} from "./select";
import {showToast} from "./toast";
import {makePostRequest} from "../utils/postRequest";

// TODO: the 2 URLs below should be loaded somehow from Django, maybe using some generic element data properties (?)
const addBookmarkUrl = '/home/bookmarks/add/';
const bookmarkFormModalUrl = '/home/bookmarks/get_form_for_sound/';

const saveBookmark = (soundId, data) => {
    let formData = {};
    if (data === undefined){
        formData.name = "";
        formData.category = "";
        formData.new_category_name = "";
        formData.use_last_category = true;
    } else {
        formData = data;
    }
    makePostRequest(`${ addBookmarkUrl }${ soundId }/`, formData, (responseText) => {
        // Bookmark saved successfully. Close model and show feedback
        handleDismissModal(`bookmarkSoundModal-${ soundId }`);
        showToast(JSON.parse(responseText).message);
    }, () => {
        // Unexpected errors happened while processing request: close modal and show error in toast
        handleDismissModal(`bookmarkSoundModal-${ soundId }`);
        showToast('Some errors occurred while bookmarking the sound.');
    });
}

const initBookmarkFormModal = (soundId) => {
    // We need to trigger create select elements because bookmark form has one
    createSelect();

    // Bind action to save bookmark in "add bookmark button" (and prevent default form submit)
    const modalElement = document.getElementById(`bookmarkSoundModal`);
    const selectElement = modalElement.getElementsByTagName('select')[0];
    selectElement.insertAdjacentHTML("beforebegin", 'Category: ');
    const formElement = modalElement.getElementsByTagName('form')[0];
    const buttonsInModalForm = formElement.getElementsByTagName('button');
    const saveButtonElement = buttonsInModalForm[buttonsInModalForm.length - 1];
    saveButtonElement.addEventListener('click', (e) => {
        e.preventDefault();
        const data = {};
        data.name = document.getElementById(`id_${  soundId.toString()  }-name`).value;
        data.category = document.getElementById(`id_${  soundId.toString()  }-category`).value;
        data.new_category_name = document.getElementById(`id_${  soundId.toString()  }-new_category_name`).value;
        saveBookmark(soundId, data);
    });
};

const bindBookmarkSoundButtons = () => {
    const bookmarkSoundButtons = [...document.querySelectorAll('[data-toggle^="bookmark-modal-"]')];
    bookmarkSoundButtons.forEach(element => {
        element.addEventListener('click', (evt) => {
            evt.preventDefault();
            const dataToggleAttributeSplit = element.getAttribute('data-toggle').split('-');
            const soundId = parseInt(dataToggleAttributeSplit[dataToggleAttributeSplit.length - 1], 10);
            const modalUrl = `${bookmarkFormModalUrl}${soundId}/`;
            if (!evt.altKey) {
                handleGenericModal(modalUrl, () => {
                    initBookmarkFormModal(soundId);
                }, () => {}, true, false);
            } else {
                saveBookmark(soundId);
            }
        });
    });
}

bindBookmarkSoundButtons();
