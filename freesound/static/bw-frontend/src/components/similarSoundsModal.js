import {handleGenericModal, bindModalActivationElements, activateModalsIfParameters} from './modal';


const handleSimilarSoundsModal = (modalUrl, modalActivationParam) => {
    handleGenericModal(modalUrl, (modalContainer) => {
        // Bind listener to update paginator links if new similarity space is selected
        const currentUrl = new URL(modalUrl, window.location.origin);

        console.log(currentUrl, modalUrl)
        const similaritySpaceSelect = modalContainer.querySelector('#similarity-space-select');
        if (similaritySpaceSelect) {
            similaritySpaceSelect.addEventListener('change', (evt) => {
                const selectedSpace = evt.target.value;
                const currentUrl = new URL(modalUrl, window.location.origin);
                currentUrl.searchParams.set('similarity_space', selectedSpace);
                currentUrl.searchParams.set('page', similaritySpaceSelect.dataset.currentPage);
                // Reload modal with new similarity space and the same page
                handleSimilarSoundsModal(currentUrl.toString(), modalActivationParam);
            });
        }
    }, undefined, true, true, modalActivationParam);
}

const bindSimilarSoundsModal = (container) => {
    bindModalActivationElements('[data-toggle="similar-sounds-modal"]', handleSimilarSoundsModal, container);
}

const activateSimilarSoundsModalIfParameters = () => {
    activateModalsIfParameters('[data-toggle="similar-sounds-modal"]', handleSimilarSoundsModal);
}

export {bindSimilarSoundsModal, activateSimilarSoundsModalIfParameters};