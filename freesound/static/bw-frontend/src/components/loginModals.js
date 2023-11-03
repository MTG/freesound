import { showToast } from './toast';
import serialize from '../utils/formSerializer'
import { activateModal, dismissModal, handleGenericModalWithForm } from "../components/modal";
import { addRecaptchaScriptTagToMainHead } from '../utils/recaptchaDynamicReload'

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
      showToast("If the address you've entered is correct, you should now receive an email with instructions");
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
  
  // Bind click actions on links to move to other login modals
  initLoginAndRegistrationModalLinks('registerModal');
  
  // Load grecaptcha script tag (needed if this is loaded ajax)
  addRecaptchaScriptTagToMainHead(registrationForm);
  
  // Add "next" parameter to the form action so users are redirected to the same page when registration finishes
  const pathWithParameters = window.location.pathname + window.location.search;
  registrationForm.action = registrationForm.action + '&next=' + encodeURI(pathWithParameters);
  
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

const initLoginAndRegistrationModalLinks = (modalContainerId) => {
  const modalContainer = document.getElementById(modalContainerId);
  [...modalContainer.querySelectorAll('[data-link="forgottenPasswordModal"]')].forEach(link => {
    link.addEventListener('click', () => {
      dismissModal(modalContainerId);
      handleProblemsLoggingInModal();
    });
  });
  [...modalContainer.querySelectorAll('[data-link="loginModal"]')].forEach(link => {
    link.addEventListener('click', () => {
      dismissModal(modalContainerId);
      handleLoginModal();
    });
  });
  [...modalContainer.querySelectorAll('[data-link="registerModal"]')].forEach(link => {
    link.addEventListener('click', () => {
      dismissModal(modalContainerId);
      handleRegistrationModal();
    });
  });
}

const handleLoginModal = () => {
  activateModal('loginModal');
  initLoginAndRegistrationModalLinks('loginModal');
  initLoginForm(document.getElementById("loginForm"));
}

const handleProblemsLoggingInModal = () => {
  activateModal('forgottenPasswordModal');
  initLoginAndRegistrationModalLinks('forgottenPasswordModal');
  initProblemsLoggingInForm(document.getElementById("problemsLoggingInModalForm"));
}

const handleRegistrationModal = () => {  
  handleGenericModalWithForm('/home/register/', initRegistrationForm, undefined, (req) => {
    // If registration succeeded, redirect to the registration feedback page
    const data = JSON.parse(req.responseText);
    window.location.href = data.redirectURL;
  }, undefined);
}

const handleRegistrationFeedbackModal = () => {
  activateModal('feedbackRegistration');
}

// Bind login modal buttons
[...document.querySelectorAll('[data-toggle="login-modal"]')].forEach(modalToggle => {
  modalToggle.addEventListener('click', () => handleLoginModal());
});

[...document.querySelectorAll('[data-toggle="registration-modal"]')].forEach(modalToggle => {
  modalToggle.addEventListener('click', () => handleRegistrationModal());
});

// Open login modals if corresponding request parameters are set
const urlParams = new URLSearchParams(window.location.search);
const registrationParam = urlParams.get('registration');
const feedbackRegistrationParam = urlParams.get('feedbackRegistration');
const problemsLoggingInParam = urlParams.get('loginProblems');

document.addEventListener("DOMContentLoaded", () => {
  if (registrationParam)  {
    handleRegistrationModal();
  }
  if (feedbackRegistrationParam) {
    handleRegistrationFeedbackModal();
  }
  if (problemsLoggingInParam) {
    handleProblemsLoggingInModal();
  }
});
