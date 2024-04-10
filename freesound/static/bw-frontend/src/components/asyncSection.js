import { showToast } from "./toast";
import { initializeStuffInContainer } from "../utils/initHelper";

const prepareAsyncSections = (container) => {
    const asyncSectionPlaceholders = container.getElementsByClassName('async-section');
    asyncSectionPlaceholders.forEach(element => {
        const contentUrl = element.dataset.asyncSectionContentUrl;
        const req = new XMLHttpRequest();
        req.open('GET', contentUrl);
        req.onload = () => {
            if (req.status >= 200 && req.status < 300) {
                element.innerHTML = req.responseText;
                // Make sure we initialize sound/pack players inside the async section
                initializeStuffInContainer(element, true, false);
            } else {
                // Unexpected errors happened while processing request: show toast
                showToast('Unexpected errors occurred while loading some of the content of this page. Please try again later...')
                element.innerHTML = '';
            }
        };
        req.onerror = () => {
            // Unexpected errors happened while processing request: show toast and clear async element
            showToast('Unexpected errors occurred while loading some of the content of this page. Please try again later...')
            element.innerHTML = '';
        };
        
        // Send the form
        req.send();
    });
}

export {prepareAsyncSections};