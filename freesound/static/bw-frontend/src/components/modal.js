const modals = [...document.querySelectorAll('[data-toggle="modal"]')];

const handleModal = modal => {
  const modalContainerId = modal.dataset.target.substring(1);
  const modalDismiss = [...document.querySelectorAll('[data-dismiss="modal"]')];

  const modalContainer = document.getElementById(modalContainerId);
  modalContainer.classList.add('show');
  modalContainer.style.display = 'block';

  console.log('modal', modalContainerId, modalContainer);

  const handleDismissModal = () => {
    modalContainer.classList.remove('show');
    modalContainer.style.display = 'none';
  };

  modalDismiss.forEach(dismiss => {
    dismiss.addEventListener('click', () => handleDismissModal(modal));
  });
};

modals.forEach(modal => {
  modal.addEventListener('click', () => handleModal(modal));
});
