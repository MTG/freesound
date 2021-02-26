import './page-polyfills';
import {handleDismissModal, handleModal} from '../components/modal';
import {showToast} from '../components/toast';
import serialize from '../utils/formSerializer'


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


const customRegistrationSubmit = (event) => {

    const registerModalForm = document.getElementById("registerModalForm");
    const registerModalElement = document.getElementById("registerModal");

    const params = serialize(registerModalForm);

    // Create new Ajax request to submit registration form contents
    const req = new XMLHttpRequest();
    req.open('POST', registerModalForm.action, true);
    req.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');

    // Handle the events
    req.onload = function() {
        if (req.status >= 200 && req.status < 400) {
            if (req.responseText.indexOf('registerModalForm') === -1){
                // Registration was successful, we should have received the redirect URL where we should redirect the
                // user in the response
                const data = JSON.parse(req.responseText);
                window.location.href = data.redirectURL;
            }  else {
                // There were errors in the registration form. In that case the response are the HTML elements of the
                // form (including error warnings) and we should re-create it

                // Close current modal and remove element
                handleDismissModal('registerModal');
                registerModalElement.remove();

                // Create new modal element and place it adjacent to newPasswordModal
                document.getElementById('newPasswordModal').insertAdjacentHTML('afterend', req.responseText);

                // Open the newly created modal
                handleModal('registerModal');
            }
        }
    };
    req.onerror = function() {
        // Unexpected errors happened while processing request: close modal and show error in toast
        handleDismissModal('registerModal');
        showToast('Some errors occurred while processing the form. Please try again later.')
    };

    // Send the form
    req.send(params);

    // Stop propagation of submit event
    event.preventDefault();
    return false;
};

export default customRegistrationSubmit;