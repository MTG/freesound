import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters, initPlayersInModal, stopPlayersInModal} from './modal';

const handleSimilarSoundsModal = (modalUrl, modalActivationParam) => {
    handleGenericModal(modalUrl, (modalContainer) => {
        initPlayersInModal(modalContainer);
    }, (modalContainer) => {
        stopPlayersInModal(modalContainer);
    }, true, true, modalActivationParam);
}

const bindSimilarSoundModals = (container) => {
    bindModalActivationElements('[data-toggle="similar-sounds-modal"]', handleSimilarSoundsModal, container);
}

bindSimilarSoundModals();
activateModalsIfParameters('[data-toggle="similar-sounds-modal"]', handleSimilarSoundsModal);

export {bindSimilarSoundModals};