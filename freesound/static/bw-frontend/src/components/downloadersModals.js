import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters} from './modal';

const handleDownloadersModal = (modalUrl, modalActivationParam, atPage) => {
    if ((atPage !== undefined) && modalUrl.indexOf('&page') == -1){
        modalUrl += '&page=' + atPage;
    }
    handleGenericModal(modalUrl, undefined, undefined, true, true, modalActivationParam);
}

const bindDownloadersModals = (container) => {
    bindModalActivationElements('[data-toggle="downloaders-modal"]', handleDownloadersModal, container);
}

const activateDownloadersModalsIfParameters = () => {
    activateModalsIfParameters('[data-toggle="downloaders-modal"]', handleDownloadersModal);
}


export {bindDownloadersModals, activateDownloadersModalsIfParameters};