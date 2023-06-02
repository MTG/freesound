import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters, initPlayersInModal, stopPlayersInModal} from './modal';

const handleRemixGroupsModal = (modalUrl, modalActivationParam) => {
    handleGenericModal(modalUrl, (modalContainer) => {
        initPlayersInModal(modalContainer);
    }, (modalContainer) => {
        stopPlayersInModal(modalContainer);
    }, true, true, modalActivationParam);
}

const bindRemixGroupModals = (container) => {
    bindModalActivationElements('[data-toggle="remix-group-modal"]', handleRemixGroupsModal, container);
}

bindRemixGroupModals();
activateModalsIfParameters('[data-toggle="remix-group-modal"]', handleRemixGroupsModal);

export {bindRemixGroupModals};
