import {handleGenericModal} from './modal';
import {stopAllPlayers} from './player/utils'
import {createPlayer} from './player/player-ui'


const handleSimilarSoundsModal = (modalUrl, modalActivationParam) => {
    handleGenericModal(modalUrl, (modalContainer) => {
        // Init sound player inside popup
        const players = [...modalContainer.getElementsByClassName('bw-player')]
        players.forEach(createPlayer)
    }, () => {
        // Stop all players that could be being played inside the modal
        stopAllPlayers();
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
