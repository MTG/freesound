import customRegistrationSubmit from "../pages/loginAndRegistration";

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

  const registerModalForm = document.getElementById("registerModalForm");
  if (registerModalForm !== undefined){

     var captchaWidgetId = grecaptcha.render( 'recaptchaWidget', {
      'sitekey' : '6Lduqx0TAAAAAG1HDusG3DKY22pkAEHxy5KxlZ4Y',  // required
      'theme' : 'light',  // optional
    });


    registerModalForm.onsubmit = (event) => {
      customRegistrationSubmit(event);
    }
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
