import initRegistrationForm from "../pages/loginAndRegistration";

const modals = [...document.querySelectorAll('[data-toggle="modal"]')];

const urlParams = new URLSearchParams(window.location.search);
const newPasswordParam = urlParams.get('newPassword');
const registrationParam = urlParams.get('registration');
const feedbackRegistrationParam = urlParams.get('feedbackRegistration');

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

  // In case the modal we are activating contains the use registration form, carry out some special init actions
  const registerModalForm = modalContainer.querySelector("#registerModalForm");
  if (registerModalForm !== null){
    initRegistrationForm(registerModalForm);
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

export {handleDismissModal, handleModal};
