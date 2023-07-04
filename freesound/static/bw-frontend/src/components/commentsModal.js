import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters, initPlayersInModal, stopPlayersInModal, bindConfirmationModalElements} from './modal';
import {bindFlagUserElements} from './flagging';

const handleCommentsModal = (modalUrl, modalActivationParam, atPage) => {
    if ((atPage !== undefined) && modalUrl.indexOf('&page') == -1){
        modalUrl += '&page=' + atPage;
    }
    handleGenericModal(modalUrl, (modalContainer) => {
        initPlayersInModal(modalContainer);
        bindConfirmationModalElements(modalContainer); // For the "delete comment" buttons which need confirmation
        bindFlagUserElements(modalContainer); // For the "flag comment" buttons
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