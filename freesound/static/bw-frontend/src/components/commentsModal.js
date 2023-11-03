import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters} from './modal';


const handleCommentsModal = (modalUrl, modalActivationParam, atPage) => {
    if ((atPage !== undefined) && modalUrl.indexOf('&page') == -1){
        modalUrl += '&page=' + atPage;
    }
    handleGenericModal(modalUrl, undefined, undefined, true, true, modalActivationParam);
}

const bindCommentsModals = (container) => {
    bindModalActivationElements('[data-toggle="comments-modal"]', handleCommentsModal, container);
}

const activateCommentsModalsIfParameters = () => {
    activateModalsIfParameters('[data-toggle="comments-modal"]', handleCommentsModal);
}

export {bindCommentsModals, activateCommentsModalsIfParameters};