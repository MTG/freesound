

const getCookie = (name) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (`${name  }=`)) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const makePostRequest = (url, data, successCallback, errorCallback) => {
    const csrftoken = getCookie('csrftoken');
    const req = new XMLHttpRequest();
    // TODO: do not hardcode the URL below
    req.open('POST', url, true);
    req.onload = () => {
        if (req.status === 200) {
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
