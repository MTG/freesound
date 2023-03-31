import {initRegistrationForm, initProblemsLoggingInForm, initLoginForm} from "../pages/loginAndRegistration";
import {showToast, showToastNoTimeout, dismissToast} from "./toast";

const modals = [...document.querySelectorAll('[data-toggle="modal"]')];

const urlParams = new URLSearchParams(window.location.search);
const registrationParam = urlParams.get('registration');
const feedbackRegistrationParam = urlParams.get('feedbackRegistration');
const problemsLoggingInParam = urlParams.get('loginProblems');

const handleDismissModal = modalContainerId => {
  const modalContainer = document.getElementById(modalContainerId);
  if (modalContainer !== null){
    modalContainer.classList.remove('show');
    modalContainer.style.display = 'none';
  }
};


const initLoginAndRegistrationModalLinks = (modalContainerId) => {
  const modalLinks = [
    document.querySelectorAll('[data-link="forgottenPasswordModal"]'),
    document.querySelectorAll('[data-link="loginModal"]'),
    document.querySelectorAll('[data-link="registerModal"]'),
  ];

  modalLinks.forEach(links => {
    links.forEach(link => {
      link.addEventListener('click', () => {
        handleDismissModal(modalContainerId);
        handleModal(link.dataset.link);
      });
    });
  });
}

const initModalDismissButton = (modalContainerElement) => {
  const modalDismiss = [...modalContainerElement.querySelectorAll('[data-dismiss="modal"]')];
  modalDismiss.forEach(dismiss => {
    dismiss.addEventListener('click', () => handleDismissModal(modalContainerElement.id));
  });
}

const handleModal = modalContainerId => {
  if (modalContainerId === "registerModal"){
    handleGenericModal('/home/register/', () => {
      const modalContainer = document.getElementById(modalContainerId);
      initLoginAndRegistrationModalLinks(modalContainerId);
      const registerModalForm = modalContainer.querySelector("#registerModalForm");
      initRegistrationForm(registerModalForm);
      // No need to init the dismiss button here because it is already done by "handleGenericModal"
    }, () => {}, true, false);
    return;
  }

  const modalContainer = document.getElementById(modalContainerId);
  modalContainer.classList.add('show');
  modalContainer.style.display = 'block';

  // Activate links inside the modal that toggle other modals
  initLoginAndRegistrationModalLinks(modalContainerId);

  // Activate modal dismiss button
  initModalDismissButton(modalContainer);

  // In case the modal we are activating contains some specific forms, carry out some special init actions
  const registerModalForm = modalContainer.querySelector("#registerModalForm");
  if (registerModalForm !== null){
    initRegistrationForm(registerModalForm);
  }
  const problemsLoggingInForm = modalContainer.querySelector("#problemsLoggingInModalForm");
  if (problemsLoggingInForm !== null){
    initProblemsLoggingInForm(problemsLoggingInForm);
  }
  const loginForm = modalContainer.querySelector("#loginForm");
  if (loginForm !== null){
    initLoginForm(loginForm);
  }
};

modals.forEach(modal => {
  modal.addEventListener('click', () => handleModal(modal.dataset.target.substring(1)));
});


document.addEventListener("DOMContentLoaded", () => {
  if (registrationParam)  {
    handleModal('registerModal');
  }
  if (feedbackRegistrationParam) {
    handleModal('feedbackRegistration');
  }
  if (problemsLoggingInParam) {
    handleModal('forgottenPasswordModal');
  }
});

// Confirmation modal
const confirmationModalButtons = [...document.querySelectorAll('[data-toggle="confirmation-modal"]')];
confirmationModalButtons.forEach(modalButton => {
  modalButton.addEventListener('click', () => {
      const confirmationModalTitle = document.getElementById('confirmationModalTitle');
      confirmationModalTitle.innerText = modalButton.dataset.modalConfirmationTitle;
      
      const confirmationModalHelpText = document.getElementById('confirmationModalHelpText');
      const helpText = modalButton.dataset.modalConfirmationHelpText;
      if (helpText !== undefined){
        confirmationModalHelpText.innerText = helpText;
      } else {
        confirmationModalHelpText.innerText = '';
      }
      
      const confirmationModalAcceptForm = document.getElementById('confirmationModalAcceptSubmitForm');
      confirmationModalAcceptForm.action = modalButton.dataset.modalConfirmationUrl;
      handleModal('confirmationModal');
  });
});


// Generic modals

const genericModalWrapper = document.getElementById('genericModalWrapper');

const handleGenericModal = (fetchContentUrl, onLoadedCallback, onClosedCallback, doRequestAsync, showLoadingToast) => {
  if (showLoadingToast !== false) { showToastNoTimeout('Loading...'); }
  const req = new XMLHttpRequest();
  req.open('GET', fetchContentUrl, doRequestAsync !== false);
  req.onload = () => {
    if (req.status >= 200 && req.status < 300) {
        if (req.responseText !== ""){
            // If response contents are not empty, add modal contents to the generic modal wrapper (the requested URL
            // should return a modal template extending "modal_base.html")
            genericModalWrapper.innerHTML = req.responseText;
            const modalContainerId = genericModalWrapper.getElementsByClassName('modal')[0].id;
            const modalContainer = document.getElementById(modalContainerId);

            // Make modal visible
            modalContainer.classList.add('show');
            modalContainer.style.display = 'block';

            // Add dismiss click handler including call to callback if defined
            const modalDismiss = [...document.querySelectorAll('[data-dismiss="modal"]')];
            modalDismiss.forEach(dismiss => {
              dismiss.addEventListener('click', () => {
                handleDismissModal(modalContainerId);
                if (onClosedCallback !== undefined){
                  onClosedCallback();
                }
              });
            });

            // Make paginator update modal (if any)
            modalContainer.getElementsByClassName('bw-pagination_container').forEach(paginationContainer => {
              paginationContainer.getElementsByTagName('a').forEach(paginatorLinkElement => {
                const loadPageUrl = paginatorLinkElement.href;
                paginatorLinkElement.href = 'javascript:void(0);';
                paginatorLinkElement.onclick = () => {
                  handleGenericModal(loadPageUrl, onLoadedCallback, onClosedCallback);
                };
              });
            });

            // Dismiss loading indicator toast and call "on loaded" call back
            if (showLoadingToast !== false) { dismissToast(); }
            if (onLoadedCallback !== undefined){
              onLoadedCallback();
            }
        } else {
            // If response contents are empty, do not show any modal but dismiss the loading toast (if used)
            if (showLoadingToast !== false) { dismissToast(); }
        }
    } else {
      // Unexpected errors happened while processing request: close modal and show error in toast
      showToast('Some errors occurred while loading the requested content.')
    }
  };
  req.onerror = () => {
    // Unexpected errors happened while processing request: close modal and show error in toast
    showToast('Some errors occurred while loading the requested content.')
  };

  // Send the form
  req.send();
};

export {handleDismissModal, handleModal, handleGenericModal};
