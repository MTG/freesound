// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

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

// @license-end
