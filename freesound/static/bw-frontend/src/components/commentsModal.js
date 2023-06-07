import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters, initPlayersInModal, stopPlayersInModal} from './modal';

const handleCommentsModal = (modalUrl, modalActivationParam, atPage) => {
    if ((atPage !== undefined) && modalUrl.indexOf('&page') == -1){
        modalUrl += '&page=' + atPage;
    }
    handleGenericModal(modalUrl, (modalContainer) => {
        initPlayersInModal(modalContainer);
    }, (modalContainer) => {
        stopPlayersInModal(modalContainer);
    }, true, true, modalActivationParam);
}

const bindCommentsModals = (container) => {
    bindModalActivationElements('[data-toggle="comments-modal"]', handleCommentsModal, container);
}

bindCommentsModals();
activateModalsIfParameters('[data-toggle="comments-modal"]', handleCommentsModal);

export {bindCommentsModals};