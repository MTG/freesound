import { showToast } from './toast';

const addUnsecureImageCheckListeners = () => {
    const elementsToCheckForUnsecureImages = document.getElementsByClassName('unsecure-image-check');
    elementsToCheckForUnsecureImages.forEach(element => {
        ['keydown', 'focusin'].forEach(eventName => {
            element.addEventListener(eventName, () => {
                setTimeout(() => {
                    // We need the timeout for the paste event to make sure the text has been pasted when evaluated
                    const regularExpression = new RegExp('.*<img.+src=.?http:.*', 'i');
                    const isUnsecure = regularExpression.test(element.value);
                    if (isUnsecure) {
                        showToast("<b>Warning</b>: We only support images from HTTPS locations. Images from an HTTP location will appear as a link.")
                    }
                }, 100);
            });
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    addUnsecureImageCheckListeners();
});