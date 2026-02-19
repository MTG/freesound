import { handleGenericModal } from './modal';

const prepareAfterDownloadSoundModals = () => {
  const downloadButtonElements = [...document.getElementsByClassName(
    'sound-download-button'
  )];
  downloadButtonElements.forEach(element => {
    const showModalUrl = element.dataset.showAfterDownloadModalUrl;
    element.addEventListener('click', () => {
      handleGenericModal(showModalUrl, undefined, undefined, false, true);
    });
  });
};

export { prepareAfterDownloadSoundModals };
