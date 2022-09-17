// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

import { getCookie } from "./cookies";

const makePostRequest = (url, data, successCallback, errorCallback) => {
    const csrftoken = getCookie('csrftoken');
    const req = new XMLHttpRequest();
    // TODO: do not hardcode the URL below
    req.open('POST', url, true);
    req.onload = () => {
        if (req.status >= 200 && req.status < 300) {
            successCallback(req.responseText);
        } else {
            errorCallback(req.responseText);
        }
    };
    req.onerror = () => {
        errorCallback(req.responseText);
    };
    req.setRequestHeader('X-CSRFToken', csrftoken);
    // Header below needed for Django .is_ajax() to return true
    req.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    const formData = new FormData();
    for (const key in data) {
        formData.append(key, data[key]);
    }
    req.send(formData);
}

export {makePostRequest};

// @license-end
