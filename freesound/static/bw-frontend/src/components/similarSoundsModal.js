// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import {handleGenericModal} from './modal';
import {stopAllPlayers} from './player/utils'
import {createPlayer} from './player/player-ui'


const openSimilarSoundsModal = (modalUrl, modalActivationParam) => {
    handleGenericModal(modalUrl, () => {
        // Init sound player inside popup
        const modalWrapper = document.getElementById('genericModalWrapper');
        const players = [...modalWrapper.getElementsByClassName('bw-player')]
        players.forEach(createPlayer)

        // If modal is activated with a param, add the param to the URL when opening the modal
        if (modalActivationParam !== undefined){
            const searchParams = new URLSearchParams(window.location.search);
            searchParams.set(modalActivationParam, "1");
            const url = window.location.protocol + '//' + window.location.host + window.location.pathname + '?' + searchParams.toString();
            window.history.replaceState(null, "", url);
        }
    }, () => {
        // Stop all players that could be being played inside the modal
        stopAllPlayers();

        // If modal is activated with a param, remove the param to the URL when closing the modal
        if (modalActivationParam !== undefined) {
            const searchParams = new URLSearchParams(window.location.search);
            searchParams.delete(modalActivationParam);
            const url = window.location.protocol + '//' + window.location.host + window.location.pathname + '?' + searchParams.toString();
            window.history.replaceState(null, "", url);
        }
    }, true, true);
}

const bindSimilarSoundButtons = () => {
    const similarSoundsButtons = document.querySelectorAll('[data-toggle="similar-sounds-modal"]');
    similarSoundsButtons.forEach(element => {
        element.addEventListener('click', (evt) => {
            evt.preventDefault();
            openSimilarSoundsModal(element.dataset.modalContentUrl, element.dataset.modalActivationParam);
        });
    });
}

bindSimilarSoundButtons();


export {openSimilarSoundsModal};

// @license-end
