import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters, dismissModal} from './modal';
import {makePostRequest} from "../utils/postRequest";
import {showToast} from "./toast";

const saveAnnotation = (addAnnotationUrl, text, user_id) => {

    let formData = {};
    formData.text = text;
    
    makePostRequest(addAnnotationUrl, formData, (responseText) => {
        // Bookmark saved successfully. Close model and show feedback
        dismissModal(`moderationAnnotationsModal`);
        const responseData = JSON.parse(responseText);
        document.getElementsByClassName('annotation-counter-' + user_id).forEach(element => {
            element.innerText = responseData.num_annotations;
        });
        showToast(responseData.message);
    }, () => {
        // Unexpected errors happened while processing request: close modal and show error in toast
        dismissModal(`moderationAnnotationsModal`);
        showToast('Some errors occurred while adding the annotation.');
    });
}

const handleModerationModal = (modalUrl, modalActivationParam, atPage) => {
    if ((atPage !== undefined) && modalUrl.indexOf('&page') == -1){
        modalUrl += '&page=' + atPage;
    }
    handleGenericModal(modalUrl, undefined, undefined, true, true, modalActivationParam);
}

const handleUserAnnnotationModal = (modalUrl, modalActivationParam) => {
    handleGenericModal(modalUrl, (modalContainer) => {
        // Bind action to save annotation (and prevent default form submit)
        const formElement = modalContainer.getElementsByTagName('form')[0];
        const buttonsInModalForm = formElement.getElementsByTagName('button');
        const textInputField = formElement.getElementsByTagName('textarea')[0];
        const saveButtonElement = buttonsInModalForm[buttonsInModalForm.length - 1];
        saveButtonElement.addEventListener('click', (e) => {
            e.preventDefault();
            saveAnnotation(saveButtonElement.dataset.addAnnotationUrl, textInputField.value, saveButtonElement.dataset.userId);
        });
    }, undefined, true, true, modalActivationParam);
}

const bindModerationModals = (container) => {
    bindModalActivationElements('[data-toggle="pending-moderation-modal"]', handleModerationModal, container);
    bindModalActivationElements('[data-toggle="user-annotations-modal"]', handleUserAnnnotationModal, container);
    bindModalActivationElements('[data-toggle="tardy-users-modal"]', handleModerationModal, container);
    bindModalActivationElements('[data-toggle="tardy-moderators-modal"]', handleModerationModal, container);
}

const activateModerationModalsIfParameters = () => {
    activateModalsIfParameters('[data-toggle="pending-moderation-modal"]', handleModerationModal);
    activateModalsIfParameters('[data-toggle="user-annotations-modal"]', handleUserAnnnotationModal);
    activateModalsIfParameters('[data-toggle="tardy-users-modal"]', handleModerationModal);
    activateModalsIfParameters('[data-toggle="tardy-moderators-modal"]', handleModerationModal);
}

export {bindModerationModals, activateModerationModalsIfParameters};