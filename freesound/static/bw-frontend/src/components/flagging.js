import {makePostRequest} from '../utils/postRequest';

function post_flag(div_id, flag_type, object_id, url) {
    const wheelElement = document.getElementById(div_id + "_wheel");
    wheelElement.innerHTML = '<img width="12px" height="12px" src="/static/bw-frontend/public/bw_indicator.gif"/>';
    makePostRequest(url, {'flag_type': flag_type, 'object_id': object_id}, () => {
        const linkElement = document.getElementById(div_id.toString() + "_link");
        const wheelElement = document.getElementById(div_id.toString() + "_wheel");
        linkElement.innerHTML = "Marked as spam/offensive";
        wheelElement.innerHTML = "";
    }, () => {
        const linkElement = document.getElementById(div_id.toString() + "_link");
        const wheelElement = document.getElementById(div_id.toString() + "_wheel");
        linkElement.innerHTML = "An error occurred, try again later";
        wheelElement.innerHTML = "";
    });
}

const bindFlagUserButtons = (container) => {
    const flagUserElements = container.getElementsByClassName('post-flag');
    flagUserElements.forEach(element => {
        element.addEventListener('click', () =>{
            post_flag(element.dataset.contentObjId + element.dataset.flagType, element.dataset.flagType, element.dataset.contentObjId,  element.dataset.postFlagUrl);
        });
    });
}

export {bindFlagUserButtons};