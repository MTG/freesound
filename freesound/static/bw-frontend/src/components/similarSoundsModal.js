import {handleGenericModal} from './modal';
import {stopAllPlayersInContainer, initializePlayersInContainer} from './player/utils'


const handleSimilarSoundsModal = (modalUrl, modalActivationParam) => {
    handleGenericModal(modalUrl, (modalContainer) => {
        initializePlayersInContainer(modalContainer);
    }, (modalContainer) => {
        stopAllPlayersInContainer(modalContainer);
    }, true, true, modalActivationParam);
}

const bindSimilarSoundButtons = () => {
    const similarSoundsButtons = document.querySelectorAll('[data-toggle="similar-sounds-modal"]');
    similarSoundsButtons.forEach(element => {
        if (element.dataset.alreadyBinded !== undefined){
            return;
        }
        element.dataset.alreadyBinded = true;
        element.addEventListener('click', (evt) => {
            evt.preventDefault();
            handleSimilarSoundsModal(element.dataset.modalContentUrl, element.dataset.modalActivationParam);
        });
    });
}

bindSimilarSoundButtons();


export {handleSimilarSoundsModal, bindSimilarSoundButtons};
