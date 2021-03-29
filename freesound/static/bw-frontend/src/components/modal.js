import {initRegistrationForm, initProblemsLoggingInForm} from "../pages/loginAndRegistration";
import {showToast} from "./toast";

const modals = [...document.querySelectorAll('[data-toggle="modal"]')];

const urlParams = new URLSearchParams(window.location.search);
const newPasswordParam = urlParams.get('newPassword');
const registrationParam = urlParams.get('registration');
const feedbackRegistrationParam = urlParams.get('feedbackRegistration');
const problemsLoggingInParam = urlParams.get('loginProblems');

const handleDismissModal = modalContainerId => {
  const modalContainer = document.getElementById(modalContainerId);
  modalContainer.classList.remove('show');
  modalContainer.style.display = 'none';
};

const handleModal = modalContainerId => {
  const modalDismiss = [...document.querySelectorAll('[data-dismiss="modal"]')];
  const modalLinks = [
    document.querySelectorAll('[data-link="forgottenPasswordModal"]'),
    document.querySelectorAll('[data-link="loginModal"]'),
    document.querySelectorAll('[data-link="registerModal"]'),
  ];

  const modalContainer = document.getElementById(modalContainerId);
  modalContainer.classList.add('show');
  modalContainer.style.display = 'block';

  // In case the modal we are activating contains some specific forms, carry out some special init actions
  const registerModalForm = modalContainer.querySelector("#registerModalForm");
  if (registerModalForm !== null){
    initRegistrationForm(registerModalForm);
  }
  const problemsLoggingInForm = modalContainer.querySelector("#problemsLoggingInModalForm");
  if (problemsLoggingInForm !== null){
    initProblemsLoggingInForm(problemsLoggingInForm);
  }

  modalDismiss.forEach(dismiss => {
    dismiss.addEventListener('click', () => handleDismissModal(modalContainerId));
  });

  modalLinks.forEach(links => {
    links.forEach(link => {
      link.addEventListener('click', () => {
        handleDismissModal(modalContainerId);
        handleModal(link.dataset.link);
      });
    });
  });
};

modals.forEach(modal => {
  modal.addEventListener('click', () => handleModal(modal.dataset.target.substring(1)));
});

if (newPasswordParam) {
  handleModal('newPasswordModal');
}

if (registrationParam)  {
  handleModal('registerModal');
}

if (feedbackRegistrationParam) {
  handleModal('feedbackRegistration');
}

if (problemsLoggingInParam) {
  handleModal('forgottenPasswordModal');
}

const genericModalWrapper = document.getElementById('generiModalWrapper');

const handleGenericModal = fetchContentUrl => {
  const req = new XMLHttpRequest();
  req.open('GET', fetchContentUrl, true);
  req.onload = () => {
    if (req.status >= 200 && req.status < 400) {

        // Add modal contents to the generic modal wrapper (the requested URL should return a modal template
        // extending "modal_base.html")
        genericModalWrapper.innerHTML = req.responseText;
        const modalContainerId = genericModalWrapper.getElementsByClassName('modal')[0].id;
        const modalContainer = document.getElementById(modalContainerId);

        // Make modal visible
        modalContainer.classList.add('show');
        modalContainer.style.display = 'block';

        // Add dismiss click handler
        const modalDismiss = [...document.querySelectorAll('[data-dismiss="modal"]')];
        modalDismiss.forEach(dismiss => {
          dismiss.addEventListener('click', () => handleDismissModal(modalContainerId));
        });

        // Make paginator update modal (if any)
        modalContainer.getElementsByClassName('bw-pagination_container').forEach(paginationContainer => {
          paginationContainer.getElementsByTagName('a').forEach(paginatorLinkElement => {
            const loadPageUrl = paginatorLinkElement.href;
            paginatorLinkElement.href = 'javascript:void(0);';
            paginatorLinkElement.onclick = () => {
              handleGenericModal(loadPageUrl);
            };
          });
        });
    }
  };
  req.onerror = () => {
    // Unexpected errors happened while processing request: close modal and show error in toast
    showToast('Some errors occurred while loading requested content.')
  };

  // Send the form
  req.send();
};


export {handleDismissModal, handleModal, handleGenericModal};
