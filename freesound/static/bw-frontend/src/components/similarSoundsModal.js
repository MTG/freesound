import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters} from './modal';

const handleSimilarSoundsModal = (modalUrl, modalActivationParam) => {
    handleGenericModal(modalUrl, undefined, undefined, true, true, modalActivationParam);
}

const bindSimilarSoundModals = (container) => {
    bindModalActivationElements('[data-toggle="similar-sounds-modal"]', handleSimilarSoundsModal, container);
}

const activateSimilarSoundsModalsIfParameters = () => {
    activateModalsIfParameters('[data-toggle="similar-sounds-modal"]', handleSimilarSoundsModal);
}

export {bindSimilarSoundModals, activateSimilarSoundsModalsIfParameters};