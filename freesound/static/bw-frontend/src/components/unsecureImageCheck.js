// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

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

// @license-end
