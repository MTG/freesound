import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters, initPlayersInModal, stopPlayersInModal} from './modal';

const handleModerationModal = (modalUrl, modalActivationParam, atPage) => {
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

const bindModerationModals = (container) => {
    bindModalActivationElements('[data-toggle="pending-moderation-modal"]', handleModerationModal, container);
    bindModalActivationElements('[data-toggle="tardy-users-modal"]', handleModerationModal, container);
    bindModalActivationElements('[data-toggle="tardy-moderators-modal"]', handleModerationModal, container);
}

bindModerationModals();
activateModalsIfParameters('[data-toggle="pending-moderation-modal"]', handleModerationModal);
activateModalsIfParameters('[data-toggle="tardy-users-modal"]', handleModerationModal);
activateModalsIfParameters('[data-toggle="tardy-moderators-modal"]', handleModerationModal);

export {bindModerationModals};