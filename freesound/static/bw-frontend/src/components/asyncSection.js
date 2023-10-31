import {showToast} from "./toast";
import {initPlayersInModal} from './modal';
import {bindSimilarSoundModals} from './similarSoundsModal';
import {bindBookmarkSoundButtons} from './bookmarkSound';
import {bindRemixGroupModals} from './remixGroupModal';

const asyncSectionPlaceholders = document.getElementsByClassName('async-section');

const initPlayersAndPlayerModalsInElement = (element) => {
    initPlayersInModal(element);
    bindSimilarSoundModals();
    bindBookmarkSoundButtons();
    bindRemixGroupModals();
}

asyncSectionPlaceholders.forEach(element => {
    const contentUrl = element.dataset.asyncSectionContentUrl;
    
    const req = new XMLHttpRequest();
    req.open('GET', contentUrl);
    req.onload = () => {
        if (req.status >= 200 && req.status < 300) {
            element.innerHTML = req.responseText;
            
            // Make sure we initialize sound/pack players inside the async section
            initPlayersAndPlayerModalsInElement(element);
        } else {
            // Unexpected errors happened while processing request: show toast
            showToast('Unexpected errors occurred while loading some of the content of this page. Please try again later...')
        }
    };
    req.onerror = () => {
        // Unexpected errors happened while processing request: show toast
        showToast('Unexpected errors occurred while loading some of the content of this page. Please try again later...')
    };
    
    // Send the form
    req.send();
});