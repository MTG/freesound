import './page-polyfills';
import {handleDismissModal, handleModal} from '../components/modal';
import {showToast} from '../components/toast';
import serialize from '../utils/formSerializer'
import addCheckboxVisibleElements from "../components/checkbox";
import {addRecaptchaScriptTagToMainHead} from '../utils/recaptchaDynamicReload'


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
    req.onload = () => {
        if (req.status >= 200 && req.status < 300) {
            if (req.getResponseHeader('content-type') === 'application/json'){
                // If response is of type JSON, that means registration was successful, we should have received the redirect URL 
                // where we should redirect the user in the response
                const data = JSON.parse(req.responseText);
                window.location.href = data.redirectURL;
            }  else {
                // There were errors in the registration form. In that case the response are the HTML elements of the
                // form (including error warnings) and we should replace current modal HTML with this one (and re-init all needed
                // javascript)
                const genericModalWrapper = registerModalElement.parentNode;
                genericModalWrapper.innerHTML = req.responseText;
                const modalContainerId = genericModalWrapper.getElementsByClassName('modal')[0].id;
                const modalContainer = document.getElementById(modalContainerId);
                modalContainer.classList.add('show');
                modalContainer.style.display = 'block';
                const registerModalForm = modalContainer.querySelector("#registerModalForm");
                initRegistrationForm(registerModalForm);
                const modalDismiss = genericModalWrapper.querySelectorAll('[data-dismiss="modal"]');
                modalDismiss.forEach(dismiss => {
                    dismiss.addEventListener('click', () => {
                        handleDismissModal('registerModal');});
                });
            }
        }
    };
    req.onerror = () => {
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

const checkUsernameAvailability = (username, baseURL, callback) => {
    const req = new XMLHttpRequest();
    req.open('GET', baseURL  + '?username=' + username, true);
    req.onload = () => {
        if (req.status >= 200 && req.status < 300) {
            const data = JSON.parse(req.responseText);
            callback(data.result);
        }
    };
    req.send();
};

const customProblemsLoggingInSubmit = (event) => {
    const problemsLoggingInForm = document.getElementById("problemsLoggingInModalForm");
    const params = serialize(problemsLoggingInForm);

    // Create new Ajax request to submit registration form contents
    const req = new XMLHttpRequest();
    req.open('POST', problemsLoggingInForm.action, true);
    req.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
    req.onload = () => {
        if (req.status >= 200 && req.status < 300) {
            showToast('Check your email, we\'ve sent you a link');
        }
    };
    req.onerror = () => {
        // Unexpected errors happened while processing request: show error in toast
        showToast('Some errors occurred while processing the form. Please try again later.')
    };

    // Send the form
    req.send(params);

    // Stop propagation of submit event
    event.preventDefault();
    return false;
};

const initRegistrationForm = (registrationForm) => {

    // Load grecaptcha script tag (needed if this is loaded ajax)
    addRecaptchaScriptTagToMainHead(registrationForm);

    // Add "next" parameter to the form action so users are redirected to the same page when registration finishes
    const pathWithParameters = window.location.pathname + window.location.search;
    registrationForm.action = registrationForm.action + '&next=' + encodeURI(pathWithParameters);

    // Initialize checkboxes (registration form contains checkboxes)
    addCheckboxVisibleElements();

    // Add event handler to check username availability on focusout
    const usernameInputElement = registrationForm.querySelector('input[name="username"]');
    usernameInputElement.addEventListener("focusout", () => {
        checkUsernameAvailability(usernameInputElement.value, registrationForm.dataset.checkUsernameUrl, (isAvailable) => {
            const previousElementIsErrorlist = usernameInputElement.previousElementSibling.classList.contains('errorlist');
            if (isAvailable === true){
                // Check if there is an "invalid username" message shown and remove it if username is now valid
                if (previousElementIsErrorlist){
                    usernameInputElement.previousElementSibling.remove();
                }
            } else {
                // Check if there is an "invalid username" message shown, and add one if it is not there
                if (!previousElementIsErrorlist) {
                    usernameInputElement.insertAdjacentHTML('beforebegin', '<ul class="errorlist"><li>You cannot use this username to create an account</li></ul>')
                }
            }
        });
    });

    // Assign custom onsubmit method which will submit the form via AJAX and reload form in modal if error occur
    registrationForm.onsubmit = (event) => {
        customRegistrationSubmit(event);
    }
};

const initLoginForm = (loginForm) => {
    // Set "next" value in the hidden "next" input so users are redirected to the same page when login finishes
    const pathWithParameters = window.location.pathname + window.location.search;
    const loginNextHiddenInput = loginForm.querySelectorAll('input[name="next"]')[0];
    if (!loginNextHiddenInput.value){
        // Only if next value is not yet set, set it automatically
        loginNextHiddenInput.value = pathWithParameters;
    }
};

const initProblemsLoggingInForm = (problemsLoggingInForm) => {
    // Assign custom onsubmit method which will submit the form via AJAX and show notification
    problemsLoggingInForm.onsubmit = (event) => {
        customProblemsLoggingInSubmit(event);
    }
};


export {initRegistrationForm, initProblemsLoggingInForm, initLoginForm};
