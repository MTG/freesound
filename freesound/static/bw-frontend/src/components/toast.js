export const showToast = text => {
  const toastElement = document.querySelector('[role="alert"]');

  toastElement.style.display = 'block';
  toastElement.children[0].innerHTML = text;

  setTimeout(function() {
    toastElement.style.display = 'none';
  }, 5000);
};
