import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters, initPlayersInModal, stopPlayersInModal} from './modal';

const handleDownloadersModal = (modalUrl, modalActivationParam, atPage) => {
    if ((atPage !== undefined) && modalUrl.indexOf('&page') == -1){
        modalUrl += '&page=' + atPage;
    }
    handleGenericModal(modalUrl, (modalContainer) => {
        // This method is used both for the "users that downloaded sound/pack" and the "sounds/packs downloaded by user" modals
        // The second type displays sounds players in the modal so we need to initialize them when modal is loaded
        initPlayersInModal(modalContainer);
    }, (modalContainer) => {
        // This method is used both for the "users that downloaded sound/pack" and the "sounds/packs downloaded by user" modals
        // The second type displays sounds players in the modal so we need to stop them when modal is closed
        stopPlayersInModal(modalContainer);
    }, true, true, modalActivationParam);
}

const bindDownloadersModals = (container) => {
    bindModalActivationElements('[data-toggle="downloaders-modal"]', handleDownloadersModal, container);
}

bindDownloadersModals();
activateModalsIfParameters('[data-toggle="downloaders-modal"]', handleDownloadersModal);

export {bindDownloadersModals};