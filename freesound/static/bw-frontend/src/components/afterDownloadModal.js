import {handleGenericModal} from './modal';

const downloadButtonElements = document.getElementsByClassName('sound-download-button');
downloadButtonElements.forEach(element => {
    const showModalUrl = element.dataset.showAfterDownloadModalUrl;
    element.addEventListener('click', () => {
        handleGenericModal(showModalUrl, () => {}, () => {}, false, true);
    });
});
