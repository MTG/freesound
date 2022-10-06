// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import {handleGenericModal} from './modal';


const bindDownloadSoundButtons = () => {
    const downloadButtonElements = document.getElementsByClassName('sound-download-button');
    downloadButtonElements.forEach(element => {
        const showModalUrl = element.dataset.showAfterDownloadModalUrl;
        element.addEventListener('click', () => {
            handleGenericModal(showModalUrl, () => {}, () => {}, false, true);
        });
    });
}

bindDownloadSoundButtons();

// @license-end
