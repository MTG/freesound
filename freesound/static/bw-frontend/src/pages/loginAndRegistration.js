import './page-polyfills';
import addCheckboxVisibleElements from "../components/checkbox";
import {handleDismissModal, handleModal} from "../components/modal";


const modalLinks = [
    document.querySelectorAll('[data-link="forgottenPasswordModal"]'),
    document.querySelectorAll('[data-link="registerModal"]'),
    document.querySelectorAll('[data-link="loginModal"]'),
];

modalLinks.forEach(links => {
    links.forEach(link => {
        link.addEventListener('click', () => {
            handleDismissModal(link.dataset.link);
            handleModal(link.dataset.link);
        });
    });
});

//---

const serialize = function(formEle) {
    // Get all fields
    const fields = [].slice.call(formEle.elements, 0);

    return fields
        .map(function(ele) {
            const name = ele.name;
            const type = ele.type;

            // We ignore
            // - field that doesn't have a name
            // - disabled field
            // - `file` input
            // - unselected checkbox/radio
            if (!name ||
                ele.disabled ||
                type === 'file' ||
                (/(checkbox|radio)/.test(type) && !ele.checked))
            {
                return '';
            }

            // Multiple select
            if (type === 'select-multiple') {
                return ele.options
                    .map(function(opt) {
                        return opt.selected
                            ? `${encodeURIComponent(name)}=${encodeURIComponent(opt.value)}`
                            : '';
                    })
                    .filter(function(item) {
                        return item;
                    })
                    .join('&');
            }

            return `${encodeURIComponent(name)}=${encodeURIComponent(ele.value)}`;
        })
        .filter(function(item) {
            return item;
        })
        .join('&');
};



const customRegistrationSubmit = (event) => {

    const registerModalForm = document.getElementById("registerModalForm");
    const registerModalElement = document.getElementById("registerModal");

    const params = serialize(registerModalForm);

    // Create new Ajax request
    const req = new XMLHttpRequest();
    req.open('POST', registerModalForm.action, true);
    req.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');

    // Handle the events
    req.onload = function() {
        if (req.status >= 200 && req.status < 400) {
            handleDismissModal('registerModal');
            registerModalElement.remove();

            document.getElementById('newPasswordModal').insertAdjacentHTML('afterend', req.responseText);

            handleModal('registerModal');
            // TODO: re-run checkbox init code
            addCheckboxVisibleElements();
        }
    };
    req.onerror = function() {
        alert("ERROR in the form request")
        // TODO: close modals and show message at bottom
    };

    // Send it
    req.send(params);

    // Stop propagation of submit event
    event.preventDefault();
    return false;
};

export default customRegistrationSubmit;