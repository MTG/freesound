let hideToastTimeout;

export const showToast = text => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  toastElement.style.display = 'block';
  toastElement.children[0].innerHTML = text;
  hideToastTimeout = setTimeout(() => {
    toastElement.style.display = 'none';
  }, 5000);
};

export const showToastNoTimeout = text => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  toastElement.style.display = 'block';
  toastElement.children[0].innerHTML = text;
};

export const dismissToast = () => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  toastElement.style.display = 'none';
};