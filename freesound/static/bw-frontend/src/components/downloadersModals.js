import {handleGenericModal} from './modal';

const handleDownloadersModal = (modalUrl, modalActivationParam, atPage) => {
    if ((atPage !== undefined) && modalUrl.indexOf('&page') == -1){
        modalUrl += '&page=' + atPage;
    }
    handleGenericModal(modalUrl, undefined, undefined, true, true, modalActivationParam);
}

const bindDownloadersButtons = () => {
    const downloadersButtons = document.querySelectorAll('[data-toggle="downloaders-modal"]');
    downloadersButtons.forEach(element => {
        if (element.dataset.alreadyBinded !== undefined){
            return;
        }
        element.dataset.alreadyBinded = true;
        element.addEventListener('click', (evt) => {
            evt.preventDefault();
            handleDownloadersModal(element.dataset.modalContentUrl, element.dataset.modalActivationParam);
        });
    });
}

bindDownloadersButtons();

export {handleDownloadersModal};