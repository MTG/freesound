import {handleGenericModal} from './modal';
import {stopAllPlayersInContainer, initializePlayersInContainer} from './player/utils';
import {initializeCarousels} from './carousel';
import {initRatingWidgets} from './rating';



const handleDownloadersModal = (modalUrl, modalActivationParam, atPage) => {
    if ((atPage !== undefined) && modalUrl.indexOf('&page') == -1){
        modalUrl += '&page=' + atPage;
    }
    handleGenericModal(modalUrl, (modalContainer) => {
        // This method is used both for the "users that downloaded sound/pack" and the "sounds/packs downloaded by user" modals
        // The second type displays sounds players in the modal so we need to initialize them when modal is loaded
        initializePlayersInContainer(modalContainer);
        initializeCarousels(modalContainer);
        initRatingWidgets(modalContainer);
    }, (modalContainer) => {
        // This method is used both for the "users that downloaded sound/pack" and the "sounds/packs downloaded by user" modals
        // The second type displays sounds players in the modal so we need to stop them when modal is closed
        stopAllPlayersInContainer(modalContainer);
    }, true, true, modalActivationParam);
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