let hideToastTimeout;

const wrapTextInUl = (text) => {
  // We wrap toast messages in ul/li so that they are formatted the same when returned from Django and when directly triggered in javascript
  if (text.indexOf('<ul>') === -1){
    return '<ul><li><span class="h-spacing-1">·</span>' + text + '</li></ul>';
  }
  return text;
}

export const showToast = text => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  toastElement.style.display = 'block';
  toastElement.children[0].innerHTML = wrapTextInUl(text);
  hideToastTimeout = setTimeout(() => {
    toastElement.style.display = 'none';
  }, 5000);
};

export const showToastNoTimeout = text => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  toastElement.style.display = 'block';
  toastElement.children[0].innerHTML = wrapTextInUl(text);
};

export const dismissToast = () => {
  clearTimeout(hideToastTimeout);
  const toastElement = document.querySelector('[role="alert"]');
  toastElement.style.display = 'none';
};