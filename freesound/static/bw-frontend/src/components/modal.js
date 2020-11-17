const modals = [...document.querySelectorAll('[data-toggle="modal"]')];

const handleModal = modalContainerId => {
  const modalDismiss = [...document.querySelectorAll('[data-dismiss="modal"]')];
  const modalLinks = [
    document.querySelector('[data-link="forgottenPassword"]'),
    document.querySelector('[data-link="loginModal"]'),
  ];

  const modalContainer = document.getElementById(modalContainerId);
  modalContainer.classList.add('show');
  modalContainer.style.display = 'block';

  const handleDismissModal = () => {
    modalContainer.classList.remove('show');
    modalContainer.style.display = 'none';
  };

  modalDismiss.forEach(dismiss => {
    dismiss.addEventListener('click', () => handleDismissModal());
  });

  modalLinks.forEach(link => {
    link.addEventListener('click', () => {
      handleDismissModal();
      handleModal(link.dataset.link);
    });
  });
};

modals.forEach(modal => {
  modal.addEventListener('click', () => handleModal(modal.dataset.target.substring(1)));
});
