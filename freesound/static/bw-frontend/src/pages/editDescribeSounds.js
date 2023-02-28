import {handleDismissModal, handleGenericModal} from "../components/modal"
import {showToast} from "../components/toast"
import {stopAllPlayers} from '../components/player/utils'
import {createPlayer} from '../components/player/player-ui'
import {initializeSoundSelector} from '../components/soundsSelector'
import addCheckboxVisibleElements from "../components/checkbox"
import {serializedIdListToIntList, combineIdsLists} from "../utils/data"


const openAddSoundSourcesModal = (modalUrl, selectedSourcesDestinationElement, onSourcesSelectedCallback) => {
    handleGenericModal(modalUrl, () => {
        const modalWrapper = document.getElementById('genericModalWrapper');
        
        const players = [...modalWrapper.getElementsByClassName('bw-player')]
        players.forEach(createPlayer)
        
        addCheckboxVisibleElements()

        const inputElement = modalWrapper.getElementsByTagName('input')[0];
        inputElement.addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                // TODO: the URL below should be loaded somehow from Django, maybe using some generic element data properties (?)
                const modalUrl = `/sources/search/?q=${inputElement.value}`;
                openAddSoundSourcesModal(modalUrl, selectedSourcesDestinationElement, onSourcesSelectedCallback);
            }
        });

        const soundSelectorElement = modalWrapper.getElementsByClassName('bw-sounds-selector-container')[0];
        initializeSoundSelector(soundSelectorElement, (element) => {
            addSelectedSourcesButton.disabled = element.dataset.selectedIds == ""
        });

        const addSelectedSourcesButton = modalWrapper.getElementsByTagName('button')[0];
        addSelectedSourcesButton.disabled = true;
        addSelectedSourcesButton.addEventListener('click', evt => {
            showToast("Adding selected sounds as sources!");
            const selectableSoundElements = [...modalWrapper.getElementsByClassName('bw-selectable-sound')];
            selectableSoundElements.forEach( element => {
                const checkbox = element.querySelectorAll('input.bw-checkbox')[0];
                if (checkbox.checked) {
                    checkbox.checked = false;
                    element.classList.remove('selected');
                    selectedSourcesDestinationElement.appendChild(element.parentNode);
                }
            });
            onSourcesSelectedCallback(soundSelectorElement.dataset.selectedIds);
            handleDismissModal('editSourcesModal');
        });

    }, () => {
        // Stop all players that could be being played inside the modal
        stopAllPlayers();
    }, true, true);
}

const bindSoundAddSourcesButtons = () => {
    const soundAddSourcesButtons = [...document.querySelectorAll('[data-toggle^="add-sources-modal"]')];
    soundAddSourcesButtons.forEach(element => {
        if (element.dataset.initialized !== true){
            element.dataset.initialized = true;
            element.addEventListener('click', (evt) => {
                evt.preventDefault();
                // TODO: the URL below should be loaded somehow from Django, maybe using some generic element data properties (?)
                const modalUrl = `/sources/search/`;
                const selectedSourcesDestinationElement = element.parentNode.getElementsByClassName('bw-sounds-selector-container')[0];
                openAddSoundSourcesModal(modalUrl, selectedSourcesDestinationElement, (selectedSoundIds) => {
                    
                    const sourcesHiddenInput = document.getElementsByName(`${element.dataset.formIdx}-sources`)[0];
                    console.log(sourcesHiddenInput, selectedSoundIds, sourcesHiddenInput.value)
                    const currentSourceIds = serializedIdListToIntList(sourcesHiddenInput.value);
                    const newSourceIds = serializedIdListToIntList(selectedSoundIds);
                    const combinedIds = combineIdsLists(currentSourceIds, newSourceIds);
                    sourcesHiddenInput.value = combinedIds.join(',');
                });
            });
        }
    });
}

bindSoundAddSourcesButtons()
